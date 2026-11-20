"""Windows 시뮬레이터와 WSL ROS 2 토픽을 연결한다."""

import math
import socket
import time
from pathlib import Path

import rclpy
from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import PointStamped, Vector3Stamped
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .simulator import Simulator, SimulatorError, UdpTransport
from .transport import SimulatorUnavailable, WindowsRelay


NS = 1_000_000_000
NEUTRAL = (0.0, 0.0)


def valid_pair(xy, lower, upper):
    return (
        isinstance(xy, (list, tuple)) and len(xy) == 2
        and all(type(v) in (int, float) and math.isfinite(v) and lower <= v <= upper for v in xy)
    )


def stamp_ns(msg):
    return msg.header.stamp.sec * NS + msg.header.stamp.nanosec


def set_header(msg, stamp):
    msg.header.frame_id = 'plate'
    msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp, NS)


class BridgeNode(Node):
    def __init__(self):
        super().__init__('sim_bridge')
        self.transport = self.declare_parameter('transport', 'relay').value
        self.host = self.declare_parameter('host', '127.0.0.1').value
        self.port = self.declare_parameter('port', 9877).value
        self.reset_pending = self.declare_parameter('reset_on_start', True).value
        self.disturbance_enabled = self.declare_parameter('disturbance_enabled', True).value
        self.force = (
            self.declare_parameter('force_x', 0.008).value,
            self.declare_parameter('force_y', -0.005).value,
        )
        rate = self.declare_parameter('rate_hz', 100.0).value
        self.timeout = self.declare_parameter('command_timeout', 0.20).value
        if self.transport not in ('relay', 'udp') or not 1 <= self.port <= 65535:
            raise ValueError('transport=relay 또는 udp와 유효한 UDP 포트가 필요합니다.')
        if not 10.0 <= rate <= 200.0 or not 0.05 <= self.timeout <= 1.0:
            raise ValueError('rate_hz=10~200, command_timeout=0.05~1.0 범위를 사용하세요.')
        if not valid_pair(self.force, -0.05, 0.05):
            raise ValueError('실습 외력의 축별 범위는 ±0.05 N입니다.')

        self.sim = None
        self.configured = False
        self.retry_at = 0.0
        self.last_stamp = None
        self.last_sim_t = None
        self.last_sensor_at = 0.0
        self.sensor_valid = False
        self.command = None
        self.target = None
        self.displayed_target = None
        self.last_display_at = 0.0

        self.position_pub = self.create_publisher(PointStamped, '/ballplate/position', 10)
        self.force_pub = self.create_publisher(Vector3Stamped, '/ballplate/disturbance', 10)
        self.motor_pub = self.create_publisher(Vector3Stamped, '/ballplate/motor_actual', 10)
        self.create_subscription(Vector3Stamped, '/ballplate/motor_cmd', self.on_command, 10)
        self.create_subscription(PointStamped, '/ballplate/target', self.on_target, 10)
        self.create_timer(1.0 / rate, self.tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_command(self, msg):
        stamp = stamp_ns(msg)
        angles = (msg.vector.x, msg.vector.y)
        if (
            msg.header.frame_id == 'plate' and self.sensor_valid and self.last_stamp is not None
            and 0 <= self.last_stamp - stamp <= 100_000_000
            and valid_pair(angles, -0.65, 0.75)
            and (self.command is None or stamp >= self.command[0])
        ):
            self.command = (stamp, time.monotonic(), angles)

    def on_target(self, msg):
        xy = (msg.point.x, msg.point.y)
        stamp = stamp_ns(msg)
        if (
            msg.header.frame_id == 'plate' and valid_pair(xy, -0.12, 0.12)
            and self.last_stamp is not None and 0 <= self.last_stamp - stamp <= 100_000_000
        ):
            self.target = xy

    def connect(self):
        if self.sim is None:
            if self.transport == 'relay':
                share = Path(get_package_share_directory('ballplate_lab'))
                transport = WindowsRelay(share / 'windows' / 'udp_relay.ps1', self.port)
            else:
                transport = UdpTransport(self.host, self.port)
            self.sim = Simulator(transport)

        self.sim.request('state')
        if self.reset_pending:
            self.sim.request('reset')
            self.reset_pending = False
            self.sim.request('pause', value=False)
        self.sim.request('mode', mode='external')
        self.set_disturbance()
        self.configured = True
        self.get_logger().info(f'Connected to simulator ({self.transport}, UDP {self.port}).')

    def set_disturbance(self):
        force = self.force if self.disturbance_enabled else NEUTRAL
        self.sim.disturbance(self.disturbance_enabled, force)

    def tick(self):
        now = time.monotonic()
        if now < self.retry_at:
            return
        try:
            if not self.configured:
                self.connect()

            angles = NEUTRAL
            if (
                self.command is not None and self.sensor_valid
                and now - self.command[1] < self.timeout
                and now - self.last_sensor_at < self.timeout
                and self.last_stamp - self.command[0] <= 100_000_000
            ):
                angles = self.command[2]
            # motor 응답에 새 센서 데이터도 들어 있어 별도 state 폴링이 필요 없다.
            state = self.sim.request('motor', angle_rad=list(angles))
            self.publish_state(state)

            if (
                self.target is not None and self.target != self.displayed_target
                and now - self.last_display_at >= 0.10
            ):
                self.sim.request('target', xy_m=list(self.target))
                self.displayed_target = self.target
                self.last_display_at = now
        except (OSError, SimulatorError, KeyError, TypeError, ValueError) as exc:
            self.get_logger().warning(f'Simulator: {exc}', throttle_duration_sec=2.0)
            self.command = None
            self.sensor_valid = False
            self.configured = False
            self.retry_at = time.monotonic() + 0.5
            if not isinstance(exc, SimulatorUnavailable):
                self.close_transport()

    def publish_state(self, state):
        sensor = state['sensor']
        ts = sensor['timestamp']
        sim_t = state['t']
        if not math.isfinite(ts) or not 0.0 <= ts < 2**31 or not math.isfinite(sim_t):
            raise SimulatorError('Invalid simulator timestamp.')
        stamp = round(ts * NS)

        if self.last_sim_t is not None and sim_t < self.last_sim_t:
            self.command = None
            self.target = None
            self.displayed_target = None
            self.last_stamp = None
            self.set_disturbance()
            self.get_logger().info('Simulator reset detected. Reapplied disturbance.')
        self.last_sim_t = sim_t

        xy = sensor['xy_m']
        self.sensor_valid = (
            sensor['valid'] is True and not state['paused'] and valid_pair(xy, -1.0, 1.0)
        )
        if not self.sensor_valid:
            self.command = None
            if not state['paused']:
                self.get_logger().warning(
                    'Ball sensor is invalid. Reset the simulator to resume.',
                    throttle_duration_sec=2.0,
                )
            return
        if stamp == self.last_stamp:
            return
        position = PointStamped()
        set_header(position, stamp)
        position.point.x, position.point.y = map(float, xy)
        self.last_stamp = stamp
        self.last_sensor_at = time.monotonic()
        self.position_pub.publish(position)
        self.publish_vector(self.force_pub, stamp, state['disturbance']['applied_force_N'])
        self.publish_vector(self.motor_pub, stamp, state['motor']['angle_rad'])

    @staticmethod
    def publish_vector(publisher, stamp, values):
        msg = Vector3Stamped()
        set_header(msg, stamp)
        msg.vector.x, msg.vector.y = map(float, values)
        publisher.publish(msg)

    def close_transport(self):
        if self.sim is not None:
            self.sim.close()
            self.sim = None

    def stop(self):
        if self.sim is None:
            return
        try:
            self.sim.request('motor', angle_rad=list(NEUTRAL))
            self.sim.disturbance(False, NEUTRAL)
        except (OSError, SimulatorError, ValueError):
            pass
        finally:
            self.close_transport()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        # 한 WSL 세션에서 같은 시뮬레이터에 두 브리지가 명령하지 않도록 한다.
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as lease:
            node = BridgeNode()
            try:
                lease.bind(f'\0ballplate_lab_{node.port}')
            except OSError as exc:
                node.get_logger().error(f'Another bridge is already using port {node.port}: {exc}')
                return 1
            try:
                rclpy.spin(node)
            finally:
                node.stop()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()

"""시뮬레이터 센서 시각으로 목표와 위치를 짝지어 PID를 실행한다."""

import math
import time

import rclpy
from geometry_msgs.msg import PointStamped, Vector3Stamped
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import Header

from .pid import PID, XY


NANOSECONDS_PER_SECOND = 1_000_000_000
MAX_SAMPLE_GAP_NS = 100_000_000
QUEUE_DEPTH = 10
StampedPoints = dict[int, tuple[XY, Header, float]]


class ControllerNode(Node):
    def __init__(self):
        super().__init__('controller')
        kp = self._startup_parameter('kp', 0.55)
        ki = self._startup_parameter('ki', 0.20)
        kd = self._startup_parameter('kd', 0.35)
        filter_tau = self._startup_parameter('filter_tau', 0.035)
        max_tilt = self._startup_parameter('max_tilt', 0.10)
        self._input_timeout = self._startup_parameter('input_timeout', 0.25)
        if not 0.0 < max_tilt <= 0.10:
            raise ValueError('max_tilt must be in (0, 0.10] rad')
        if self._input_timeout <= 0.0:
            raise ValueError('input_timeout must be positive')
        self._pid = PID(kp, ki, kd, filter_tau, max_tilt)
        self._positions: StampedPoints = {}
        self._targets: StampedPoints = {}
        self._latest_position_stamp: int | None = None
        self._last_sample_stamp: int | None = None
        self._last_command_header: Header | None = None
        self._last_inputs_at = 0.0

        self._tilt_pub = self.create_publisher(Vector3Stamped, '/ballplate/tilt_cmd', QUEUE_DEPTH)
        self._error_pub = self.create_publisher(Vector3Stamped, '/ballplate/error', QUEUE_DEPTH)
        self.create_subscription(
            PointStamped, '/ballplate/position', self._on_position, QUEUE_DEPTH
        )
        self.create_subscription(PointStamped, '/ballplate/target', self._on_target, QUEUE_DEPTH)
        self.create_timer(0.05, self._watchdog, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def _startup_parameter(self, name: str, default: float) -> float:
        parameter = self.declare_parameter(
            name, default, ParameterDescriptor(read_only=True, description='Set at node startup.')
        )
        value = parameter.value
        if not math.isfinite(value) or value < 0.0:
            raise ValueError(f'{name} must be finite and nonnegative')
        return value

    @staticmethod
    def _stamp(msg: PointStamped) -> int | None:
        stamp = msg.header.stamp
        if msg.header.frame_id != 'plate' or stamp.sec < 0:
            return None
        if not 0 <= stamp.nanosec < NANOSECONDS_PER_SECOND:
            return None
        return stamp.sec * NANOSECONDS_PER_SECOND + stamp.nanosec

    def _queue(
        self, points: StampedPoints, stamp: int, msg: PointStamped, bound: float
    ) -> None:
        xy = (msg.point.x, msg.point.y)
        if not all(math.isfinite(value) and abs(value) <= bound for value in xy):
            return
        points[stamp] = (xy, msg.header, time.monotonic())
        if len(points) > QUEUE_DEPTH:
            del points[next(iter(points))]
        self._control_if_matched(stamp)

    def _on_position(self, msg: PointStamped) -> None:
        stamp = self._stamp(msg)
        if stamp is None or stamp == self._latest_position_stamp:
            return
        if self._latest_position_stamp is not None and stamp < self._latest_position_stamp:
            # 리셋 직후 목표가 위치보다 먼저 도착했을 수도 있다.
            target = self._targets.get(stamp)
            self._reset_control()
            if target is not None:
                self._targets[stamp] = target
        self._latest_position_stamp = stamp
        self._queue(self._positions, stamp, msg, bound=1.0)

    def _on_target(self, msg: PointStamped) -> None:
        stamp = self._stamp(msg)
        if stamp is not None:
            self._queue(self._targets, stamp, msg, bound=0.12)

    def _control_if_matched(self, stamp: int) -> None:
        if stamp not in self._positions or stamp not in self._targets:
            return
        measurement, header, position_at = self._positions.pop(stamp)
        reference, _, target_at = self._targets.pop(stamp)
        inputs_at = min(position_at, target_at)
        if time.monotonic() - inputs_at >= self._input_timeout:
            return

        dt = None
        if self._last_sample_stamp is not None:
            delta = stamp - self._last_sample_stamp
            if delta <= 0:
                return
            if delta <= MAX_SAMPLE_GAP_NS:
                dt = delta / NANOSECONDS_PER_SECOND
        ux, uy = self._pid.update(reference, measurement, dt)
        if not math.isfinite(ux) or not math.isfinite(uy):
            raise ValueError('PID must return finite tilt commands')
        self._publish_xy(self._tilt_pub, header, ux, uy)
        self._publish_xy(
            self._error_pub, header, reference[0] - measurement[0], reference[1] - measurement[1]
        )
        self._last_sample_stamp = stamp
        self._last_command_header = header
        self._last_inputs_at = inputs_at

    @staticmethod
    def _publish_xy(publisher, header: Header, x: float, y: float) -> None:
        msg = Vector3Stamped()
        msg.header = header
        msg.vector.x = float(x)
        msg.vector.y = float(y)
        publisher.publish(msg)

    def _reset_control(self) -> None:
        if self._last_command_header is not None:
            self._publish_xy(self._tilt_pub, self._last_command_header, 0.0, 0.0)
        self._pid.reset()
        self._positions.clear()
        self._targets.clear()
        self._last_sample_stamp = None
        self._last_command_header = None

    def _watchdog(self) -> None:
        if self._last_command_header is None:
            return
        if time.monotonic() - self._last_inputs_at >= self._input_timeout:
            self.get_logger().warn('Position/target input stalled. Returning to neutral tilt.')
            self._reset_control()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ControllerNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except NotImplementedError as exc:
        node.get_logger().error(str(exc))
        return 1
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()

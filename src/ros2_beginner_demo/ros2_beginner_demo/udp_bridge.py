"""외부 장치의 UDP 메시지와 ROS 2 토픽 사이를 연결합니다."""

import json
import socket

from geometry_msgs.msg import PointStamped, Vector3Stamped
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


class UdpBridge(Node):
    def __init__(self):
        super().__init__('udp_bridge')
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp.connect(('127.0.0.1', 9999))
        self.udp.settimeout(0.05)  # 장치가 꺼져 있어도 오래 기다리지 않습니다.

        self.position_pub = self.create_publisher(PointStamped, '/demo/position', 10)
        self.motor_sub = self.create_subscription(
            Vector3Stamped, '/demo/motor_cmd', self.send_motor, 10
        )
        self.timer = self.create_timer(0.5, self.read_position)

    def read_position(self):
        # UDP 위치 응답 -> ROS 2 위치 토픽[m].
        try:
            self.udp.send(b'{"op":"state"}')
            reply = json.loads(self.udp.recv(4096))
            x, y = map(float, reply['xy_m'])
        except (OSError, KeyError, TypeError, ValueError):
            self.get_logger().warning(
                '위치를 받지 못했습니다. 가상 장치를 확인하세요.', throttle_duration_sec=3.0
            )
            return

        msg = PointStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'plate'
        msg.point.x = x
        msg.point.y = y
        self.position_pub.publish(msg)

    def send_motor(self, msg):
        # ROS 2 모터 토픽[rad] -> UDP 명령. x는 A, y는 B에 해당합니다.
        packet = {'op': 'motor', 'angle_rad': [msg.vector.x, msg.vector.y]}
        try:
            self.udp.send(json.dumps(packet, allow_nan=False).encode('utf-8'))
        except (OSError, ValueError):
            self.get_logger().warning('UDP 모터 명령 전송 실패', throttle_duration_sec=3.0)


def main():
    rclpy.init()
    node = UdpBridge()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.udp.close()
        node.destroy_node()
        rclpy.try_shutdown()

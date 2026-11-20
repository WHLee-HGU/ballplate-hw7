"""기울기 명령을 실제 시뮬레이터 서보 명령 토픽으로 변환한다."""

import rclpy
from geometry_msgs.msg import Vector3Stamped
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .simulator import plate_to_servo


class MotorNode(Node):
    def __init__(self):
        super().__init__('motor_mapper')
        self.motor = self.create_publisher(Vector3Stamped, '/ballplate/motor_cmd', 10)
        self.create_subscription(Vector3Stamped, '/ballplate/tilt_cmd', self.on_tilt, 10)

    def on_tilt(self, msg):
        if msg.header.frame_id != 'plate':
            return
        try:
            # 양의 u_x, u_y가 각각 공을 +X, +Y로 가속하는 좌표계.
            a, b = plate_to_servo(-msg.vector.y, msg.vector.x)
        except ValueError as exc:
            self.get_logger().warning(str(exc), throttle_duration_sec=1.0)
            return
        command = Vector3Stamped()
        command.header = msg.header
        command.vector.x = a
        command.vector.y = b
        self.motor.publish(command)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MotorNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()

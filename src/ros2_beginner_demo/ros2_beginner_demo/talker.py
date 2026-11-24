"""1초마다 번호가 붙은 문자열을 발행한다."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class Talker(Node):
    def __init__(self):
        super().__init__('talker')
        # String 메시지를 /chatter에 발행한다. 큐 깊이는 10이다.
        self.publisher = self.create_publisher(String, '/chatter', 10)
        self.count = 1
        self.timer = self.create_timer(1.0, self.publish_message)

    def publish_message(self):
        message = String()
        message.data = f'안녕하세요, ROS 2! #{self.count}'
        self.publisher.publish(message)
        self.get_logger().info(f'보냄 → {message.data}')
        self.count += 1


def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    try:
        # 타이머 콜백을 처리하며 Ctrl+C가 입력될 때까지 기다린다.
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

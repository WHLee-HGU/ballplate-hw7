"""구독한 문자열을 받을 때마다 화면에 표시한다."""

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from std_msgs.msg import String


class Listener(Node):
    def __init__(self):
        super().__init__('listener')
        self.subscription = self.create_subscription(
            String, '/chatter', self.receive_message, 10
        )

    def receive_message(self, message):
        # 실제 문자열은 String 메시지의 data 필드에 들어 있다.
        self.get_logger().info(f'받음 → {message.data}')


def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

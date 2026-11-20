"""센서의 시뮬레이션 시간에 동기화해 목표 위치를 발행하는 노드."""

import math

import rclpy
from geometry_msgs.msg import PointStamped
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

from .trajectory import DEFAULT_WAYPOINTS, Trajectory


class TrajectoryNode(Node):
    def __init__(self):
        super().__init__("trajectory")
        defaults = {
            "mode": "fixed",
            "fixed_xy": [0.0, 0.0],
            "waypoints": list(DEFAULT_WAYPOINTS),
            "segment_s": 4.0,
            "hold_s": 1.0,
        }
        parameters = {
            name: self.declare_parameter(
                name, default, ParameterDescriptor(read_only=True)
            ).value
            for name, default in defaults.items()
        }
        self.trajectory = Trajectory(**parameters)
        self.start_ns = None
        self.previous_ns = None
        self.publisher = self.create_publisher(PointStamped, "/ballplate/target", 10)
        self.create_subscription(PointStamped, "/ballplate/position", self.on_position, 10)
        self.get_logger().info(f"Trajectory mode: {self.trajectory.mode}")

    def on_position(self, position):
        if position.header.frame_id != "plate" or not all(
            math.isfinite(value) for value in (position.point.x, position.point.y)
        ):
            return
        stamp = position.header.stamp
        stamp_ns = stamp.sec * 1_000_000_000 + stamp.nanosec
        if stamp_ns == self.previous_ns:
            return
        if self.previous_ns is None or stamp_ns < self.previous_ns:
            self.start_ns = stamp_ns
        self.previous_ns = stamp_ns
        elapsed_s = (stamp_ns - self.start_ns) / 1_000_000_000

        target = PointStamped()
        target.header = position.header
        target.point.x, target.point.y = self.trajectory.at(elapsed_s)
        self.publisher.publish(target)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = TrajectoryNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.try_shutdown()

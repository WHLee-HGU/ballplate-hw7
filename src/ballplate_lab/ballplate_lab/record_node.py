"""같은 센서 시각의 목표와 공 위치를 CSV에 기록합니다."""

from collections import OrderedDict
import csv
import math
from pathlib import Path
import sys

import rclpy
from geometry_msgs.msg import PointStamped
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node


CSV_COLUMNS = (
    "sim_t_s", "target_x_m", "target_y_m", "x_m", "y_m", "error_x_m", "error_y_m",
)
MAX_UNMATCHED = 128


class ExperimentRecorder(Node):
    def __init__(self):
        super().__init__("experiment_recorder")
        csv_path = self.declare_parameter(
            "csv_path", "ballplate.csv", ParameterDescriptor(read_only=True)
        ).value
        if not csv_path:
            raise ValueError("csv_path에 CSV 파일 경로를 지정하세요.")
        self.csv_path = Path(csv_path).expanduser().resolve()
        self.pending = {"position": OrderedDict(), "target": OrderedDict()}
        self.last_stamp_ns = {"position": None, "target": None}
        self.written = 0
        self.create_subscription(
            PointStamped, "/ballplate/position", self.on_position, 10
        )
        self.create_subscription(
            PointStamped, "/ballplate/target", self.on_target, 10
        )
        self.create_timer(0.5, self.flush_log)

        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_file = self.csv_path.open("x", encoding="utf-8", newline="")
        try:
            self.writer = csv.writer(self.log_file)
            self.writer.writerow(CSV_COLUMNS)
            self.flush_log()
        except OSError:
            self.log_file.close()
            raise
        self.get_logger().info(f"CSV recording started at {self.csv_path}")

    def on_position(self, message):
        self.receive(message, "position", "target")

    def on_target(self, message):
        self.receive(message, "target", "position")

    def receive(self, message, source, counterpart):
        if self.log_file is None or message.header.frame_id != "plate":
            return
        xy = (message.point.x, message.point.y)
        if not all(math.isfinite(value) for value in xy):
            return
        stamp = message.header.stamp
        stamp_ns = stamp.sec * 1_000_000_000 + stamp.nanosec
        previous_ns = self.last_stamp_ns[source]
        if stamp_ns == previous_ns:
            return
        if previous_ns is not None and stamp_ns < previous_ns:
            self.get_logger().error(
                "Simulator time rewound. Closing this CSV. Use a new file for the next run."
            )
            self.close_log()
            return
        self.last_stamp_ns[source] = stamp_ns

        other_xy = self.pending[counterpart].pop(stamp_ns, None)
        if other_xy is None:
            queue = self.pending[source]
            queue[stamp_ns] = xy
            if len(queue) > MAX_UNMATCHED:
                queue.popitem(last=False)
            return

        (x, y), (target_x, target_y) = (xy, other_xy) if source == "position" else (other_xy, xy)
        time_s = f"{stamp.sec}.{stamp.nanosec:09d}"
        self.writer.writerow((time_s, target_x, target_y, x, y, target_x - x, target_y - y))
        self.written += 1

    def flush_log(self):
        if self.log_file is not None:
            self.log_file.flush()

    def close_log(self):
        if self.log_file is not None:
            log_file = self.log_file
            self.log_file = None
            log_file.close()
            summary = f"CSV saved with {self.written} matched rows at {self.csv_path}"
            if rclpy.ok(context=self.context):
                self.get_logger().info(summary)
            else:
                print(summary, flush=True)


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ExperimentRecorder()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except (OSError, ValueError) as exc:
        print(f"CSV recording failed ({exc})", file=sys.stderr)
        return 1
    finally:
        try:
            if node is not None:
                try:
                    node.close_log()
                finally:
                    node.destroy_node()
        finally:
            rclpy.try_shutdown()
    return 0

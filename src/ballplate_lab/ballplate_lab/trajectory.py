"""시뮬레이션 경과 시간으로 목표의 X, Y 좌표를 계산합니다."""

import math


TARGET_LIMIT_M = 0.12
DEFAULT_WAYPOINTS = (0.025, 0.025, -0.025, 0.025, -0.025, -0.025, 0.025, -0.025)
MODES = ("fixed", "waypoint_step", "waypoint_linear")


class Trajectory:
    """원점 부근의 고정 목표 또는 순환 경유점 경로."""

    def __init__(
        self,
        mode="fixed",
        fixed_xy=(0.0, 0.0),
        waypoints=DEFAULT_WAYPOINTS,
        segment_s=4.0,
        hold_s=1.0,
    ):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}")
        if len(fixed_xy) != 2:
            raise ValueError("fixed_xy must be [x, y]")
        if len(waypoints) < 4 or len(waypoints) % 2 != 0:
            raise ValueError("waypoints must be [x0, y0, x1, y1, ...] with at least two points")
        if any(
            not math.isfinite(value) or abs(value) > TARGET_LIMIT_M
            for value in (*fixed_xy, *waypoints)
        ):
            raise ValueError(f"all coordinates must be finite and within ±{TARGET_LIMIT_M} m")
        if not math.isfinite(segment_s) or segment_s <= 0.0:
            raise ValueError("segment_s must be finite and positive")
        if not math.isfinite(hold_s) or hold_s < 0.0:
            raise ValueError("hold_s must be finite and nonnegative")

        self.mode = mode
        self.fixed_xy = tuple(fixed_xy)
        self.waypoints = tuple(zip(waypoints[::2], waypoints[1::2]))
        self.segment_s = segment_s
        self.hold_s = hold_s
        self.interval_s = segment_s + hold_s if mode == "waypoint_linear" else segment_s
        self.cycle_s = self.interval_s * len(self.waypoints)
        if not math.isfinite(self.cycle_s):
            raise ValueError("trajectory cycle time must be finite")

    def at(self, elapsed_s):
        """첫 유효 샘플 이후 경과 시간 [s]에 대한 목표 (x, y) [m]."""
        if self.mode == "fixed":
            return self.fixed_xy

        cycle_phase_s = elapsed_s % self.cycle_s
        index = min(int(cycle_phase_s / self.interval_s), len(self.waypoints) - 1)
        current_xy = self.waypoints[index]
        if self.mode == "waypoint_step":
            return current_xy

        interval_phase_s = cycle_phase_s - index * self.interval_s
        fraction = max(0.0, min(1.0, (interval_phase_s - self.hold_s) / self.segment_s))
        next_x, next_y = self.waypoints[(index + 1) % len(self.waypoints)]
        x, y = current_xy
        return x + fraction * (next_x - x), y + fraction * (next_y - y)

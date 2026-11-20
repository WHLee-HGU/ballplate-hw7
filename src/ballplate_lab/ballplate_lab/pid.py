"""학생용 PID 구현 파일. 위치와 목표는 [m], dt는 [s], 출력은 [rad]."""


XY = tuple[float, float]


class PID:
    def __init__(self, kp: float, ki: float, kd: float, filter_tau: float, max_tilt: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.filter_tau = filter_tau
        self.max_tilt = max_tilt
        self.reset()

    def reset(self) -> None:
        self.previous_measurement: XY | None = None
        self.velocity = [0.0, 0.0]
        self.integral = [0.0, 0.0]

    def update(self, reference: XY, measurement: XY, dt: float | None) -> XY:
        """유효 기울기 (u_x, u_y)를 반환한다. dt=None은 새 제어 구간의 첫 샘플이다."""
        # TODO 1. 각 축의 오차를 구하고 비례항을 계산하세요.
        # TODO 2. 유효한 dt에 대해 오차를 적분하고 적분 포화를 방지하세요.
        # TODO 3. 측정값의 차분을 저역통과 필터링해 미분항을 계산하세요.
        # TODO 4. 이전 측정값을 갱신하고 두 축의 출력을 각각 ±max_tilt로 제한하세요.
        # 첫 샘플에서는 내부 상태를 초기화한 뒤 비례항만 쓰세요.
        raise NotImplementedError('Complete PID.update in ballplate_lab/pid.py first.')

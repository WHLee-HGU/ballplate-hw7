"""Windows 시뮬레이터 UDP 프로토콜과 판 역기구학."""

import json
import math
import socket


class SimulatorError(RuntimeError):
    """The simulator rejected a request or returned invalid state."""


class UdpTransport:
    def __init__(self, host, port):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.settimeout(0.05)
        try:
            self.socket.connect((host, port))
        except OSError:
            self.socket.close()
            raise

    def request(self, packet):
        self.socket.send(json.dumps(packet, allow_nan=False).encode('utf-8'))
        return json.loads(self.socket.recv(16384))

    def close(self):
        self.socket.close()


class Simulator:
    def __init__(self, transport):
        self.transport = transport

    def request(self, op, **fields):
        response = self.transport.request(dict(op=op, **fields))
        if not isinstance(response, dict) or 'error' in response:
            raise SimulatorError(f'{op}: {response}')
        return response

    def disturbance(self, enabled, force):
        self.request('disturbance', enabled=enabled, force_N=list(force), end_s=None)

    def close(self):
        self.transport.close()


def clamp(value, lower, upper):
    return max(lower, min(upper, value))


def plate_to_servo(roll, pitch):
    """판의 roll/pitch [rad]에서 서보 A/B 각도 [rad]를 계산한다."""
    if not all(math.isfinite(v) and abs(v) <= 0.10 for v in (roll, pitch)):
        raise ValueError('판의 기울기는 축별 ±0.10 rad 이내여야 합니다.')

    # 원본 lab_common.py와 동일한 R=Rx(roll)Ry(pitch) 및 기구 치수.
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    attachments = (
        (0.0, -0.13 * cr, 0.19 - 0.13 * sr),
        (0.13 * cp, 0.13 * sr * sp, 0.19 - 0.13 * cr * sp),
    )
    origins = ((0.0, -0.18, 0.075), (0.18, 0.0, 0.075))
    angles = []
    for axis, (point, origin) in enumerate(zip(attachments, origins)):
        dx, dy, dz = (p - o for p, o in zip(point, origin))
        a = dy if axis == 0 else -dx
        c = (dx * dx + dy * dy + dz * dz - 0.115**2) / 0.05
        angle = math.atan2(dz, a) - math.acos(clamp(c / math.hypot(a, dz), -1.0, 1.0))
        angles.append(clamp(angle, -0.65, 0.75))
    return angles

"""ROS 2 없이 동작하는 가상 외부 장치."""

import json
import socket


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.bind(('127.0.0.1', 9999))
        print('가상 장치가 UDP 127.0.0.1:9999에서 대기합니다.', flush=True)
        while True:
            data, peer = udp.recvfrom(4096)
            try:
                packet = json.loads(data)
                operation = packet['op']
                if operation == 'state':
                    # 위치 요청을 보낸 주소로 X, Y 위치[m]를 회신합니다.
                    reply = {'xy_m': [0.03, -0.01]}
                    udp.sendto(json.dumps(reply).encode('utf-8'), peer)
                elif operation == 'motor':
                    # 모터 명령은 받아서 출력하고, 회신은 보내지 않습니다.
                    a, b = packet['angle_rad']
                    print(f'모터 명령 [rad]  A={a}  B={b}', flush=True)
            except (KeyError, TypeError, ValueError):
                print('잘못된 UDP 메시지를 건너뜁니다.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass

# 처음 시작하는 ROS 2 Jazzy

Ubuntu 24.04에서 Python 발행자와 구독자를 실행하고, UDP 브리지로 가상 장치와 통신하는 실습입니다. WSL 2의 Ubuntu에서도 같은 명령을 사용합니다.

## Ubuntu에서 다운로드하고 빌드하기

ROS 2 Jazzy, Git, colcon을 설치한 Ubuntu 터미널에서 실행합니다. `~/ros2_beginner_ws`에 기존 실습이 있으면 먼저 이름을 바꿔 보관합니다.

```bash
git clone --depth 1 --branch ros2-beginner \
  https://github.com/WHLee-HGU/ballplate-hw7.git ~/ros2_beginner_ws
cd ~/ros2_beginner_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

[Ubuntu용 ROS 2 Jazzy 및 개발 도구 설치](https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html)

## 터미널 두 개에서 메시지 주고받기

터미널 A에서 발행자를 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_beginner_ws/install/setup.bash
export ROS_DOMAIN_ID=42
ros2 run ros2_beginner_demo talker
```

터미널 B에서 구독자를 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_beginner_ws/install/setup.bash
export ROS_DOMAIN_ID=42
ros2 run ros2_beginner_demo listener
```

두 노드는 `/chatter`에서 `std_msgs/msg/String`을 주고받습니다. 같은 환경을 불러온 터미널 C에서 확인합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_beginner_ws/install/setup.bash
export ROS_DOMAIN_ID=42
ros2 node list
ros2 topic list -t
ros2 topic echo /chatter --once
```

GUI를 사용할 수 있고 `rqt_graph`가 설치된 환경에서는 `ros2 run rqt_graph rqt_graph`로 연결을 볼 수 있습니다. 종료하려면 각 터미널에서 Ctrl+C를 누릅니다.

## UDP 브리지 실습

A와 B의 이전 노드를 Ctrl+C로 종료합니다. 터미널 A에서 가상 장치를 시작합니다.

```bash
cd ~/ros2_beginner_ws
python3 tools/fake_device.py
```

터미널 B에서 ROS 2 브리지를 실행합니다.

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_beginner_ws/install/setup.bash
export ROS_DOMAIN_ID=42
ros2 run ros2_beginner_demo udp_bridge
```

같은 ROS 2 환경과 도메인 번호를 설정한 터미널 C에서 위치를 읽고 모터 명령을 보냅니다.

```bash
ros2 topic echo /demo/position --once
ros2 topic pub --once /demo/motor_cmd \
  geometry_msgs/msg/Vector3Stamped '{vector: {x: 0.1, y: -0.2}}'
```

C에서 X=0.03, Y=-0.01 m가, A에서 모터 A=0.1, B=-0.2 rad 명령이 보입니다. 가상 장치의 UDP 포트는 9999입니다. 실제 [Ball on Plate HW7](https://github.com/WHLee-HGU/ballplate-hw7/tree/main)의 실행 방법은 과제 저장소 기본 브랜치에서 확인합니다.

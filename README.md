# HW7 Ball-on-Plate PID 실습

시뮬레이터에서 받은 공의 X·Y 위치를 목표에 추종시키고, 일정한 외력을 받는 동안 PD, PI, PID의 응답을 데이터로 비교합니다. Windows에서 `BallPlateSimulator.exe`를 실행하고, WSL의 ROS 2 Jazzy에서 Python 노드를 실행합니다.

## 1. 워크스페이스 준비

준비물은 Windows의 WSL 2 Ubuntu 24.04, WSL에 설치한 ROS 2 Jazzy·`colcon`·Git입니다. `BallPlateSimulator.exe`는 수업에서 별도로 배포합니다. 받은 실행 파일은 Windows에 보관하세요.

PowerShell에서 Ubuntu를 시작하세요.

```powershell
wsl.exe -d Ubuntu-24.04
```

WSL에서 아래 명령으로 학생용 저장소를 복제하고 빌드하세요. 복제한 폴더가 ROS 2 워크스페이스입니다.

```bash
git clone https://github.com/WHLee-HGU/ballplate-hw7.git ~/ballplate_student_ws
cd ~/ballplate_student_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

새 WSL 터미널에서는 `source /opt/ros/jazzy/setup.bash`와 `source ~/ballplate_student_ws/install/setup.bash`를 실행하세요.

## 2. PID 구현

`src/ballplate_lab/ballplate_lab/pid.py`의 `PID.update()` 안에 있는 네 가지 TODO를 채우세요. 입력 `reference`와 `measurement`는 각각 목표와 측정 위치 `(x, y)` [m]입니다. `dt` [s]는 연속 센서 샘플 간격이며, 새 제어 구간의 첫 샘플에서는 `None`입니다. 반환값 `(u_x, u_y)`의 단위는 rad입니다.

1. 각 축의 오차 `e = r − y`를 구해 비례항 `Kp × e`를 계산하세요.
2. 이전 적분 상태에 `e × dt`를 더해 적분 후보를 구하세요. 후보를 반영한 출력이 한계를 넘고 현재 오차가 같은 방향으로 포화를 심화하는 경우, 어떤 상태를 유지해야 할지 판단하세요.
3. 측정값의 후진 차분 `(y_now − y_prev) / dt`로 속도를 추정하세요. `α = dt / (τ + dt)`를 쓰는 1차 필터를 적용하고, 공의 움직임을 감쇠하도록 필터링한 속도의 부호를 고려하세요.
4. 세 항을 합쳐 축별 `±max_tilt`로 제한하고 이전 측정값을 갱신하세요. 첫 샘플에서는 상태를 초기화하고 비례항만 사용하세요.

`Ki = 0`이면 PD, `Kd = 0`이면 PI입니다. 각 게인이 0일 때 해당 항의 기여도가 0이 되도록 하나의 `PID.update()`에 구현하세요. `NotImplementedError`는 TODO를 구현한 뒤 제거합니다. 시뮬레이터를 켜기 전에 `dt=None`, 한 축의 오차만 있는 경우, 측정값이 일정한 상태에서 목표만 바뀌는 경우, 기울기 한계에 도달하는 경우의 출력을 점검하세요.

## 3. 동일한 외력으로 비교

Windows에서 `BallPlateSimulator.exe`를 열어 두세요. WSL에서는 아래 명령을 **한 번에 하나씩** 실행합니다. 각 실행이 시뮬레이터를 초기화하고 기본 외력 `(0.008, −0.005)` N을 계속 가합니다. 기본 설정은 `disturbance:=true force_x:=0.008 force_y:=-0.005`입니다. 외력, 목표, 공통 게인과 초기화 조건을 세 모드에서 동일하게 유지하세요. 실행별로 새 CSV 경로를 사용하고 시뮬레이션 경과 시간이 약 22초가 되거나 공이 판을 벗어나면 `Ctrl+C`를 누르세요.

```bash
ros2 launch ballplate_lab experiment.launch.py control:=pd  trajectory:=fixed csv:="$PWD/pd_fixed.csv"
ros2 launch ballplate_lab experiment.launch.py control:=pi  trajectory:=fixed csv:="$PWD/pi_fixed.csv"
ros2 launch ballplate_lab experiment.launch.py control:=pid trajectory:=fixed csv:="$PWD/pid_fixed.csv"
```

두 번째 WSL 터미널에서도 ROS 환경을 불러오면 위치 [m], 목표 [m], 기울기 명령 [rad], 실제 외력 [N]을 확인할 수 있습니다. `--once`를 빼면 지속적으로 표시됩니다.

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic echo /ballplate/position --once
ros2 topic echo /ballplate/target --once
ros2 topic echo /ballplate/tilt_cmd --once
ros2 topic echo /ballplate/disturbance --once
```

고정 목표에서는 첫 센서 샘플을 기준으로 같은 `12–20 s` 구간을 요약하세요.

```bash
ros2 run ballplate_lab summarize_run "$PWD/pd_fixed.csv" --start 12 --end 20
ros2 run ballplate_lab summarize_run "$PWD/pi_fixed.csv" --start 12 --end 20
ros2 run ballplate_lab summarize_run "$PWD/pid_fixed.csv" --start 12 --end 20
```

이후 같은 실험을 `trajectory:=waypoint_linear`로 반복하고 파일명을 `pd_waypoint.csv`, `pi_waypoint.csv`, `pid_waypoint.csv`로 바꾸세요. 기본 경로는 네 경유점을 잇는 20초 사각형입니다. 세 모드를 첫 한 바퀴(`--start 0 --end 20`)에서 비교하세요.

## 4. 기록과 해석

- **고정 목표**에서 X·Y 오차의 부호 있는 평균과 위치 오차의 크기를 비교하세요. PD는 일정한 힘을 상쇄하기 위해 위치가 목표에서 벗어난 상태에 머물 수 있습니다. 적분항이 그 편차를 줄였는지 데이터로 확인하세요.
- **경유점 경로**에서 목표와 실제 X·Y 궤적, 위치 오차의 RMSE와 최대값을 비교하세요. 꼭짓점에서 생기는 지연과 지나침을 살펴보고, 기울기 명령이 한계에 도달한 구간을 확인하세요.
- **PI와 PID의 차이**에서 미분항이 진동과 오버슈트에 준 영향을 설명하세요. 공이 판에서 벗어났거나 유효 샘플이 20초 이전에 끊겼다면 그 시점과 마지막으로 관측한 거동을 기록하세요. 일부 구간만 측정된 실행은 측정 시간도 함께 표시하세요.

구현한 `pid.py`, 실행별 CSV, X·Y 그래프, 비교 결과를 함께 제출하세요. 관측이 예상과 달랐다면 게인, 출력 포화, 실행 조건을 근거로 설명하세요.

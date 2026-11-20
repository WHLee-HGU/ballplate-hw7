from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, OpaqueFunction, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def launch_nodes(context):
    params = LaunchConfiguration('params_file')
    control = LaunchConfiguration('control').perform(context)
    csv_path = LaunchConfiguration('csv').perform(context)

    def value(name, value_type):
        return ParameterValue(LaunchConfiguration(name), value_type=value_type)

    nodes = [
        Node(
            package='ballplate_lab', executable='trajectory', output='screen',
            parameters=[params, {'mode': value('trajectory', str)}],
        ),
        Node(
            package='ballplate_lab', executable='controller', output='screen',
            parameters=[params, {
                'kp': value('kp', float),
                'ki': 0.0 if control == 'pd' else value('ki', float),
                'kd': 0.0 if control == 'pi' else value('kd', float),
            }],
        ),
        Node(package='ballplate_lab', executable='motor_mapper', output='screen'),
        Node(
            package='ballplate_lab', executable='sim_bridge', output='screen',
            parameters=[params, {
                'transport': value('transport', str),
                'host': value('host', str),
                'port': value('port', int),
                'reset_on_start': value('reset', bool),
                'disturbance_enabled': value('disturbance', bool),
                'force_x': value('force_x', float),
                'force_y': value('force_y', float),
            }],
        ),
    ]
    if csv_path:
        nodes.insert(0, Node(
            package='ballplate_lab', executable='experiment_recorder', output='screen',
            parameters=[{'csv_path': ParameterValue(csv_path, value_type=str)}],
        ))

    handlers = [
        RegisterEventHandler(OnProcessExit(
            target_action=node,
            on_exit=[EmitEvent(event=Shutdown(reason='An experiment node exited.'))],
        ))
        for node in nodes
    ]
    return handlers + nodes


def generate_launch_description():
    config = Path(get_package_share_directory('ballplate_lab')) / 'config' / 'experiment.yaml'
    return LaunchDescription([
        DeclareLaunchArgument('control', default_value='pid', choices=['pid', 'pd', 'pi']),
        DeclareLaunchArgument(
            'trajectory', default_value='waypoint_linear',
            choices=['fixed', 'waypoint_step', 'waypoint_linear'],
        ),
        DeclareLaunchArgument('kp', default_value='0.55'),
        DeclareLaunchArgument('ki', default_value='0.20'),
        DeclareLaunchArgument('kd', default_value='0.35'),
        DeclareLaunchArgument('disturbance', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('force_x', default_value='0.008', description='X force in N'),
        DeclareLaunchArgument('force_y', default_value='-0.005', description='Y force in N'),
        DeclareLaunchArgument('reset', default_value='true', choices=['true', 'false']),
        DeclareLaunchArgument('transport', default_value='relay', choices=['relay', 'udp']),
        DeclareLaunchArgument('host', default_value='127.0.0.1', description='Direct UDP host'),
        DeclareLaunchArgument('port', default_value='9877'),
        DeclareLaunchArgument('csv', default_value='', description='New CSV file path'),
        DeclareLaunchArgument('params_file', default_value=str(config)),
        OpaqueFunction(function=launch_nodes),
    ])

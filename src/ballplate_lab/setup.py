from setuptools import setup


setup(
    name='ballplate_lab',
    version='0.1.0',
    packages=['ballplate_lab'],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/ballplate_lab']),
        ('share/ballplate_lab', ['package.xml']),
        ('share/ballplate_lab/launch', ['launch/experiment.launch.py']),
        ('share/ballplate_lab/config', ['config/experiment.yaml']),
        ('share/ballplate_lab/windows', ['windows/udp_relay.ps1']),
    ],
    install_requires=['setuptools'],
    maintainer='Ball on Plate Lab',
    maintainer_email='maintainer@example.org',
    description='Ball on Plate PID laboratory for ROS 2 Jazzy.',
    license='MIT',
    entry_points={
        'console_scripts': [
            'sim_bridge = ballplate_lab.bridge_node:main',
            'trajectory = ballplate_lab.trajectory_node:main',
            'controller = ballplate_lab.controller_node:main',
            'motor_mapper = ballplate_lab.motor_node:main',
            'experiment_recorder = ballplate_lab.record_node:main',
            'summarize_run = ballplate_lab.summarize:main',
        ],
    },
)

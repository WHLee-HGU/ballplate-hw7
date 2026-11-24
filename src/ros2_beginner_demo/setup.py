from setuptools import setup


package_name = 'ros2_beginner_demo'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', [f'resource/{package_name}']),
        (f'share/{package_name}', ['package.xml']),
    ],
    install_requires=['setuptools'],
    maintainer='ROS 2 Lab',
    maintainer_email='ros2-lab@example.invalid',
    description='Beginner ROS 2 Jazzy topic and simulator exercises.',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'talker = ros2_beginner_demo.talker:main',
            'listener = ros2_beginner_demo.listener:main',
            'udp_bridge = ros2_beginner_demo.udp_bridge:main',
        ],
    },
)

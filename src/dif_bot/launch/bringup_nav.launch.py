"""
Todo en uno para el proyecto final / video:
  Gazebo + robot + EKF + map_server/AMCL + Nav2 + RViz
  ros2 launch dif_bot bringup_nav.launch.py map:=/ruta/a/mapa.yaml [use_ros2_control:=true]
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot')
    launch_dir = os.path.join(pkg, 'launch')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'sim.launch.py')),
        launch_arguments={
            'use_ros2_control': LaunchConfiguration('use_ros2_control'),
            'use_ekf': 'true',
            'rviz': 'false',
            'headless': LaunchConfiguration('headless'),
            'world': LaunchConfiguration('world'),
        }.items(),
    )
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'localization.launch.py')),
        launch_arguments={'map': LaunchConfiguration('map')}.items(),
    )
    navigation = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(launch_dir, 'navigation.launch.py')),
    )
    rviz = Node(
        package='rviz2', executable='rviz2', output='screen',
        condition=IfCondition(LaunchConfiguration('rviz')),
        arguments=['-d', os.path.join(pkg, 'rviz', 'nav.rviz')],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=os.path.join(pkg, 'maps', 'warehouse.yaml')),
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('world', default_value=os.path.join(pkg, 'worlds', 'warehouse.sdf')),
        sim,
        # se da tiempo a que Gazebo publique /clock y TF antes de arrancar AMCL/Nav2
        TimerAction(period=5.0, actions=[localization]),
        TimerAction(period=8.0, actions=[navigation, rviz]),
    ])

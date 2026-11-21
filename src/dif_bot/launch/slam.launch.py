"""
Practica 3: SLAM Toolbox (online async).
Requiere la simulacion corriendo, idealmente con EKF:
  ros2 launch dif_bot sim.launch.py use_ekf:=true rviz:=false
  ros2 launch dif_bot slam.launch.py
  ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
Guardar el mapa:
  ros2 run nav2_map_server map_saver_cli -f ~/rbtc_ws/src/dif_bot/maps/warehouse
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot')
    slam_params = LaunchConfiguration('slam_params_file')
    rviz = LaunchConfiguration('rviz')

    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('slam_toolbox'), 'launch', 'online_async_launch.py')),
        launch_arguments={'slam_params_file': slam_params, 'use_sim_time': 'true'}.items(),
    )

    rviz_node = Node(
        package='rviz2', executable='rviz2', output='screen', condition=IfCondition(rviz),
        arguments=['-d', os.path.join(pkg, 'rviz', 'nav.rviz')],
        parameters=[{'use_sim_time': True}],
    )

    return LaunchDescription([
        DeclareLaunchArgument('slam_params_file',
                              default_value=os.path.join(pkg, 'config', 'slam_toolbox.yaml')),
        DeclareLaunchArgument('rviz', default_value='true'),
        slam,
        rviz_node,
    ])

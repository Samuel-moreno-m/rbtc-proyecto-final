import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('dif_bot_mission')
    return LaunchDescription([
        DeclareLaunchArgument('waypoints_file',
                              default_value=os.path.join(pkg, 'config', 'waypoints.yaml')),
        Node(
            package='dif_bot_mission',
            executable='mission_node',
            name='mission_node',
            output='screen',
            emulate_tty=True,
            parameters=[{'waypoints_file': LaunchConfiguration('waypoints_file'),
                         'use_sim_time': True}],
        ),
    ])

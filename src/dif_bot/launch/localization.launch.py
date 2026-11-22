import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    pkg = get_package_share_directory('dif_bot')
    map_yaml = LaunchConfiguration('map')
    params = LaunchConfiguration('params_file')
    autostart = LaunchConfiguration('autostart')
    rviz = LaunchConfiguration('rviz')

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=os.path.join(pkg, 'maps', 'warehouse.yaml')),
        DeclareLaunchArgument('params_file', default_value=os.path.join(pkg, 'config', 'amcl.yaml')),
        DeclareLaunchArgument('autostart', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='false'),

        Node(package='nav2_map_server', executable='map_server', name='map_server',
             output='screen',
             parameters=[params, {'yaml_filename': map_yaml, 'use_sim_time': True}]),

        Node(package='nav2_amcl', executable='amcl', name='amcl', output='screen',
             parameters=[params, {'use_sim_time': True}]),

        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_localization', output='screen',
             parameters=[{'use_sim_time': True, 'autostart': autostart,
                          'node_names': ['map_server', 'amcl']}]),

        Node(package='rviz2', executable='rviz2', output='screen', condition=IfCondition(rviz),
             arguments=['-d', os.path.join(pkg, 'rviz', 'nav.rviz')],
             parameters=[{'use_sim_time': True}]),
    ])

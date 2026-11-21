"""
Practica 5: servidores de navegacion de Nav2 (planner, controller, behaviors, BT navigator...).
Requiere simulacion + localizacion corriendo.
  ros2 launch dif_bot navigation.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile


def generate_launch_description():
    pkg = get_package_share_directory('dif_bot')
    params = ParameterFile(LaunchConfiguration('params_file'), allow_substs=True)
    autostart = LaunchConfiguration('autostart')

    lifecycle_nodes = ['controller_server', 'smoother_server', 'planner_server',
                       'behavior_server', 'velocity_smoother', 'bt_navigator',
                       'waypoint_follower']

    common = {'use_sim_time': True}

    return LaunchDescription([
        DeclareLaunchArgument('params_file',
                              default_value=os.path.join(pkg, 'config', 'nav2_params.yaml')),
        DeclareLaunchArgument('autostart', default_value='true'),

        Node(package='nav2_controller', executable='controller_server', output='screen',
             parameters=[params, common], remappings=[('cmd_vel', 'cmd_vel_nav')]),
        Node(package='nav2_smoother', executable='smoother_server', name='smoother_server',
             output='screen', parameters=[params, common]),
        Node(package='nav2_planner', executable='planner_server', name='planner_server',
             output='screen', parameters=[params, common]),
        Node(package='nav2_behaviors', executable='behavior_server', name='behavior_server',
             output='screen', parameters=[params, common],
             remappings=[('cmd_vel', 'cmd_vel_nav')]),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother', output='screen', parameters=[params, common],
             remappings=[('cmd_vel', 'cmd_vel_nav'), ('cmd_vel_smoothed', 'cmd_vel')]),
        Node(package='nav2_bt_navigator', executable='bt_navigator', name='bt_navigator',
             output='screen', parameters=[params, common]),
        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             name='waypoint_follower', output='screen', parameters=[params, common]),

        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation', output='screen',
             parameters=[{'use_sim_time': True, 'autostart': autostart,
                          'node_names': lifecycle_nodes}]),
    ])

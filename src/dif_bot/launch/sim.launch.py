import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            OpaqueFunction, RegisterEventHandler, TimerAction)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
import xacro

def _bool(context, name):
    return context.launch_configurations[name].lower() in ('true', '1', 'yes')

def launch_setup(context, *args, **kwargs):
    pkg = get_package_share_directory('dif_bot')
    use_ros2_control = _bool(context, 'use_ros2_control')
    spawn_controllers = _bool(context, 'spawn_controllers')
    use_ekf = _bool(context, 'use_ekf')
    headless = _bool(context, 'headless')
    rviz = _bool(context, 'rviz')
    world = context.launch_configurations['world']
    laser_noise = context.launch_configurations['laser_noise']
    x = context.launch_configurations['x']
    y = context.launch_configurations['y']
    yaw = context.launch_configurations['yaw']

    robot_description = xacro.process_file(
        os.path.join(pkg, 'urdf', 'robot.urdf.xacro'),
        mappings={
            'use_ros2_control': str(use_ros2_control).lower(),
            'odom_tf': str(not use_ekf).lower(),
            'laser_noise': laser_noise,
        },
    ).toxml()

    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )

    gz_args = f'-r -v 2 {world}'
    if headless:
        gz_args = f'-s --headless-rendering {gz_args}'
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': gz_args, 'on_exit_shutdown': 'true'}.items(),
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'dif_bot',
                   '-x', x, '-y', y, '-z', '0.02', '-Y', yaw],
    )

    bridges = [Node(
        package='ros_gz_bridge', executable='parameter_bridge', name='bridge_sensors',
        output='screen',
        parameters=[{'config_file': os.path.join(pkg, 'config', 'bridge_sensors.yaml'),
                     'use_sim_time': True}],
    )]
    if not use_ros2_control:
        bridges.append(Node(
            package='ros_gz_bridge', executable='parameter_bridge', name='bridge_gz_control',
            output='screen',
            parameters=[{'config_file': os.path.join(pkg, 'config', 'bridge_gz_control.yaml'),
                         'use_sim_time': True}],
        ))
        if not use_ekf:
            bridges.append(Node(
                package='ros_gz_bridge', executable='parameter_bridge', name='bridge_gz_tf',
                output='screen',
                parameters=[{'config_file': os.path.join(pkg, 'config', 'bridge_gz_tf.yaml'),
                             'use_sim_time': True}],
            ))

    actions = [rsp, gazebo, spawn, *bridges]

    if use_ros2_control and spawn_controllers:
        timeouts = ['--controller-manager-timeout', '60',
                    '--switch-timeout', '30', '--service-call-timeout', '30']
        jsb = Node(package='controller_manager', executable='spawner', output='screen',
                   arguments=['joint_state_broadcaster', *timeouts])
        ddc = Node(package='controller_manager', executable='spawner', output='screen',
                   arguments=['diff_drive_controller', *timeouts])
        actions += [
            RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=[jsb])),
            RegisterEventHandler(OnProcessExit(target_action=jsb, on_exit=[ddc])),
        ]

    if use_ekf:
        actions.append(Node(
            package='robot_localization',
            executable='ekf_node',
            name='ekf_filter_node',
            output='screen',
            parameters=[os.path.join(pkg, 'config', 'ekf.yaml'), {'use_sim_time': True}],
            remappings=[('odometry/filtered', '/odom_filtered')],
        ))

    if rviz:
        actions.append(TimerAction(period=3.0, actions=[Node(
            package='rviz2', executable='rviz2', output='screen',
            arguments=['-d', os.path.join(pkg, 'rviz', 'dif_bot.rviz')],
            parameters=[{'use_sim_time': True}],
        )]))

    return actions

def generate_launch_description():
    pkg = get_package_share_directory('dif_bot')
    return LaunchDescription([
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        DeclareLaunchArgument('spawn_controllers', default_value='true'),
        DeclareLaunchArgument('use_ekf', default_value='false'),
        DeclareLaunchArgument('world', default_value=os.path.join(pkg, 'worlds', 'warehouse.sdf')),
        DeclareLaunchArgument('headless', default_value='false'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('laser_noise', default_value='0.01'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=launch_setup),
    ])

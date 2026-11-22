# Proyecto Final RBTC: navegación autónoma con ROS 2, Gazebo y Nav2

Robot diferencial `dif_bot` (IMU, LiDAR 2D y cámara) simulado en Gazebo. El proyecto cubre el pipeline completo:

| Práctica | Qué se hace | Archivos principales |
|---|---|---|
| 1. Control y odometría | Plugin DiffDrive de Gazebo **vs.** `ros2_control` (`diff_drive_controller`) | `urdf/robot.urdf.xacro`, `urdf/gz_control.xacro`, `urdf/ros2_control.xacro`, `config/controllers*.yaml`, `launch/sim.launch.py` |
| 2. Fusión sensorial | EKF 2D (`robot_localization`): odometría + IMU, publica `/odom_filtered` | `config/ekf.yaml` |
| 3. SLAM | SLAM Toolbox (online async), mapa en `maps/` | `config/slam_toolbox.yaml`, `launch/slam.launch.py`, `maps/warehouse.*` |
| 4. Localización | AMCL + map_server | `config/amcl.yaml`, `launch/localization.launch.py` |
| 5. Navegación | Nav2: NavFn + Regulated Pure Pursuit + BT con recuperaciones | `config/nav2_params.yaml`, `launch/navigation.launch.py` |
| Proyecto final | Nodo de misiones con `nav2_simple_commander`, servicio de inicio y waypoints en YAML | paquete `dif_bot_mission` |

**Video demostrativo:** [video/video_mision_rbtc.mp4](video/video_mision_rbtc.mp4). Muestra la misión de 7 waypoints con Gazebo, RViz y terminales: 7/7 alcanzados, 0 fallos, 8 min 13 s.

**Integrantes:** Samuel Jerónimo Moreno Mora, Esteban Pineda, Joshua Tapias · **Profesor:** Ing. Daniel Palomino Suárez, MSc. · Escuela Colombiana de Ingeniería Julio Garavito

Probado en **Ubuntu 24.04 + ROS 2 Kilted + Gazebo Ionic (gz-sim 9)**. En Jazzy (Gazebo Harmonic) también funciona; ver la sección de compatibilidad al final.

## Estructura

```
rbtc_ws/src/
├── dif_bot/                      # robot, simulación y configuración de navegación
│   ├── urdf/        robot.urdf.xacro, gz_control.xacro, ros2_control.xacro, sensors.xacro, ...
│   ├── config/      controllers.yaml, controllers_ekf.yaml, ekf.yaml, slam_toolbox.yaml,
│   │                amcl.yaml, nav2_params.yaml, bridge_*.yaml
│   ├── launch/      sim, slam, localization, navigation, bringup_nav
│   ├── worlds/      warehouse.sdf (bodega 10 x 8 m)
│   ├── maps/        warehouse.pgm / warehouse.yaml (generado con SLAM)
│   └── rviz/        dif_bot.rviz, nav.rviz
└── dif_bot_mission/              # proyecto final
    ├── dif_bot_mission/mission_node.py
    ├── config/waypoints.yaml
    └── launch/mission.launch.py
```

## Instalación

```bash
sudo apt install ros-$ROS_DISTRO-navigation2 ros-$ROS_DISTRO-nav2-bringup \
  ros-$ROS_DISTRO-slam-toolbox ros-$ROS_DISTRO-robot-localization \
  ros-$ROS_DISTRO-ros-gz ros-$ROS_DISTRO-gz-ros2-control \
  ros-$ROS_DISTRO-ros2-controllers ros-$ROS_DISTRO-teleop-twist-keyboard ros-$ROS_DISTRO-xacro

mkdir -p ~/rbtc_ws && cd ~/rbtc_ws
git clone <URL_DE_ESTE_REPO> .          # o copiar la carpeta src/
source /opt/ros/$ROS_DISTRO/setup.bash
colcon build --symlink-install
source install/setup.bash
```

> En todas las terminales nuevas: `source ~/rbtc_ws/install/setup.bash`.

Todos los `cmd_vel` del proyecto son `geometry_msgs/TwistStamped` (por defecto en Nav2 Kilted y en `diff_drive_controller`). Para teleoperar:

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
```

---

## Práctica 1: control y odometría

```bash
# a) Plugin DiffDrive de Gazebo
ros2 launch dif_bot sim.launch.py use_ros2_control:=false

# b) ros2_control (los controladores se cargan solos)
ros2 launch dif_bot sim.launch.py use_ros2_control:=true

# b') ros2_control activando los controladores a mano, como en la guía
ros2 launch dif_bot sim.launch.py use_ros2_control:=true spawn_controllers:=false
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active diff_drive_controller
```

Comandos útiles para comparar:

```bash
ros2 topic info /odom -v            # quién publica la odometría
ros2 topic hz /odom                 # Gazebo: ~30 Hz | ros2_control: ~50 Hz
ros2 control list_controllers
ros2 run tf2_tools view_frames      # genera frames.pdf con el árbol TF
```

## Práctica 2: EKF

```bash
ros2 launch dif_bot sim.launch.py use_ekf:=true          # (+ use_ros2_control:=true si se quiere)
ros2 topic echo /odom_filtered
ros2 run tf2_ros tf2_echo odom base_footprint             # ahora la publica el EKF
```

En RViz (`dif_bot.rviz`) se ven las flechas de `/odom` (rojo) y `/odom_filtered` (verde). Para probar sin IMU, comentar el bloque `imu0` de `config/ekf.yaml` y relanzar.

## Práctica 3: SLAM

```bash
ros2 launch dif_bot sim.launch.py use_ekf:=true rviz:=false
ros2 launch dif_bot slam.launch.py
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true
# recorrer toda la bodega despacio (<= 0.3 m/s) y luego:
ros2 run nav2_map_server map_saver_cli -f ~/rbtc_ws/src/dif_bot/maps/warehouse
```

## Práctica 4: AMCL

```bash
ros2 launch dif_bot sim.launch.py use_ekf:=true rviz:=false
ros2 launch dif_bot localization.launch.py map:=$HOME/rbtc_ws/src/dif_bot/maps/warehouse.yaml rviz:=true
```

AMCL arranca con pose inicial (0, 0, 0) (`amcl.yaml`). Para el experimento de pose incorrecta: en RViz usar **2D Pose Estimate** en un punto equivocado y mover el robot con teleop. Para ver la nube de partículas, activar el display `ParticleCloud` (`/particle_cloud`).

## Práctica 5: Nav2

```bash
# Todo en uno: Gazebo + EKF + AMCL + Nav2 + RViz
ros2 launch dif_bot bringup_nav.launch.py
#   (opcional) map:=/ruta/mapa.yaml  use_ros2_control:=true  headless:=true
```

En RViz usar **Nav2 Goal** para enviar metas. Para ver las recuperaciones, poner un obstáculo frente al robot desde Gazebo y observar el log de `bt_navigator` / `behavior_server`.

## Proyecto final: misiones autónomas

```bash
# Terminal 1: simulación + navegación
ros2 launch dif_bot bringup_nav.launch.py
# Terminal 2: nodo de misiones
ros2 launch dif_bot_mission mission.launch.py
# Terminal 3: estado (o rqt -> Topic Monitor / Service Caller)
ros2 topic echo /mission/status
# Terminal 4: iniciar / cancelar / recargar
ros2 service call /mission/start  std_srvs/srv/Trigger
ros2 service call /mission/cancel std_srvs/srv/Trigger
ros2 service call /mission/reload std_srvs/srv/Trigger
```

Waypoints en `dif_bot_mission/config/waypoints.yaml`:

```yaml
mission:
  name: "Ronda de inspeccion de bodega"
  frame_id: map
  mode: sequential          # sequential (goToPose uno a uno) | follow_waypoints
  loops: 1                  # 0 = infinito
  goal_timeout: 120.0
  waypoints:
    - {name: "Muelle este", x: 3.8, y: 0.5, yaw: 1.57, wait: 2.0}
    ...
```

Se puede usar otro archivo con `waypoints_file:=/ruta/otro.yaml`.

## Video demostrativo (qué grabar)

1. Pantalla dividida: Gazebo, RViz y una terminal (o RQT).
2. `ros2 launch dif_bot bringup_nav.launch.py`: mostrar el mapa, el robot localizado y los costmaps.
3. `ros2 launch dif_bot_mission mission.launch.py` y luego `ros2 service call /mission/start ...`.
4. Mostrar `/mission/status` mientras el robot recorre los waypoints (y el plan en RViz).
5. Opcional: poner un obstáculo en Gazebo para mostrar el replanteo o una recuperación; probar `/mission/cancel`.
6. Cerrar con el resumen que imprime el nodo (waypoints alcanzados y tiempo total).

Para grabar en Ubuntu: `Ctrl+Alt+Shift+R` (grabador de GNOME) u OBS Studio.

## Compatibilidad con Jazzy

- Nav2 Jazzy publica `Twist` por defecto: el archivo ya tiene `enable_stamped_cmd_vel: true`, así que funciona igual.
- Si `bt_navigator` se queja de `error_code_name_prefixes`, cambiarlo por `error_code_names: [compute_path_error_code, follow_path_error_code]`.
- `gz_args`, los plugins `gz-sim-*` y `gz_ros2_control` tienen los mismos nombres en Harmonic.

## WSL2

Si Gazebo se cierra por OpenGL: `export LIBGL_ALWAYS_SOFTWARE=1` o lanzar con `headless:=true` y usar solo RViz.

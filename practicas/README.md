# Prácticas

Cada carpeta documenta una práctica: objetivo, archivos del código que usa, comandos para ejecutarla, resultados medidos y capturas.

| # | Práctica | Resultado principal |
|---|---|---|
| 1 | [Control y odometría](practica1_control_odometria/README.md) | DiffDrive de Gazebo vs. `ros2_control`: quién publica `/odom` y la TF |
| 2 | [Fusión sensorial con EKF](practica2_fusion_ekf/README.md) | Con IMU, error de orientación de 19.5° a 6.6° |
| 3 | [Mapeo con SLAM](practica3_slam/README.md) | Mapa de 0.05 m/celda, 203 × 163 celdas |
| 4 | [Localización con AMCL](practica4_amcl/README.md) | Converge desde 1.3 m de error; falla con el robot secuestrado (3.7 m) |
| 5 | [Navegación con Nav2](practica5_nav2/README.md) | Metas desde RViz; recuperaciones ClearCostmap, Spin, Wait y BackUp |
| PF | [Misiones autónomas](proyecto_final_misiones/README.md) | 7/7 waypoints, 0 fallos ([video](../video/video_mision_rbtc.mp4)) |

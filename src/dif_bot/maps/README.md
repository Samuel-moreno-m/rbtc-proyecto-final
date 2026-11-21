# maps/

Aquí se guardan los mapas generados con SLAM (Práctica 3):

```bash
ros2 run nav2_map_server map_saver_cli -f ~/rbtc_ws/src/dif_bot/maps/warehouse
cd ~/rbtc_ws && colcon build --packages-select dif_bot   # para instalarlo
```

Resultado: `warehouse.pgm` (imagen de ocupación) + `warehouse.yaml` (resolución, origen, umbrales).

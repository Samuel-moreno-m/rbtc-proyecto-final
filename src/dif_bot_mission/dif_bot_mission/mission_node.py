import math
import threading
import time

import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.executors import ExternalShutdownException, SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger

def yaw_to_quaternion(yaw):
    return 0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0)

class MissionNode(Node):

    def __init__(self):
        super().__init__('mission_node')
        self.declare_parameter('waypoints_file', '')
        self.declare_parameter('localizer', 'amcl')

        self.status_pub = self.create_publisher(String, '/mission/status', 10)
        self.create_service(Trigger, '/mission/start', self._on_start)
        self.create_service(Trigger, '/mission/cancel', self._on_cancel)
        self.create_service(Trigger, '/mission/reload', self._on_reload)

        self.navigator = BasicNavigator(node_name='mission_navigator')
        self._nav2_ready = False
        self._worker = None
        self._cancel_requested = threading.Event()

        self.mission = None
        ok, msg = self._load_mission()
        self._status(msg if ok else f'ERROR: {msg}')
        self._status('Listo. Llame a /mission/start para iniciar la mision.')

    def _status(self, text):
        self.get_logger().info(text)
        self.status_pub.publish(String(data=text))

    def _load_mission(self):
        path = self.get_parameter('waypoints_file').value
        if not path:
            return False, 'parametro waypoints_file vacio'
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)['mission']
            wps = data['waypoints']
            if not wps:
                return False, 'la lista de waypoints esta vacia'
            for i, wp in enumerate(wps):
                for key in ('x', 'y'):
                    if key not in wp:
                        return False, f'waypoint {i} sin campo "{key}"'
            data.setdefault('frame_id', 'map')
            data.setdefault('mode', 'sequential')
            data.setdefault('loops', 1)
            data.setdefault('set_initial_pose', False)
            data.setdefault('goal_timeout', 120.0)
            if data['mode'] not in ('sequential', 'follow_waypoints'):
                return False, f'modo desconocido: {data["mode"]}'
            self.mission = data
            return True, f'Mision "{data.get("name", "sin nombre")}" cargada: {len(wps)} waypoints, ' \
                         f'modo={data["mode"]}, vueltas={data["loops"]} ({path})'
        except Exception as e:
            return False, f'no se pudo leer {path}: {e}'

    def _make_pose(self, wp):
        pose = PoseStamped()
        pose.header.frame_id = self.mission['frame_id']
        pose.header.stamp = self.navigator.get_clock().now().to_msg()
        pose.pose.position.x = float(wp['x'])
        pose.pose.position.y = float(wp['y'])
        qx, qy, qz, qw = yaw_to_quaternion(float(wp.get('yaw', 0.0)))
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def _error_info(self):
        try:
            res = self.navigator.result_future.result().result
            return f'error_code={res.error_code} {getattr(res, "error_msg", "")}'.strip()
        except Exception:
            return 'sin detalle'

    def _busy(self):
        return self._worker is not None and self._worker.is_alive()

    def _on_start(self, request, response):
        if self._busy():
            response.success = False
            response.message = 'Ya hay una mision en curso'
            return response
        if self.mission is None:
            ok, msg = self._load_mission()
            if not ok:
                response.success = False
                response.message = msg
                return response
        self._cancel_requested.clear()
        self._worker = threading.Thread(target=self._run_mission, daemon=True)
        self._worker.start()
        response.success = True
        response.message = f'Mision iniciada ({len(self.mission["waypoints"])} waypoints)'
        return response

    def _on_cancel(self, request, response):
        if not self._busy():
            response.success = False
            response.message = 'No hay mision en curso'
            return response
        self._cancel_requested.set()
        response.success = True
        response.message = 'Cancelacion solicitada'
        return response

    def _on_reload(self, request, response):
        if self._busy():
            response.success = False
            response.message = 'No se puede recargar con una mision en curso'
            return response
        ok, msg = self._load_mission()
        response.success = ok
        response.message = msg
        self._status(msg if ok else f'ERROR: {msg}')
        return response

    def _run_mission(self):
        m = self.mission
        t0 = time.monotonic()
        try:
            if m['set_initial_pose']:
                ip = m.get('initial_pose', {'x': 0.0, 'y': 0.0, 'yaw': 0.0})
                self._status(f'Fijando pose inicial ({ip["x"]:.2f}, {ip["y"]:.2f})')
                self.navigator.setInitialPose(self._make_pose(ip))

            if not self._nav2_ready:
                self._status('Esperando a que Nav2 este activo...')
                self.navigator.waitUntilNav2Active(
                    localizer=self.get_parameter('localizer').value)
                self._nav2_ready = True

            loops = int(m['loops'])
            loop = 0
            reached, failed = 0, 0
            while (loops <= 0 or loop < loops) and not self._cancel_requested.is_set():
                loop += 1
                self._status(f'=== Vuelta {loop}{"" if loops <= 0 else "/" + str(loops)} ===')
                if m['mode'] == 'sequential':
                    r, f = self._run_sequential()
                else:
                    r, f = self._run_follow_waypoints()
                reached += r
                failed += f

            elapsed = time.monotonic() - t0
            state = 'CANCELADA' if self._cancel_requested.is_set() else 'COMPLETADA'
            self._status(f'Mision {state}: {reached} waypoints alcanzados, {failed} fallidos, '
                         f'{elapsed:.1f} s')
        except Exception as e:
            self._status(f'ERROR en la mision: {e}')

    def _wait_task(self, describe, timeout):
        start = time.monotonic()
        last_log = 0.0
        canceled = False
        while not self.navigator.isTaskComplete():
            if not canceled and self._cancel_requested.is_set():
                canceled = True
                self.navigator.cancelTask()
            elif not canceled and time.monotonic() - start > timeout:
                canceled = True
                self._status(f'Timeout de {timeout:.0f} s: cancelando meta')
                self.navigator.cancelTask()
            fb = self.navigator.getFeedback()
            now = time.monotonic()
            if fb is not None and now - last_log > 2.0:
                last_log = now
                self._status(describe(fb))
        return self.navigator.getResult()

    def _run_sequential(self):
        m = self.mission
        reached, failed = 0, 0
        n = len(m['waypoints'])
        for i, wp in enumerate(m['waypoints'], start=1):
            if self._cancel_requested.is_set():
                break
            name = wp.get('name', f'WP{i}')
            self._status(f'[{i}/{n}] Navegando a "{name}" '
                         f'({wp["x"]:.2f}, {wp["y"]:.2f}, yaw={wp.get("yaw", 0.0):.2f})')
            self.navigator.goToPose(self._make_pose(wp))
            result = self._wait_task(
                lambda fb, name=name: f'  -> "{name}": distancia restante '
                                      f'{fb.distance_remaining:.2f} m, recuperaciones '
                                      f'{fb.number_of_recoveries}',
                float(wp.get('timeout', m['goal_timeout'])))
            if result == TaskResult.SUCCEEDED:
                reached += 1
                self._status(f'[{i}/{n}] "{name}" alcanzado')
                wait = float(wp.get('wait', 0.0))
                if wait > 0.0:
                    self._status(f'  esperando {wait:.1f} s en "{name}"')
                    end = time.monotonic() + wait
                    while time.monotonic() < end and not self._cancel_requested.is_set():
                        time.sleep(0.1)
            elif result == TaskResult.CANCELED:
                self._status(f'[{i}/{n}] "{name}" cancelado')
                if self._cancel_requested.is_set():
                    break
                failed += 1
            else:
                failed += 1
                self._status(f'[{i}/{n}] FALLO al ir a "{name}" ({self._error_info()}); '
                             f'se continua con el siguiente')
        return reached, failed

    def _run_follow_waypoints(self):
        m = self.mission
        poses = [self._make_pose(wp) for wp in m['waypoints']]
        n = len(poses)
        self._status(f'Enviando {n} waypoints a followWaypoints()')
        self.navigator.followWaypoints(poses)
        timeout = float(m['goal_timeout']) * n
        result = self._wait_task(
            lambda fb: f'  -> waypoint actual {fb.current_waypoint + 1}/{n}', timeout)
        if result == TaskResult.SUCCEEDED:
            missed = list(getattr(self.navigator.result_future.result().result,
                                  'missed_waypoints', []))
            return n - len(missed), len(missed)
        return 0, n

def main(args=None):
    rclpy.init(args=args)
    node = MissionNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node._cancel_requested.set()
        node.navigator.destroy_node()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()

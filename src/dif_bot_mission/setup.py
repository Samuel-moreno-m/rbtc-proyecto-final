from glob import glob
import os

from setuptools import find_packages, setup

package_name = 'dif_bot_mission'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Estudiante RBTC',
    maintainer_email='student@example.com',
    description='Nodo de misiones autonomas con nav2_simple_commander',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mission_node = dif_bot_mission.mission_node:main',
        ],
    },
)

cmake_minimum_required(VERSION 3.8)
project(dif_bot)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf config launch worlds maps rviz
  DESTINATION share/${PROJECT_NAME}
)

ament_package()

# cmake_minimum_required(VERSION 3.12 FATAL_ERROR)
cmake_minimum_required(VERSION 2.8)
project(bus-mapper)


if (CMAKE_VERSION VERSION_LESS "3.1")
  if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++11")
  endif ()
else ()
  set (CMAKE_CXX_STANDARD 11)
endif ()

# This tells the compiler to not aggressively optimize and
# to include debugging information so that the debugger
# can properly read what's going on.
set(CMAKE_BUILD_TYPE Debug)

# Let's ensure -std=c++xx instead of -std=g++xx
set(CMAKE_CXX_EXTENSIONS OFF)

# Let's nicely support folders in IDE's
set_property(GLOBAL PROPERTY USE_FOLDERS ON)

add_subdirectory(src)

add_executable(pathfind src/pathfind.cpp)
add_executable(visualize src/visualize.cpp)

# target_include_directories(bus-mapper PRIVATE include)
target_link_libraries(pathfind PRIVATE bus PRIVATE graph PRIVATE utils)
target_link_libraries(visualize PRIVATE bus PRIVATE graph PRIVATE utils)

file(GLOB_RECURSE UTILS_TEST tests/utils/*.cpp)

file(GLOB_RECURSE GRAPH_TEST tests/graph/*.cpp)

file(GLOB GENERAL_TEST tests/*.cpp)

list(APPEND TEST ${UTILS_TEST} ${GRAPH_TEST} ${GENERAL_TEST})

add_executable(test tests/test-main.cpp ${TEST})

# target_include_directories(test-bus-mapper PRIVATE include)
target_link_libraries(test PRIVATE graph PRIVATE utils)
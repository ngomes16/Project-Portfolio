file(GLOB_RECURSE SOURCE CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/src/bus/*.cpp)
add_library(bus ${SOURCE})
# We need this directory, and users of our library will need it too
target_include_directories(bus PUBLIC ${PROJECT_SOURCE_DIR}/include)
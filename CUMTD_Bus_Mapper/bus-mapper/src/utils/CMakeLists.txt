file(GLOB_RECURSE SOURCE CONFIGURE_DEPENDS ${PROJECT_SOURCE_DIR}/src/utils/*.cpp)
add_library(utils ${SOURCE})
# We need this directory, and users of our library will need it too
target_include_directories(utils PUBLIC ${PROJECT_SOURCE_DIR}/include)

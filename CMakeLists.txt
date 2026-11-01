cmake_minimum_required(VERSION 3.20)
project(BabelNativeExample LANGUAGES CXX)

set(BABEL_NATIVE_SDK_DIR "${CMAKE_CURRENT_SOURCE_DIR}/.sdk"
    CACHE PATH "Directory containing the native SDK")

add_library(BabelLicensingNative SHARED IMPORTED)
if(WIN32)
    set_target_properties(BabelLicensingNative PROPERTIES
        IMPORTED_IMPLIB "${BABEL_NATIVE_SDK_DIR}/lib/BabelLicensingNative.lib"
        IMPORTED_LOCATION "${BABEL_NATIVE_SDK_DIR}/bin/BabelLicensingNative.dll")
else()
    find_library(BABEL_NATIVE_LIBRARY
        NAMES BabelLicensingNative
        PATHS "${BABEL_NATIVE_SDK_DIR}/lib"
        NO_DEFAULT_PATH REQUIRED)
    set_target_properties(BabelLicensingNative PROPERTIES
        IMPORTED_LOCATION "${BABEL_NATIVE_LIBRARY}")
endif()

add_executable(native-example cpp/main.cpp)
target_compile_features(native-example PRIVATE cxx_std_20)
target_include_directories(native-example PRIVATE "${BABEL_NATIVE_SDK_DIR}/include")
target_link_libraries(native-example PRIVATE BabelLicensingNative)
if(MSVC)
    set_property(TARGET native-example PROPERTY
        MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
elseif(APPLE)
    set_target_properties(native-example PROPERTIES BUILD_RPATH "@loader_path")
else()
    set_target_properties(native-example PROPERTIES BUILD_RPATH "$ORIGIN")
endif()

# The deployed app needs only the Babel runtime next to its executable.
add_custom_command(TARGET native-example POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
        "$<TARGET_FILE:BabelLicensingNative>" "$<TARGET_FILE_DIR:native-example>"
    VERBATIM)

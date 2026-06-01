cmake_minimum_required(VERSION 3.18)
project(bv_ui_control VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Qt MOC / UIC / RCC auto-processing
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTOUIC ON)
set(CMAKE_AUTORCC ON)

# ── Qt6 ────────────────────────────────────────────────────────────────
# Point CMake to the Homebrew-installed Qt6
# Use Qt 6.8.2 (matches BrainVoyager) for ABI compatibility
set(CMAKE_PREFIX_PATH "/tmp/qt682/6.8.2/macos" CACHE PATH "Qt6 install prefix")

find_package(Qt6 REQUIRED COMPONENTS Core Widgets Gui Test Network WebSockets)

# ── Our dylib ──────────────────────────────────────────────────────────
add_subdirectory(src)

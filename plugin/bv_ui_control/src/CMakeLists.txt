# ── Dylib sources ──────────────────────────────────────────────────────
set(DYLIB_SOURCES
    mylib.cpp
    hook.mm          # ObjC++ injection entry point
)

set(DYLIB_HEADERS
    mylib.h
    Export.h
)

# ── Build the shared library ───────────────────────────────────────────
add_library(bv_inject SHARED ${DYLIB_SOURCES} ${DYLIB_HEADERS})

target_include_directories(bv_inject PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)

target_compile_definitions(bv_inject PRIVATE
    MYLIB_BUILDING_LIBRARY
)

# ── Link Qt ────────────────────────────────────────────────────────────
# AQT-installed Qt already uses @rpath install names, so the dylib will
# automatically use the host app's bundled Qt when injected.
target_link_libraries(bv_inject PRIVATE
    Qt6::Core
    Qt6::Widgets
    Qt6::Gui
    Qt6::Network
    Qt6::WebSockets
    Qt6::Test          # for QTest::mouseClick
)

# ── macOS: Foundation + AppKit for ObjC swizzling ──────────────────────
if(APPLE)
    target_link_libraries(bv_inject PRIVATE
        "-framework Foundation"
        "-framework AppKit"
    )

    set_target_properties(bv_inject PROPERTIES
        MACOSX_RPATH ON
        SUFFIX ".dylib"
    )

    # Ensure the injected dylib can find the host app's bundled Qt.
    # BrainVoyager has Qt in @executable_path/../Frameworks.
    add_custom_command(TARGET bv_inject POST_BUILD
        COMMAND ${CMAKE_INSTALL_NAME_TOOL}
            -add_rpath "@executable_path/../Frameworks"
            "$<TARGET_FILE:bv_inject>" || true
        COMMENT "Ensure @rpath → @executable_path/../Frameworks"
    )
endif()

# Ensure .mm files are compiled as Objective-C++
set_source_files_properties(hook.mm PROPERTIES
    COMPILE_FLAGS "-x objective-c++"
)

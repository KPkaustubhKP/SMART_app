# Smart Agriculture Project - CMakeLists.txt for Pico W
# This file configures the build system for the Raspberry Pi Pico 2 W project

cmake_minimum_required(VERSION 3.13)

# Include the Pico SDK import script
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)

# Set project name and language
project(smart_agriculture_pico)

# Set C standard
set(CMAKE_C_STANDARD 11)

# Initialize the Raspberry Pi Pico SDK
pico_sdk_init()

# Add executable
add_executable(smart_agriculture_pico
    main.c
    dht22.c  # Optional: separate DHT22 library file
)

# Create map/bin/hex/uf2 file in addition to ELF
pico_add_extra_outputs(smart_agriculture_pico)

# Link to pico_stdlib (gpio, time, etc)
target_link_libraries(smart_agriculture_pico
    pico_stdlib
    pico_cyw43_arch_lwip_threadsafe_background
    pico_lwip_http
    hardware_adc
    hardware_gpio
    pico_time
)

# Enable USB output, disable uart output
pico_enable_stdio_usb(smart_agriculture_pico 1)
pico_enable_stdio_uart(smart_agriculture_pico 0)

# Compile definitions for debugging (optional)
target_compile_definitions(smart_agriculture_pico PRIVATE
    PICO_DEFAULT_UART=0
    PICO_DEFAULT_UART_TX_PIN=0
    PICO_DEFAULT_UART_RX_PIN=1
)

# Set the board type to Pico W (important for Wi-Fi support)
set(PICO_BOARD pico_w CACHE STRING "Board type")

# Additional compile options for optimization
target_compile_options(smart_agriculture_pico PRIVATE
    -Wall
    -Wextra
    -O2
)
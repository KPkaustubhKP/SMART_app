# Smart Agriculture Pico W Integration - Complete Setup Guide

This guide provides step-by-step instructions to integrate your Raspberry Pi Pico 2 W with your Smart Agriculture website.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Hardware Setup](#hardware-setup)
3. [Software Setup](#software-setup)
4. [Backend Integration](#backend-integration)
5. [Compilation and Flashing](#compilation-and-flashing)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

## 🔧 Prerequisites

### Hardware Required:
- Raspberry Pi Pico 2 W (with Wi-Fi capability)
- DHT22 Temperature & Humidity Sensor
- Capacitive Soil Moisture Sensor
- LDR (Light Dependent Resistor) or Light Sensor Module
- Breadboard and jumper wires
- Micro-USB cable
- 10kΩ resistor (for LDR if not using module)

### Software Required:
- Raspberry Pi Pico C/C++ SDK
- CMake (version 3.13 or later)
- GCC ARM cross-compiler
- Git
- Code editor (VS Code recommended)

## 🔌 Hardware Setup

### Pin Connections:

#### DHT22 Sensor:
```
DHT22 Pin    →    Pico W Pin
VCC          →    3V3 (Pin 36)
Data         →    GPIO15 (Pin 20)
GND          →    GND (Pin 23)
```

#### Soil Moisture Sensor:
```
Sensor Pin   →    Pico W Pin
VCC          →    3V3 (Pin 36)
Signal       →    GPIO26/ADC0 (Pin 31)
GND          →    GND (Pin 23)
```

#### LDR Light Sensor:
```
LDR/Module   →    Pico W Pin
VCC          →    3V3 (Pin 36)
Signal       →    GPIO27/ADC1 (Pin 32)
GND          →    GND (Pin 23)
```

### Wiring Diagram:
```
                    Raspberry Pi Pico 2 W
                    ┌─────────────────────┐
                    │                     │
DHT22 Data    ────→ │ GPIO15         3V3  │ ←──── Sensors VCC
                    │                     │
Soil Sensor   ────→ │ GPIO26/ADC0    GND  │ ←──── Sensors GND
                    │                     │
Light Sensor  ────→ │ GPIO27/ADC1         │
Status LED    ────→ │ GPIO25 (Built-in)   │
                    │                     │
                    └─────────────────────┘
```

## 💻 Software Setup

### 1. Install Pico SDK

#### On Linux (Ubuntu/Debian):
```bash
# Install dependencies
sudo apt update
sudo apt install cmake gcc-arm-none-eabi libnewlib-arm-none-eabi build-essential git

# Clone Pico SDK
cd ~
git clone https://github.com/raspberrypi/pico-sdk.git --branch master
cd pico-sdk
git submodule update --init

# Set environment variable
echo 'export PICO_SDK_PATH=~/pico-sdk' >> ~/.bashrc
source ~/.bashrc
```

#### On Windows:
1. Install the Pico SDK installer from the official Raspberry Pi website
2. Follow the setup wizard
3. Ensure the PICO_SDK_PATH environment variable is set

#### On macOS:
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install cmake
brew tap ArmMbed/homebrew-formulae
brew install arm-none-eabi-gcc

# Clone Pico SDK
cd ~
git clone https://github.com/raspberrypi/pico-sdk.git --branch master
cd pico-sdk
git submodule update --init

# Set environment variable
echo 'export PICO_SDK_PATH=~/pico-sdk' >> ~/.zshrc
source ~/.zshrc
```

### 2. Create Project Directory

```bash
mkdir smart-agriculture-pico
cd smart-agriculture-pico
```

### 3. Copy Project Files

Copy the following files from this guide into your project directory:
- `main.c` (rename from pico-main.c)
- `CMakeLists.txt`
- `dht22.c`
- `dht22.h`
- `test-connectivity.c`

## 🖥️ Backend Integration

### 1. Update Your FastAPI Backend

Add the backend extension code to your existing FastAPI application:

1. Open your main FastAPI file (usually `main.py`)
2. Add the code from `backend-extension.py` to your existing application
3. Install any missing dependencies:

```bash
pip install aiosqlite  # If not already installed
```

### 2. Test the New Endpoint

Start your backend server and verify the new endpoint works:

```bash
# Navigate to your backend directory
cd path/to/your/backend

# Start the server
python main.py

# Test the new endpoint (in another terminal)
curl -X GET http://localhost:8000/api/sensors/pico/test
```

You should receive a JSON response confirming the endpoint is working.

## ⚙️ Compilation and Flashing

### 1. Configure the Code

Edit the configuration values in `main.c`:

```c
// Wi-Fi Configuration - EDIT THESE VALUES
#define WIFI_SSID "Your_WiFi_Network_Name"
#define WIFI_PASSWORD "Your_WiFi_Password"

// Server Configuration - EDIT THIS URL
#define SERVER_HOST "your-backend-url.com"  // Your deployed backend URL
#define SERVER_PORT 443  // Use 443 for HTTPS, 80 for HTTP
```

### 2. Build the Project

```bash
# Create build directory
mkdir build
cd build

# Configure with CMake
cmake .. -DPICO_BOARD=pico_w

# Build the project
make -j4
```

### 3. Flash to Pico W

1. Hold the BOOTSEL button on your Pico W
2. Connect it to your computer via USB (while holding BOOTSEL)
3. Release BOOTSEL - the Pico should appear as a USB drive
4. Copy the generated `.uf2` file to the Pico:

```bash
# The .uf2 file will be in the build directory
cp smart_agriculture_pico.uf2 /path/to/pico/drive/
```

The Pico will automatically reboot and start running your code.

## 🧪 Testing

### 1. Test Connectivity First

Before using the full sensor code, test connectivity with the simple test program:

1. Rename `main.c` to `main_sensors.c`
2. Rename `test-connectivity.c` to `main.c`
3. Edit the Wi-Fi and server settings in the test file
4. Build and flash the test program
5. Monitor the serial output

### 2. Monitor Serial Output

Use a serial terminal to monitor the Pico's output:

```bash
# On Linux/macOS
screen /dev/ttyACM0 115200

# On Windows, use PuTTY or similar
```

### 3. Expected Output

You should see output similar to:
```
================================================
  Smart Agriculture - Pico W Connectivity Test  
================================================

TEST 1: Wi-Fi Connection
------------------------
Connecting to Wi-Fi network: YourNetwork
✓ Connected to Wi-Fi successfully
IP Address: 192.168.1.100

TEST 2: HTTP Connectivity
-------------------------
✓ HTTP connectivity test passed!

TEST 3: JSON Communication Test
-------------------------------
✓ JSON communication test passed!

🎉 ALL TESTS PASSED! 🎉
```

### 4. Switch to Full Sensor Code

Once connectivity tests pass:

1. Rename `main.c` back to `test-connectivity.c`
2. Rename `main_sensors.c` back to `main.c`
3. Build and flash the full sensor program

## 🌐 Website Integration

Your existing website should automatically start receiving data from the Pico W. The data will appear in:

1. **Current Sensor Readings**: Updated in real-time
2. **Historical Data**: Stored in the database
3. **Device Status**: Shows when the Pico last sent data

You can verify data reception by:
1. Checking the browser console for API calls
2. Looking at the database tables
3. Monitoring the FastAPI logs

## 🔍 Troubleshooting

### Common Issues:

#### 1. Wi-Fi Connection Fails
- **Check SSID and password**: Ensure they're correct and properly escaped
- **Signal strength**: Move closer to your router
- **Network type**: Ensure you're connecting to 2.4GHz (Pico W doesn't support 5GHz)

#### 2. HTTP Requests Fail
- **Server URL**: Verify your backend is accessible from the internet
- **Firewall**: Check if port 443/80 is open
- **SSL/HTTPS**: If using HTTPS, ensure proper certificates

#### 3. Sensor Readings Are Invalid
- **Wiring**: Double-check all connections
- **Power supply**: Ensure stable 3.3V supply
- **Timing**: DHT22 needs 2+ seconds between readings

#### 4. Build Errors
- **SDK Path**: Verify PICO_SDK_PATH environment variable
- **Dependencies**: Ensure all required libraries are installed
- **Board Type**: Make sure you're building for `pico_w`

### Debug Commands:

```bash
# Check environment variables
echo $PICO_SDK_PATH

# Verify build configuration
cmake .. -DPICO_BOARD=pico_w -DCMAKE_VERBOSE_MAKEFILE=ON

# Clean build
make clean && make -j4
```

### Serial Debug Output:

The code includes extensive debug output. Monitor it to diagnose issues:

```
Initializing sensors...
✓ All sensors initialized
Connecting to Wi-Fi network: MyNetwork
✓ Connected to Wi-Fi successfully
IP Address: 192.168.1.100

=== Reading Sensors ===
Temperature: 25.50°C
Humidity: 60.00%
Soil Moisture: 45.30%
Light Intensity: 78.20%

Sending sensor data to server...
✓ Data sent successfully to server
```

## 🔄 Maintenance and Updates

### Regular Tasks:
1. **Monitor sensor accuracy**: Calibrate sensors periodically
2. **Check connectivity**: Ensure stable Wi-Fi connection
3. **Update firmware**: Keep Pico SDK updated
4. **Battery check**: If using battery power, monitor levels

### Performance Optimization:
- Adjust `SENSOR_READ_INTERVAL_MS` based on your needs
- Implement sleep modes for battery operation
- Add sensor data validation and filtering

## 📚 Additional Resources

- [Raspberry Pi Pico W Documentation](https://www.raspberrypi.org/documentation/microcontrollers/)
- [Pico C/C++ SDK Documentation](https://raspberrypi.github.io/pico-sdk-doxygen/)
- [DHT22 Sensor Datasheet](https://www.sparkfun.com/datasheets/Sensors/Temperature/DHT22.pdf)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🆘 Getting Help

If you encounter issues:

1. **Check the serial output** for error messages
2. **Verify hardware connections** with a multimeter
3. **Test with minimal code** (use the connectivity test)
4. **Check network connectivity** from other devices
5. **Review server logs** for API endpoint issues

Remember to replace all placeholder values (Wi-Fi credentials, server URLs) with your actual configuration before building and flashing the code.

---

**🎉 Congratulations!** Once everything is working, you'll have a fully integrated IoT sensor node sending real-time agricultural data to your web dashboard!
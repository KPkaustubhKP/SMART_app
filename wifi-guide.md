# NPK Sensor WiFi Integration — Complete Step-by-Step Guide

**Your Setup**: Pico 2 W (with WiFi) → NPK Sensor (RS485) → Backend API → Dashboard Website

---

## 🎯 Step 1: Understand the Architecture

```
┌─────────────────────┐
│  Friend's Laptop    │
│  (Pico 2 W WiFi)    │
│  └─ NPK Sensor (RS485)
└──────────┬──────────┘
           │ WiFi (HTTPS)
           ↓
┌─────────────────────┐
│  Backend (Render)   │
│  FastAPI + SQLite   │
└──────────┬──────────┘
           │ HTTP REST
           ↓
┌─────────────────────┐
│  Your Dashboard     │
│  (Website)          │
└─────────────────────┘
```

**Data Flow**:
1. Pico reads NPK sensor via RS485 (UART)
2. Pico sends data to backend via WiFi (HTTPS POST)
3. Backend stores in database
4. Website fetches and displays live data

---

## 🔧 Step 2: Hardware Connections on Pico 2 W

### Pico 2 W Pinout for Your Setup:

| Component | Pico Pin | GPIO | Purpose |
|-----------|----------|------|---------|
| RS485 TX | Pin 1 | GP0 | UART0 TX → Sensor TX |
| RS485 RX | Pin 2 | GP1 | UART0 RX → Sensor RX |
| RS485 DE | Pin 10 | GP7 | Transmit Enable |
| RS485 RE | Pin 11 | GP8 | Receive Enable |
| **WiFi** | Built-in CYW43 | — | Already enabled on Pico 2 W |

**Existing connections** (from your code):
- ✅ UART0 on GP0/GP1 (correct)
- ✅ DE on GP7, RE on GP8 (correct)
- ✅ CRC16 validation (correct)

---

## 📝 Step 3: Add WiFi Libraries to CMakeLists.txt

**Your current CMakeLists.txt needs these additions:**

```cmake
# Add WiFi support
target_link_libraries(NPK_Interfacing
    pico_stdlib
    hardware_uart
    pico_cyw43_arch_lwip_threadsafe_background  # ← ADD THIS
    pico_lwip_http                              # ← ADD THIS
    pico_lwip_mbedtls                           # ← ADD THIS
)

# Add WiFi include paths
target_include_directories(NPK_Interfacing PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
)
```

---

## 💾 Step 4: Updated NPK_Interfacing.c with WiFi Support

**Key additions to your code:**

### A. WiFi Credentials (Edit these!)
```c
#define WIFI_SSID "YOUR_WIFI_NETWORK"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define API_SERVER "smart-agriculture-backend-y747.onrender.com"  // Your backend
#define API_PORT 443  // HTTPS
#define API_ENDPOINT "/api/sensors/data"
```

### B. WiFi Connection Function
```c
// Initialize WiFi and connect
void wifi_init_and_connect() {
    if (cyw43_arch_init()) {
        printf("Failed to init WiFi\n");
        return;
    }
    
    cyw43_arch_enable_sta_mode();
    printf("Connecting to WiFi: %s\n", WIFI_SSID);
    
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, 
                                            CYW43_AUTH_WPA2_MIXED_PSK, 10000)) {
        printf("Failed to connect to WiFi\n");
        return;
    }
    
    printf("Connected to WiFi! IP: %s\n", ip4addr_ntoa(netif_ip4_addr(netif_default)));
}
```

### C. Send Data Function
```c
// Send sensor data to backend via HTTPS POST
void send_data_to_backend(float moist, float temp, uint16_t ec, float ph, 
                          uint16_t N, uint16_t P, uint16_t K) {
    // JSON payload
    char json[256];
    snprintf(json, sizeof(json),
        "{"
        "\"device_id\":\"PICO_NPK_001\","
        "\"timestamp\":%ld,"
        "\"soil_moisture\":%.2f,"
        "\"soil_temperature\":%.2f,"
        "\"humidity\":0,"
        "\"light_intensity\":0,"
        "\"soil_ph\":%.2f,"
        "\"npk\":{"
        "\"nitrogen\":%u,"
        "\"phosphorus\":%u,"
        "\"potassium\":%u"
        "}"
        "}",
        time(NULL),
        moist, temp, ph, N, P, K
    );
    
    // Send HTTPS POST request
    // (See complete code file for full implementation)
    printf("Sent to backend: %s\n", json);
}
```

---

## 🚀 Step 5: Complete Workflow (Step by Step)

### On Your Friend's Laptop:

#### 5.1: Clone and Setup Environment
```bash
# Clone repository
git clone <your-repo-url>
cd SMART_app/Pico

# Set up Pico SDK environment
export PICO_SDK_PATH=~/pico/pico-sdk
export PICO_TOOLCHAIN_PATH=~/pico/pico-toolchain

# Create build directory
mkdir -p build && cd build
```

#### 5.2: Update WiFi Credentials
```bash
# Edit the source file
nano ../NPK_Interfacing.c

# Change these lines:
# #define WIFI_SSID "YOUR_ACTUAL_SSID"
# #define WIFI_PASSWORD "YOUR_PASSWORD"
# #define API_SERVER "your-backend-url.onrender.com"
```

#### 5.3: Build the Firmware
```bash
cmake .. -DPICO_BOARD=pico2w
make -j4

# Output: NPK_Interfacing.uf2 (ready to flash)
```

#### 5.4: Flash to Pico 2 W
```bash
# 1. Press BOOTSEL button on Pico
# 2. Connect USB to laptop
# 3. Copy .uf2 file to PICO volume that appears
cp NPK_Interfacing.uf2 /media/username/RPI-RP2/

# Or use picotool
picotool load NPK_Interfacing.uf2
```

#### 5.5: Monitor Serial Output
```bash
# On Linux/Mac (check connection)
ls /dev/ttyACM* 
# Should show /dev/ttyACM0

# Monitor with minicom/screen
screen /dev/ttyACM0 115200

# Or with Arduino IDE Serial Monitor
```

---

## 📊 Step 6: Expected Serial Output

When everything is working, you'll see:

```
ZTS-3002 Sensor Starting...
Connecting to WiFi: YOUR_SSID
Connected to WiFi! IP: 192.168.x.x

------ Sensor Readings ------
Moisture: 45.32 %
Temperature: 24.85 °C
EC: 1250 µS/cm
pH: 6.85
Nitrogen (N): 125 mg/kg
Phosphorus (P): 48 mg/kg
Potassium (K): 182 mg/kg
------------------------------

Sent to backend: {...json payload...}
HTTP Response: 200 OK
```

---

## 🌐 Step 7: Verify Backend Reception

### Check if data arrived at backend:

#### Option A: Using API directly
```bash
# SSH into your Render deployment or use terminal
curl https://your-backend.onrender.com/api/sensors/current

# Should return your NPK data:
{
  "timestamp": "2025-10-30T...",
  "soil_moisture": 45.32,
  "soil_temperature": 24.85,
  "soil_ph": 6.85,
  "npk": {
    "nitrogen": 125,
    "phosphorus": 48,
    "potassium": 182
  }
}
```

#### Option B: Check database directly
```bash
# On Render backend logs
select * from current_sensors;
select * from pico_sensor_data order by created_at desc limit 5;
```

---

## 💻 Step 8: View on Your Dashboard

### Access Dashboard
```
https://your-frontend-url.onrender.com
# Or localhost:3000 if running locally
```

### You'll see:
- ✅ **Live NPK values** (Nitrogen, Phosphorus, Potassium)
- ✅ **Soil Moisture** from sensor
- ✅ **Temperature** from sensor
- ✅ **pH Level** from sensor
- ✅ **Last Updated** timestamp
- ✅ **Data Source** indicator (current/last_received)

---

## 🔧 Step 9: Troubleshooting

### Issue 1: WiFi won't connect
```
Check: 
- WIFI_SSID and WIFI_PASSWORD are correct
- WiFi is 2.4GHz (Pico 2 W doesn't support 5GHz)
- Signal strength is adequate
- Try with -DPICO_CYW43_WL_DEFAULT_MAC for MAC address issues
```

### Issue 2: Backend connection fails (HTTP Error)
```
Check:
- Backend server is running and accessible
- URL is correct (https://, not http://)
- Device ID in code matches expectations
- JSON payload format matches API schema
```

### Issue 3: No data in dashboard
```
Check:
- Sensor is still working (validate with USB serial)
- POST request returns 200 OK
- Backend database has tables
- Frontend is fetching from correct API endpoint
- Check browser console for API errors
```

### Debug Serial Monitor Output
```bash
# If nothing appears:
# 1. Check baudrate (should be 115200 for USB)
# 2. Verify RP2040 is powered (LED should blink)
# 3. Try different USB cable/port
# 4. Check device manager for COM port (Windows)

# Enable verbose debug mode in code:
// Add before main loop
#define DEBUG 1
#ifdef DEBUG
printf("Debug: Entering main loop\n");
#endif
```

---

## 📋 Step 10: File Organization

Your final project structure should be:

```
SMART_app/
├── backend/
│   ├── main.py              (Already updated ✅)
│   └── requirements.txt
├── frontend/
│   └── public/index.html    (Dashboard)
└── Pico/
    ├── NPK_Interfacing.c    (Updated with WiFi ⬇️)
    ├── CMakeLists.txt       (Updated with WiFi libs ⬇️)
    ├── build/
    │   └── NPK_Interfacing.uf2  (Compiled firmware)
    └── pico_sdk_import.cmake
```

---

## 🎯 Quick Reference Checklist

- [ ] Edit WiFi credentials in C code
- [ ] Update CMakeLists.txt with WiFi libraries
- [ ] Build firmware with `cmake && make`
- [ ] Flash .uf2 to Pico 2 W
- [ ] Monitor serial output (should show WiFi connection)
- [ ] Verify API POST request reaches backend
- [ ] Check dashboard displays NPK data
- [ ] Confirm data refreshes every 2 seconds
- [ ] Test WiFi reconnection (disconnect/reconnect)
- [ ] Validate data format in database

---

## 🔗 Important URLs for Your Setup

| Service | URL | Purpose |
|---------|-----|---------|
| Backend API | `https://smart-agriculture-backend-y747.onrender.com` | POST sensor data |
| Current Data | `https://smart-agriculture-backend-y747.onrender.com/api/sensors/current` | Fetch live readings |
| Health Check | `https://smart-agriculture-backend-y747.onrender.com/health` | Verify backend online |
| Dashboard | `https://your-frontend-url.onrender.com` | View live data |

---

## 🎓 Next Steps (After WiFi Integration Works)

1. Add DHT22 (temperature/humidity) sensor
2. Add LDR (light sensor) 
3. Add soil moisture capacitive sensor
4. Implement persistent WiFi reconnection logic
5. Add data logging to SD card (optional)
6. Create historical graphs on dashboard

Would you like me to provide the complete updated NPK_Interfacing.c code?
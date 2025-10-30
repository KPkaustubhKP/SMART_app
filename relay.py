#!/usr/bin/env python3
"""
NPK Sensor Serial Relay - Forwards sensor data from Pico to cloud backend
Reads USB serial data from Pico, sends to FastAPI backend, updates dashboard
"""

import serial
import requests
import json
import time
import sys
from datetime import datetime

# ==================== CONFIGURATION ====================
SERIAL_PORT = 'COM3'  # Windows: COM3, COM4, etc
# SERIAL_PORT = '/dev/ttyACM0'  # Linux: /dev/ttyACM0, /dev/ttyACM1
# SERIAL_PORT = '/dev/tty.usbmodem1201'  # Mac
BAUD_RATE = 115200
BACKEND_URL = 'https://smart-agriculture-backend-y747.onrender.com/api/sensors/data'
DEVICE_ID = 'PICO_NPK_001'
TIMEOUT = 5  # Seconds

# ==================== FUNCTIONS ====================

def find_serial_port():
    """Try to find the Pico serial port automatically"""
    import platform
    
    if platform.system() == 'Windows':
        print("Windows detected. Check Device Manager for COM ports.")
        return None
    elif platform.system() == 'Darwin':  # macOS
        import glob
        ports = glob.glob('/dev/tty.usbmodem*')
        if ports:
            return ports[0]
    else:  # Linux
        import glob
        ports = glob.glob('/dev/ttyACM*')
        if ports:
            return ports[0]
    
    return None

def open_serial(port, baud):
    """Open and return serial connection"""
    try:
        ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)  # Wait for Pico to initialize
        print(f"✅ Serial port opened: {port}")
        return ser
    except serial.SerialException as e:
        print(f"❌ Failed to open serial port {port}: {e}")
        return None

def parse_sensor_data(line):
    """Parse sensor data from Pico format: DATA:|45.20|24.85|6.85|1250|125|48|182|"""
    try:
        parts = line.split('|')
        if len(parts) < 8:
            return None
        
        return {
            'moist': float(parts[1]),
            'temp': float(parts[2]),
            'ph': float(parts[3]),
            'ec': int(parts[4]),
            'N': int(parts[5]),
            'P': int(parts[6]),
            'K': int(parts[7])
        }
    except (ValueError, IndexError) as e:
        print(f"❌ Parse error: {e}")
        return None

def build_json_payload(sensor_data):
    """Build JSON payload for backend"""
    return {
        "device_id": DEVICE_ID,
        "timestamp": int(datetime.now().timestamp()),
        "soil_moisture": sensor_data['moist'],
        "soil_temperature": sensor_data['temp'],
        "humidity": 0,
        "light_intensity": 0,
        "soil_ph": sensor_data['ph'],
        "npk": {
            "nitrogen": sensor_data['N'],
            "phosphorus": sensor_data['P'],
            "potassium": sensor_data['K']
        }
    }

def send_to_backend(payload):
    """Send payload to backend API"""
    try:
        response = requests.post(
            BACKEND_URL,
            json=payload,
            timeout=TIMEOUT
        )
        
        if response.status_code in [200, 201]:
            print(f"✅ Backend: HTTP {response.status_code}")
            return True
        else:
            print(f"❌ Backend: HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:100]}")
            return False
    
    except requests.exceptions.Timeout:
        print(f"❌ Backend: Timeout")
        return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Backend: Connection failed")
        return False
    except Exception as e:
        print(f"❌ Backend: {e}")
        return False

def main():
    """Main relay loop"""
    print("\n" + "="*60)
    print("  NPK Sensor Serial Relay to Cloud")
    print("="*60)
    print(f"Serial Port: {SERIAL_PORT}")
    print(f"Baud Rate: {BAUD_RATE}")
    print(f"Backend: {BACKEND_URL}")
    print(f"Device ID: {DEVICE_ID}")
    print("="*60 + "\n")
    
    # Open serial port
    ser = open_serial(SERIAL_PORT, BAUD_RATE)
    if ser is None:
        print("❌ Cannot continue without serial connection")
        return
    
    try:
        data_count = 0
        error_count = 0
        start_time = time.time()
        
        print("📡 Listening for sensor data...\n")
        
        while True:
            try:
                # Read from serial
                if ser.in_waiting:
                    line = ser.readline().decode('utf-8').strip()
                    
                    if not line:
                        continue
                    
                    # Show debug lines
                    if not line.startswith("DATA:|"):
                        print(f"🔍 {line}")
                        continue
                    
                    print(f"📨 Raw: {line}")
                    
                    # Parse sensor data
                    sensor_data = parse_sensor_data(line)
                    if sensor_data is None:
                        error_count += 1
                        continue
                    
                    # Build payload
                    payload = build_json_payload(sensor_data)
                    
                    # Display parsed data
                    print(f"📊 Data: M={sensor_data['moist']:.2f}% T={sensor_data['temp']:.2f}°C pH={sensor_data['ph']:.2f} N={sensor_data['N']} P={sensor_data['P']} K={sensor_data['K']}")
                    
                    # Send to backend
                    if send_to_backend(payload):
                        data_count += 1
                    else:
                        error_count += 1
                    
                    # Show stats every 10 messages
                    if data_count % 10 == 0:
                        elapsed = time.time() - start_time
                        rate = data_count / elapsed
                        print(f"📈 Stats: Sent={data_count} Errors={error_count} Rate={rate:.2f}/sec\n")
            
            except KeyboardInterrupt:
                print("\n⏹️  Stopping relay...")
                break
            except UnicodeDecodeError:
                print("❌ Serial decode error")
                continue
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(1)
        
        # Final stats
        print("\n" + "="*60)
        print(f"✅ Relay stopped")
        print(f"   Total sent: {data_count}")
        print(f"   Errors: {error_count}")
        print("="*60 + "\n")
    
    finally:
        ser.close()
        print("✅ Serial port closed")

if __name__ == '__main__':
    # Check if port is provided as argument
    if len(sys.argv) > 1:
        SERIAL_PORT = sys.argv[1]
    
    main()

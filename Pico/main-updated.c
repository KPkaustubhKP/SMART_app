/**
 * Smart Agriculture IoT - Raspberry Pi Pico 2 W Main Code
 * 
 * This code connects to Wi-Fi, reads multiple sensors, and sends data
 * to a FastAPI backend server via HTTP POST requests in JSON format.
 * 
 * Sensors supported:
 * - DHT22 (Temperature & Humidity)
 * - Soil Moisture (Analog)
 * - LDR Light Sensor (Analog)
 * - Additional analog sensors can be easily added
 * 
 * Author: Smart Agriculture Team
 * Date: October 2024
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "lwip/apps/http_client.h"
#include "lwip/tcp.h"
#include "lwip/dns.h"
#include "hardware/adc.h"
#include "hardware/gpio.h"
#include "pico/time.h"

// ==================== CONFIGURATION ====================
// Wi-Fi Configuration - EDIT THESE VALUES
#define WIFI_SSID "SMART_wifi"
#define WIFI_PASSWORD "Allahhuakbar"

// Server Configuration - EDIT THIS URL
#define SERVER_HOST "smart-agriculture-backend-y747.onrender.com"  // Your deployed backend URL
#define SERVER_PORT 443  // Use 443 for HTTPS, 80 for HTTP
#define API_ENDPOINT "/api/sensors/data"  // New endpoint for receiving Pico data

// Pin Configurations
#define DHT22_PIN 15         // GPIO15 for DHT22 data pin
#define SOIL_MOISTURE_PIN 26 // ADC0 (GPIO26) for soil moisture sensor
#define LDR_PIN 27          // ADC1 (GPIO27) for light sensor
#define STATUS_LED_PIN 25   // Built-in LED for status indication

// Timing Configuration
#define SENSOR_READ_INTERVAL_MS 5000  // Read sensors every 5 seconds
#define HTTP_RETRY_DELAY_MS 2000     // Retry delay on HTTP failure
#define MAX_HTTP_RETRIES 3           // Maximum HTTP retry attempts

// Buffer sizes
#define HTTP_BUFFER_SIZE 1024
#define JSON_BUFFER_SIZE 512

// ==================== GLOBAL VARIABLES ====================
static char json_payload[JSON_BUFFER_SIZE];
static char http_response_buffer[HTTP_BUFFER_SIZE];
static bool wifi_connected = false;
static bool server_available = false;

// ==================== DHT22 FUNCTIONS ====================
// Simplified DHT22 implementation for this example
// In production, use a proper DHT22 library like pico_dht

typedef struct {
    float temperature;
    float humidity;
    bool valid;
} dht22_reading_t;

/**
 * Read DHT22 sensor data
 * This is a simplified implementation - use proper DHT22 library in production
 */
dht22_reading_t read_dht22() {
    dht22_reading_t reading = {0};
    
    // TODO: Implement proper DHT22 communication protocol
    // For now, return simulated values for testing
    reading.temperature = 25.5f;  // Simulated temperature
    reading.humidity = 60.0f;     // Simulated humidity
    reading.valid = true;
    
    return reading;
}

// ==================== ANALOG SENSOR FUNCTIONS ====================

/**
 * Initialize ADC for analog sensors
 */
void init_adc() {
    adc_init();
    adc_gpio_init(SOIL_MOISTURE_PIN);
    adc_gpio_init(LDR_PIN);
}

/**
 * Read soil moisture sensor (0-100%)
 * Returns percentage where 0% = very dry, 100% = very wet
 */
float read_soil_moisture() {
    adc_select_input(0);  // Select ADC0 (GPIO26)
    uint16_t raw = adc_read();
    
    // Convert to percentage (calibrate these values based on your sensor)
    // Typical values: dry soil ~65000, wet soil ~30000
    const uint16_t DRY_VALUE = 65000;
    const uint16_t WET_VALUE = 30000;
    
    float moisture = ((float)(DRY_VALUE - raw) / (DRY_VALUE - WET_VALUE)) * 100.0f;
    
    // Clamp to 0-100%
    if (moisture < 0) moisture = 0;
    if (moisture > 100) moisture = 100;
    
    return moisture;
}

/**
 * Read light sensor (0-100%)
 * Returns percentage where 0% = dark, 100% = bright
 */
float read_light_intensity() {
    adc_select_input(1);  // Select ADC1 (GPIO27)
    uint16_t raw = adc_read();
    
    // Convert to percentage (0-100%)
    float light = ((float)raw / 65535.0f) * 100.0f;
    
    return light;
}

// ==================== LED STATUS FUNCTIONS ====================

void status_led_init() {
    gpio_init(STATUS_LED_PIN);
    gpio_set_dir(STATUS_LED_PIN, GPIO_OUT);
}

void status_led_blink(int count, int delay_ms) {
    for (int i = 0; i < count; i++) {
        gpio_put(STATUS_LED_PIN, 1);
        sleep_ms(delay_ms);
        gpio_put(STATUS_LED_PIN, 0);
        sleep_ms(delay_ms);
    }
}

// ==================== JSON FUNCTIONS ====================

/**
 * Create JSON payload with sensor data
 */
void create_json_payload(dht22_reading_t dht, float soil_moisture, float light_intensity) {
    snprintf(json_payload, JSON_BUFFER_SIZE,
        "{"
        "\"device_id\":\"pico_w_001\","
        "\"timestamp\":%llu,"
        "\"soil_moisture\":%.2f,"
        "\"soil_temperature\":%.2f,"
        "\"humidity\":%.2f,"
        "\"light_intensity\":%.2f,"
        "\"soil_ph\":7.0,"  // Placeholder - add actual pH sensor if available
        "\"npk\":{"
            "\"nitrogen\":50,"
            "\"phosphorus\":30,"
            "\"potassium\":40"
        "}"
        "}",
        to_us_since_boot(get_absolute_time()) / 1000000,  // Unix timestamp approximation
        soil_moisture,
        dht.temperature,
        dht.humidity,
        light_intensity
    );
}

// ==================== HTTP CLIENT FUNCTIONS ====================

static void http_result_callback(void *arg, httpc_result_t httpc_result, 
                               u32_t rx_content_len, u32_t srv_res, err_t err) {
    printf("HTTP Result: %d, Server Response: %lu, Error: %d\n", 
           httpc_result, srv_res, err);
    
    if (httpc_result == HTTPC_RESULT_OK && srv_res == 200) {
        server_available = true;
        printf("✓ Data sent successfully to server\n");
        status_led_blink(2, 100);  // 2 quick blinks for success
    } else {
        server_available = false;
        printf("✗ Failed to send data to server\n");
        status_led_blink(5, 100);  // 5 quick blinks for error
    }
}

static err_t http_headers_callback(httpc_state_t *connection, void *arg,
                                 struct pbuf *hdr, u16_t hdr_len, u32_t content_len) {
    printf("HTTP Headers received, content length: %lu\n", content_len);
    return ERR_OK;
}

static err_t http_body_callback(void *arg, struct altcp_pcb *conn, 
                              struct pbuf *p, err_t err) {
    if (p != NULL) {
        // Copy response to buffer for debugging
        u16_t copy_len = p->tot_len;
        if (copy_len >= HTTP_BUFFER_SIZE) {
            copy_len = HTTP_BUFFER_SIZE - 1;
        }
        pbuf_copy_partial(p, http_response_buffer, copy_len, 0);
        http_response_buffer[copy_len] = '\0';
        
        printf("HTTP Response: %s\n", http_response_buffer);
        altcp_recved(conn, p->tot_len);
        pbuf_free(p);
    }
    return ERR_OK;
}

/**
 * Send HTTP POST request with sensor data
 */
bool send_sensor_data() {
    printf("Sending sensor data to server...\n");
    
    // Prepare HTTP client settings
    httpc_connection_t settings = {
        .result_fn = http_result_callback,
        .headers_done_fn = http_headers_callback,
        .use_proxy = 0
    };
    
    // Create HTTP headers
    const char* headers = 
        "Content-Type: application/json\r\n"
        "User-Agent: PicoW-SmartAgriculture/1.0\r\n"
        "Connection: close\r\n";
    
    // Resolve server IP
    ip_addr_t server_ip;
    err_t dns_err = dns_gethostbyname(SERVER_HOST, &server_ip, NULL, NULL);
    
    if (dns_err != ERR_OK) {
        printf("DNS resolution failed for %s\n", SERVER_HOST);
        return false;
    }
    
    // Send POST request
    httpc_state_t *connection = NULL;
    err_t err = httpc_post(&server_ip, SERVER_PORT, API_ENDPOINT, 
                          &settings, json_payload, strlen(json_payload),
                          http_body_callback, NULL, &connection);
    
    if (err != ERR_OK) {
        printf("HTTP POST failed with error: %d\n", err);
        return false;
    }
    
    return true;
}

// ==================== WIFI FUNCTIONS ====================

/**
 * Initialize Wi-Fi and connect to network
 */
bool wifi_init_and_connect() {
    printf("Initializing Wi-Fi...\n");
    
    if (cyw43_arch_init()) {
        printf("✗ Wi-Fi init failed\n");
        return false;
    }
    
    cyw43_arch_enable_sta_mode();
    printf("Connecting to Wi-Fi network: %s\n", WIFI_SSID);
    
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, 
                                          CYW43_AUTH_WPA2_AES_PSK, 10000)) {
        printf("✗ Failed to connect to Wi-Fi\n");
        return false;
    }
    
    printf("✓ Connected to Wi-Fi successfully\n");
    
    // Print IP address
    const ip4_addr_t *ip = netif_ip4_addr(netif_default);
    printf("IP Address: %s\n", ip4addr_ntoa(ip));
    
    wifi_connected = true;
    return true;
}

// ==================== TEST FUNCTIONS ====================

/**
 * Test HTTP connectivity with a simple ping
 */
bool test_server_connectivity() {
    printf("\n=== Testing Server Connectivity ===\n");
    
    // Create simple test payload
    const char* test_payload = "{\"test\":\"ping\",\"device\":\"pico_w\"}";
    
    // Temporarily use test payload
    strcpy(json_payload, test_payload);
    
    bool result = send_sensor_data();
    
    printf("Server connectivity test: %s\n", result ? "PASSED" : "FAILED");
    return result;
}

// ==================== MAIN FUNCTIONS ====================

/**
 * Initialize all sensors and peripherals
 */
void init_sensors() {
    printf("Initializing sensors...\n");
    
    // Initialize ADC for analog sensors
    init_adc();
    
    // Initialize DHT22 pin
    gpio_init(DHT22_PIN);
    gpio_set_dir(DHT22_PIN, GPIO_IN);
    gpio_pull_up(DHT22_PIN);
    
    // Initialize status LED
    status_led_init();
    
    printf("✓ All sensors initialized\n");
}

/**
 * Read all sensors and print values
 */
void read_and_display_sensors() {
    printf("\n=== Reading Sensors ===\n");
    
    // Read DHT22
    dht22_reading_t dht = read_dht22();
    
    // Read analog sensors
    float soil_moisture = read_soil_moisture();
    float light_intensity = read_light_intensity();
    
    // Display readings
    printf("Temperature: %.2f°C\n", dht.temperature);
    printf("Humidity: %.2f%%\n", dht.humidity);
    printf("Soil Moisture: %.2f%%\n", soil_moisture);
    printf("Light Intensity: %.2f%%\n", light_intensity);
    
    // Create JSON payload
    create_json_payload(dht, soil_moisture, light_intensity);
    printf("JSON Payload: %s\n", json_payload);
}

/**
 * Main application loop
 */
void main_loop() {
    printf("\n=== Starting Main Loop ===\n");
    
    absolute_time_t last_sensor_read = get_absolute_time();
    int retry_count = 0;
    
    while (true) {
        // Check if it's time to read sensors
        if (absolute_time_diff_us(last_sensor_read, get_absolute_time()) >= 
            SENSOR_READ_INTERVAL_MS * 1000) {
            
            // Read all sensors
            read_and_display_sensors();
            
            // Send data to server if Wi-Fi is connected
            if (wifi_connected) {
                bool success = send_sensor_data();
                
                if (success) {
                    retry_count = 0;  // Reset retry counter on success
                } else {
                    retry_count++;
                    printf("HTTP send failed, retry %d/%d\n", retry_count, MAX_HTTP_RETRIES);
                    
                    if (retry_count >= MAX_HTTP_RETRIES) {
                        printf("Max retries reached, will try again next cycle\n");
                        retry_count = 0;
                    } else {
                        sleep_ms(HTTP_RETRY_DELAY_MS);
                        continue;  // Skip updating last_sensor_read to retry immediately
                    }
                }
            } else {
                printf("Wi-Fi not connected, skipping server upload\n");
            }
            
            last_sensor_read = get_absolute_time();
        }
        
        // Small delay to prevent busy waiting
        sleep_ms(100);
        
        // Handle Wi-Fi events
        cyw43_arch_poll();
    }
}

/**
 * Main function
 */
int main() {
    // Initialize standard I/O
    stdio_init_all();
    
    // Wait for serial connection (for debugging)
    sleep_ms(3000);
    
    printf("\n");
    printf("========================================\n");
    printf("  Smart Agriculture - Pico W IoT Node  \n");
    printf("========================================\n");
    printf("Firmware Version: 1.0\n");
    printf("Build Date: %s %s\n", __DATE__, __TIME__);
    printf("Wi-Fi Network: %s\n", WIFI_SSID);
    printf("Backend Server: %s\n", SERVER_HOST);
    printf("========================================\n\n");
    
    // Initialize sensors
    init_sensors();
    
    // Initialize and connect to Wi-Fi
    if (!wifi_init_and_connect()) {
        printf("✗ Startup failed - Wi-Fi connection failed\n");
        while (true) {
            status_led_blink(10, 200);  // Error pattern
            sleep_ms(2000);
        }
    }
    
    // Test server connectivity
    sleep_ms(2000);  // Wait for network to stabilize
    test_server_connectivity();
    
    // Success indication
    status_led_blink(3, 500);  // 3 slow blinks for success
    
    printf("\n✓ Initialization complete - starting main loop\n");
    printf("Sending data to: %s%s\n", SERVER_HOST, API_ENDPOINT);
    
    // Start main application loop
    main_loop();
    
    return 0;
}

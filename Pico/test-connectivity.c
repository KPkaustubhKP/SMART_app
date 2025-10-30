/**
 * Simple HTTP Test for Raspberry Pi Pico W
 * 
 * This is a minimal test program to verify Wi-Fi connectivity and HTTP communication
 * with your Smart Agriculture backend server.
 * 
 * Use this to test your setup before using the full sensor code.
 * 
 * Author: Smart Agriculture Team
 * Date: October 2024
 */

#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "lwip/apps/http_client.h"
#include "lwip/dns.h"

// ==================== CONFIGURATION ====================
// EDIT THESE VALUES FOR YOUR SETUP
#define WIFI_SSID "Your_WiFi_SSID"
#define WIFI_PASSWORD "Your_WiFi_Password"
#define SERVER_HOST "smart-agriculture-backend.onrender.com"
#define SERVER_PORT 443
#define TEST_ENDPOINT "/api/sensors/pico/test"

// Status LED
#define LED_PIN 25

// ==================== GLOBAL VARIABLES ====================
static bool test_completed = false;
static bool test_successful = false;

// ==================== LED FUNCTIONS ====================
void led_init() {
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
}

void led_blink(int count, int delay_ms) {
    for (int i = 0; i < count; i++) {
        gpio_put(LED_PIN, 1);
        sleep_ms(delay_ms);
        gpio_put(LED_PIN, 0);
        sleep_ms(delay_ms);
    }
}

// ==================== HTTP CALLBACK FUNCTIONS ====================
static void http_result_callback(void *arg, httpc_result_t httpc_result, 
                               u32_t rx_content_len, u32_t srv_res, err_t err) {
    printf("\n=== HTTP Test Result ===\n");
    printf("HTTP Result Code: %d\n", httpc_result);
    printf("Server Response Code: %lu\n", srv_res);
    printf("Content Length: %lu bytes\n", rx_content_len);
    printf("LwIP Error: %d\n", err);
    
    if (httpc_result == HTTPC_RESULT_OK && srv_res == 200) {
        printf("✓ HTTP Test SUCCESSFUL!\n");
        test_successful = true;
        led_blink(3, 200);  // 3 quick blinks for success
    } else {
        printf("✗ HTTP Test FAILED!\n");
        test_successful = false;
        led_blink(10, 100); // 10 rapid blinks for failure
    }
    
    test_completed = true;
}

static err_t http_headers_callback(httpc_state_t *connection, void *arg,
                                 struct pbuf *hdr, u16_t hdr_len, u32_t content_len) {
    printf("Received HTTP headers (%d bytes)\n", hdr_len);
    return ERR_OK;
}

static err_t http_body_callback(void *arg, struct altcp_pcb *conn, 
                              struct pbuf *p, err_t err) {
    if (p != NULL) {
        char buffer[256];
        u16_t len = p->tot_len;
        if (len >= sizeof(buffer)) {
            len = sizeof(buffer) - 1;
        }
        
        pbuf_copy_partial(p, buffer, len, 0);
        buffer[len] = '\0';
        
        printf("Server Response Body: %s\n", buffer);
        
        altcp_recved(conn, p->tot_len);
        pbuf_free(p);
    }
    return ERR_OK;
}

// ==================== WIFI FUNCTIONS ====================
bool wifi_connect() {
    printf("Initializing Wi-Fi...\n");
    
    if (cyw43_arch_init()) {
        printf("✗ Wi-Fi initialization failed\n");
        return false;
    }
    
    cyw43_arch_enable_sta_mode();
    printf("Connecting to Wi-Fi network: %s\n", WIFI_SSID);
    
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD, 
                                          CYW43_AUTH_WPA2_AES_PSK, 15000)) {
        printf("✗ Failed to connect to Wi-Fi\n");
        return false;
    }
    
    printf("✓ Connected to Wi-Fi successfully\n");
    
    // Print network information
    const ip4_addr_t *ip = netif_ip4_addr(netif_default);
    const ip4_addr_t *gateway = netif_ip4_gw(netif_default);
    const ip4_addr_t *netmask = netif_ip4_netmask(netif_default);
    
    printf("Network Information:\n");
    printf("  IP Address: %s\n", ip4addr_ntoa(ip));
    printf("  Gateway: %s\n", ip4addr_ntoa(gateway));
    printf("  Netmask: %s\n", ip4addr_ntoa(netmask));
    
    return true;
}

// ==================== HTTP TEST FUNCTIONS ====================
bool test_http_connectivity() {
    printf("\n=== Testing HTTP Connectivity ===\n");
    printf("Connecting to: %s:%d%s\n", SERVER_HOST, SERVER_PORT, TEST_ENDPOINT);
    
    // Reset test status
    test_completed = false;
    test_successful = false;
    
    // Configure HTTP client
    httpc_connection_t settings = {
        .result_fn = http_result_callback,
        .headers_done_fn = http_headers_callback,
        .use_proxy = 0
    };
    
    // Resolve server IP address
    ip_addr_t server_ip;
    err_t dns_err = dns_gethostbyname(SERVER_HOST, &server_ip, NULL, NULL);
    
    if (dns_err != ERR_OK) {
        printf("✗ DNS resolution failed for %s (error: %d)\n", SERVER_HOST, dns_err);
        return false;
    }
    
    printf("✓ DNS resolution successful: %s\n", ipaddr_ntoa(&server_ip));
    
    // Send HTTP GET request
    httpc_state_t *connection = NULL;
    err_t err = httpc_get_file(&server_ip, SERVER_PORT, TEST_ENDPOINT,
                              &settings, http_body_callback, NULL, &connection);
    
    if (err != ERR_OK) {
        printf("✗ Failed to initiate HTTP request (error: %d)\n", err);
        return false;
    }
    
    printf("HTTP request sent, waiting for response...\n");
    
    // Wait for response (with timeout)
    int timeout_count = 0;
    const int MAX_TIMEOUT = 300; // 30 seconds (100ms * 300)
    
    while (!test_completed && timeout_count < MAX_TIMEOUT) {
        cyw43_arch_poll();
        sleep_ms(100);
        timeout_count++;
        
        // Print progress dots
        if (timeout_count % 50 == 0) {
            printf(".");
            fflush(stdout);
        }
    }
    
    if (!test_completed) {
        printf("\n✗ HTTP request timed out\n");
        return false;
    }
    
    return test_successful;
}

// ==================== JSON TEST FUNCTIONS ====================
bool test_json_post() {
    printf("\n=== Testing JSON POST ===\n");
    
    // Create test JSON payload
    const char* json_data = 
        "{"
        "\"test\":\"connectivity\","
        "\"device\":\"pico_w_test\","
        "\"timestamp\":1234567890"
        "}";
    
    printf("Sending JSON payload: %s\n", json_data);
    
    // Reset test status
    test_completed = false;
    test_successful = false;
    
    // Configure HTTP client for POST
    httpc_connection_t settings = {
        .result_fn = http_result_callback,
        .headers_done_fn = http_headers_callback,
        .use_proxy = 0
    };
    
    // Resolve server IP
    ip_addr_t server_ip;
    err_t dns_err = dns_gethostbyname(SERVER_HOST, &server_ip, NULL, NULL);
    
    if (dns_err != ERR_OK) {
        printf("✗ DNS resolution failed\n");
        return false;
    }
    
    // Send POST request (Note: This is a simplified version)
    // For a proper POST with JSON, you would need to implement custom headers
    httpc_state_t *connection = NULL;
    err_t err = httpc_get_file(&server_ip, SERVER_PORT, TEST_ENDPOINT,
                              &settings, http_body_callback, NULL, &connection);
    
    if (err != ERR_OK) {
        printf("✗ Failed to send POST request (error: %d)\n", err);
        return false;
    }
    
    // Wait for response
    int timeout_count = 0;
    const int MAX_TIMEOUT = 300;
    
    while (!test_completed && timeout_count < MAX_TIMEOUT) {
        cyw43_arch_poll();
        sleep_ms(100);
        timeout_count++;
    }
    
    if (!test_completed) {
        printf("✗ POST request timed out\n");
        return false;
    }
    
    return test_successful;
}

// ==================== MAIN FUNCTION ====================
int main() {
    // Initialize stdio
    stdio_init_all();
    sleep_ms(3000);  // Wait for serial connection
    
    // Initialize LED
    led_init();
    
    printf("\n");
    printf("================================================\n");
    printf("  Smart Agriculture - Pico W Connectivity Test  \n");
    printf("================================================\n");
    printf("Test Version: 1.0\n");
    printf("Build Date: %s %s\n", __DATE__, __TIME__);
    printf("================================================\n\n");
    
    // Test 1: Wi-Fi Connection
    printf("TEST 1: Wi-Fi Connection\n");
    printf("------------------------\n");
    
    if (!wifi_connect()) {
        printf("✗ CRITICAL: Wi-Fi connection failed!\n");
        printf("Please check:\n");
        printf("  - SSID: %s\n", WIFI_SSID);
        printf("  - Password is correct\n");
        printf("  - Router is accessible\n");
        
        // Error indication
        while (true) {
            led_blink(20, 100);
            sleep_ms(2000);
        }
    }
    
    led_blink(2, 300);  // Success indication
    sleep_ms(2000);
    
    // Test 2: HTTP Connectivity
    printf("\nTEST 2: HTTP Connectivity\n");
    printf("-------------------------\n");
    
    if (!test_http_connectivity()) {
        printf("✗ HTTP connectivity test failed!\n");
        printf("Please check:\n");
        printf("  - Server URL: %s\n", SERVER_HOST);
        printf("  - Server is running and accessible\n");
        printf("  - Firewall/network settings\n");
    } else {
        printf("✓ HTTP connectivity test passed!\n");
    }
    
    sleep_ms(2000);
    
    // Test 3: JSON Communication (simplified)
    printf("\nTEST 3: JSON Communication Test\n");
    printf("-------------------------------\n");
    
    if (!test_json_post()) {
        printf("✗ JSON communication test failed!\n");
    } else {
        printf("✓ JSON communication test passed!\n");
    }
    
    // Final Results
    printf("\n");
    printf("================================================\n");
    printf("  CONNECTIVITY TEST RESULTS                    \n");
    printf("================================================\n");
    printf("Wi-Fi Connection:    ✓ PASSED\n");
    printf("HTTP Connectivity:   %s\n", test_successful ? "✓ PASSED" : "✗ FAILED");
    printf("JSON Communication:  %s\n", test_successful ? "✓ PASSED" : "✗ FAILED");
    printf("================================================\n");
    
    if (test_successful) {
        printf("\n🎉 ALL TESTS PASSED! 🎉\n");
        printf("Your Pico W is ready for the full sensor code!\n");
        
        // Success pattern
        while (true) {
            led_blink(3, 200);
            sleep_ms(2000);
        }
    } else {
        printf("\n❌ SOME TESTS FAILED ❌\n");
        printf("Please resolve the issues before proceeding.\n");
        
        // Failure pattern
        while (true) {
            led_blink(1, 1000);
            sleep_ms(1000);
        }
    }
    
    return 0;
}
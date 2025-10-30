/**
 * DHT22 Library Header File
 * 
 * Header file for the DHT22 temperature and humidity sensor library
 * for Raspberry Pi Pico W.
 * 
 * Author: Smart Agriculture Team
 * Date: October 2024
 */

#ifndef DHT22_H
#define DHT22_H

#include <stdint.h>
#include <stdbool.h>

// Structure to hold DHT22 reading
typedef struct {
    float temperature;  // Temperature in Celsius
    float humidity;     // Humidity in percentage
    bool valid;         // True if reading is valid
} dht22_reading_t;

/**
 * Initialize DHT22 sensor on specified GPIO pin
 * 
 * @param pin GPIO pin number where DHT22 data line is connected
 */
void dht22_init(uint pin);

/**
 * Read temperature and humidity from DHT22 sensor
 * 
 * @param pin GPIO pin number where DHT22 data line is connected
 * @return dht22_reading_t structure containing temperature, humidity, and validity
 */
dht22_reading_t dht22_read(uint pin);

/**
 * Read DHT22 with automatic retries on failure
 * 
 * @param pin GPIO pin number where DHT22 data line is connected
 * @param max_retries Maximum number of retry attempts
 * @return dht22_reading_t structure containing temperature, humidity, and validity
 */
dht22_reading_t dht22_read_with_retry(uint pin, int max_retries);

#endif // DHT22_H
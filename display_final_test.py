import network
import socket
import struct
import time
from machine import I2C, Pin, ADC, SPI
from ili9341 import Display, color565

# ---------------------- SEN55 and MQ7 Sensor Setup ---------------------- #

# Initialize I2C for SEN55 (GP4 = SDA, GP5 = SCL)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
SEN55_ADDR = 0x69  # SEN55 I2C Address

# Initialize MQ7 on GP26 (ADC0)
mq7 = ADC(Pin(26))

# Commands for SEN55
CMD_START_MEASUREMENT = bytearray([0x00, 0x21])
CMD_READ_VALUES = bytearray([0x03, 0xC4])

# CRC-8 calculation (Polynomial 0x31)
def crc8(data):
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc <<= 1
            crc &= 0xFF  # Keep 8-bit
    return crc

# Function to start SEN55 measurement
def start_measurement():
    try:
        i2c.writeto(SEN55_ADDR, CMD_START_MEASUREMENT)
        print("✅ SEN55 Measurement Started")
    except Exception as e:
        print("⚠️ Error starting measurement:", e)

# Function to read and decode SEN55 data
def read_sen55():
    try:
        i2c.writeto(SEN55_ADDR, CMD_READ_VALUES)
        time.sleep(0.1)
        data = i2c.readfrom(SEN55_ADDR, 24)

        values = []
        for i in range(0, 24, 3):
            raw_bytes = data[i:i+2]
            crc_received = data[i+2]
            if crc8(raw_bytes) != crc_received:
                print(f"⚠️ Checksum error at index {i//3}! Skipping...")
                values.append(None)
            else:
                value = struct.unpack(">h", raw_bytes)[0]
                values.append(value)

        # Convert raw values to proper units (per your sensor datasheet)
        pm1_0    = values[0] / 10.0 if values[0] is not None else None
        pm2_5    = values[1] / 10.0 if values[1] is not None else None
        pm10     = values[3] / 10.0 if values[3] is not None else None
        humidity = values[4] / 100.0 if values[4] is not None else None
        temperature = values[5] / 200.0 if values[5] is not None else None
        voc_index = values[6] / 10.0 if values[6] is not None else None
        nox_index = values[7] / 10.0 if values[7] is not None else None

        return pm1_0, pm2_5, pm10, humidity, temperature, voc_index, nox_index

    except Exception as e:
        print("⚠️ Error reading SEN55:", e)
        return None, None, None, None, None, None, None

# Function to read CO concentration from MQ7 sensor
def read_mq7():
    raw_value = mq7.read_u16()  # ADC 16-bit reading
    voltage = (raw_value / 65535) * 3.3  # Convert to voltage (0-3.3V)
    co_ppm = max(0, (voltage - 0.2) * 100)  # Example scaling; adjust via calibration
    return co_ppm

# Helper function to get full sensor readings (8 values)
def get_sensor_readings():
    sen55_values = read_sen55()  # Returns 7 values
    co = read_mq7()             # Get CO value from MQ7 sensor
    # If SEN55 reading failed, return all Nones
    if sen55_values[0] is None:
        return (None,) * 8
    return sen55_values + (co,)

# ---------------------- ILI9341 Display Setup ---------------------- #

def update_display(display, sensor_data, indices):
    """
    Clear the display and show sensor readings for the given indices.
    Uses the built-in 8x8 font via draw_text8x8().
    
    Args:
        display (Display): The ILI9341 display object.
        sensor_data (tuple): Tuple containing 8 sensor readings.
        indices (list): List of indices in sensor_data to display.
    """
    display.clear(color565(0, 0, 0))  # Clear display to black
    y = 10  # Starting y coordinate for text
    for i in indices:
        if i == 0:
            text = "PM1.0: {} ug/m3".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 1:
            text = "PM2.5: {} ug/m3".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 2:
            text = "PM10: {} ug/m3".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 3:
            text = "Humidity: {}%".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 4:
            text = "Temp: {} C".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 5:
            text = "VOC idx: {}".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 6:
            text = "NOx idx: {}".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        elif i == 7:
            text = "CO: {} ppm".format(sensor_data[i] if sensor_data[i] is not None else "ERR")
        else:
            text = "Unknown"
        # Use draw_text8x8(x, y, text, color, background)
        display.draw_text8x8(10, y, text, color565(255, 255, 255))
        y += 10  # Increment y; adjust spacing as needed

# ---------------------- Main Loop ---------------------- #

def main():
    # Start SEN55 measurement
    start_measurement()
    time.sleep(2)  # Allow sensor to settle
    
    # Initialize SPI and display (using your library)
    spi = SPI(1, baudrate=10000000, sck=Pin(14), mosi=Pin(15))
    display = Display(spi, cs=Pin(17), dc=Pin(6), rst=Pin(7))
    
    while True:
        # Fetch sensor readings (8 values: 7 from SEN55, 1 from MQ7)
        sensor_values = get_sensor_readings()
        
        # Display first 4 readings for 5 seconds:
        # PM1.0, PM2.5, PM10, Humidity
        update_display(display, sensor_values, [0, 1, 2, 3])
        time.sleep(5)
        
        # Display next 4 readings for 5 seconds:
        # Temperature, VOC index, NOx index, CO
        update_display(display, sensor_values, [4, 5, 6, 7])
        time.sleep(5)

# Run the main loop
main()

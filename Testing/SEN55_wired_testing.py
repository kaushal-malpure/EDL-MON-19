from machine import I2C, Pin
import time
import struct

# Initialize I2C on Pico W (I2C0 with GP4 = SDA, GP5 = SCL)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=100000)
SEN55_ADDR = 0x69  # Default I²C address for SEN55

# Commands
CMD_START_MEASUREMENT = bytearray([0x00, 0x21])
CMD_READ_VALUES = bytearray([0x03, 0xC4])

# CRC-8 calculation (Polynomial 0x31)
def crc8(data):
    """Calculates CRC-8 checksum for 2 bytes using polynomial 0x31."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc <<= 1
            crc &= 0xFF  # Keep it 8-bit
    return crc

# Function to start measurement
def start_measurement():
    """Sends command to start continuous measurement on SEN55."""
    try:
        i2c.writeto(SEN55_ADDR, CMD_START_MEASUREMENT)
        print("✅ SEN55 Measurement Started")
    except Exception as e:
        print("⚠️ Error starting measurement:", e)

# Function to read and decode SEN55 data (Big-Endian int16)
def read_sen55():
    """Reads air quality data from SEN55 and verifies checksum."""
    try:
        # Request measurement data
        i2c.writeto(SEN55_ADDR, CMD_READ_VALUES)
        time.sleep(0.1)  # Give sensor time to respond

        # Read 24 bytes (Each value is 2 bytes + 1 checksum byte)
        data = i2c.readfrom(SEN55_ADDR, 24)

        # Extract values using Big-Endian int16 format
        values = []
        for i in range(0, 24, 3):  # Step by 3 (2 data bytes + 1 checksum)
            raw_bytes = data[i:i+2]  # Extract 2 data bytes
            crc = data[i+2]  # Extract checksum byte

            # Verify checksum
            if crc8(raw_bytes) != crc:
                print(f"⚠️ Checksum error at index {i//3}! Skipping...")
                values.append(None)  # Mark as invalid
            else:
                # Convert Big-Endian int16 to integer
                value = struct.unpack(">h", raw_bytes)[0]
                values.append(value)

        # Decode sensor values (apply scaling)
        pm1_0 = values[0] / 10.0 if values[0] is not None else None
        pm2_5 = values[1] / 10.0 if values[1] is not None else None
        pm4_0 = values[2] / 10.0 if values[2] is not None else None
        pm10  = values[3] / 10.0 if values[3] is not None else None
        humidity = values[4] / 100.0 if values[4] is not None else None
        temperature = values[5] / 200.0 if values[5] is not None else None
        voc_index = values[6] / 10.0 if values[6] is not None else None
        nox_index = values[7] / 10.0 if values[7] is not None else None

        return pm1_0, pm2_5, pm4_0, pm10, humidity, temperature, voc_index, nox_index

    except Exception as e:
        print("⚠️ Error reading SEN55:", e)
        return None, None, None, None, None, None, None, None

# Start Measurement Process
start_measurement()
time.sleep(2)  # Allow time to initialize

# Read Data Continuously
while True:
    pm1_0, pm2_5, pm4_0, pm10, humidity, temperature, voc, nox = read_sen55()
    
    if pm1_0 is not None:
        print(f"🌫️ PM1.0: {pm1_0} µg/m³ | PM2.5: {pm2_5} µg/m³ | PM10: {pm10} µg/m³")
        print(f"💧 Humidity: {humidity}% | 🌡️ Temperature: {temperature}°C")
        print(f"🌿 VOC Index: {voc} | 🚗 NOx Index: {nox}")
    
    time.sleep(2)  # Read every 2 seconds
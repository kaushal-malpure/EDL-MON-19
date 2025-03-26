import network
import socket

# Create Wi-Fi access point
ap = network.WLAN(network.AP_IF)
ap.config(essid="PicoW_Network", password="12345678")  # Set SSID & password
ap.active(True)  # Enable AP mode

print("Pico W Access Point Created!")
while not ap.active():
    pass  # Wait until the AP is active

print("Access Point IP Address:", ap.ifconfig()[0])

# Create a simple webpage
html = """<!DOCTYPE html>
<html>
<head><title>Pico W Server</title></head>
<body><h1>Hello, World!</h1></body>
</html>
"""

# Start a web server
addr = ("0.0.0.0", 80)
s = socket.socket()
s.bind(addr)
s.listen(5)
print("Web Server Started! Connect to:", ap.ifconfig()[0])

while True:
    conn, addr = s.accept()
    print("Client connected from", addr)
    request = conn.recv(1024)  # Read the request
    conn.send("HTTP/1.1 200 OK\nContent-Type: text/html\n\n" + html)  # Send response
    conn.close()

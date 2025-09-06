import network
import time

sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('${WiFiSSID}', '${WiFiPassword}')

for x in range(5):
    if sta_if.isconnected():
        break
    time.sleep(1)

if sta_if.isconnected():
    print("Network config:", sta_if.ifconfig())

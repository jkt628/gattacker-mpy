import json
import re
from typing import Dict

import aioble
from aioble.central import ScanResult
from microdot import Microdot
from microdot.websocket import with_websocket
from micropython import const

_ADV_TYPE_MANUFACTURER = const(0xFF)
hexVal = re.compile("0x([0-9A-Fa-f]+)")
onlyHexName = re.compile(
    "^[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]$"
)


class Peripheral(ScanResult):
    def __init__(self, parent):
        self.device = parent.device
        self.adv_data = parent.adv_data
        self.resp_data = parent.resp_data
        self.rssi = parent.rssi
        self.connectable = parent.connectable
        self._name = parent.name()
        if not self._name:
            self._name = parent.device.addr_hex().replace(":", "").lower()

    def name(self):
        return self._name

    def set_name(self, name):
        if name and self._name != name and onlyHexName.match(self._name):
            self._name = name


peripherals: Dict[str, Peripheral] = {}


def PrettyUUID(uuid):
    value = str(uuid)
    match = hexVal.search(value)
    if match:
        return int(match.group(1), 16)
    return value.replace("UUID('", "").replace("')", "")


async def send(ws, data):
    payload = json.dumps(data)
    print(payload)
    await ws.send(payload)


def web_server():
    app = Microdot()

    @app.route("/")
    @with_websocket
    async def ws(request, ws):
        print("Connect from", request.client_addr)
        await send(
            ws,
            {
                "type": "stateChange",
                "state": "poweredOn",
            },
        )
        cancel = None
        while True:
            raw = await ws.receive()
            data = json.loads(raw)
            print(data)

            action = data["action"]
            if action == "startScanning":
                cancel = None
                await send(
                    ws,
                    {
                        "type": "startScanning",
                    },
                )
                async with aioble.scan(15000, interval_us=30000, window_us=30000, active=True) as scanner:
                    async for result in scanner:
                        if cancel:
                            await scanner.cancel()
                            cancel = None
                            break

                        # scan sometimes returns incomplete results, especially result.name().
                        # the strategy is to build up peripherals and send updates as we get them.

                        # convert all the things
                        peripheral = Peripheral(result)
                        address = peripheral.device.addr_hex()
                        peripheralId = address.replace(":", "").lower()
                        if peripheralId in peripherals:
                            peripheral = peripherals[peripheralId]
                        else:
                            peripherals[peripheralId] = peripheral
                        peripheral.set_name(result.name())
                        serviceUuids = [PrettyUUID(x) for x in result.services()]
                        if not serviceUuids:
                            continue
                        manufacturer = b""
                        for x in result._decode_field(_ADV_TYPE_MANUFACTURER):
                            manufacturer += x.hex()

                        await send(
                            ws,
                            {
                                "type": "discover",
                                "peripheralId": peripheralId,
                                "name": peripheral.name(),
                                "rssi": result.rssi,
                                "address": address,
                                "connectable": result.connectable,
                                "advertisement": {
                                    "localName": peripheral.name(),
                                    "serviceUuids": serviceUuids,
                                    "manufacturerData": manufacturer,
                                },
                            },
                        )
                await send(
                    ws,
                    {
                        "type": "stopScanning",
                    },
                )
            elif action == "stopScanning":
                cancel = True

    app.run(port=0xb1e, debug=True)


if __name__ == "__main__":
    web_server()

import asyncio
import json
import re
from typing import Dict, Generator

import aioble
import bluetooth
from aioble.central import ScanResult
from microdot import Microdot
from microdot.websocket import with_websocket
from micropython import const

try:
    from debug import DEBUG
except ImportError:
    DEBUG = False

# see https://docs.micropython.org/en/latest/library/micropython.html#micropython.const
# from aioble.central import _ADV_TYPE_MANUFACTURER
_ADV_TYPE_MANUFACTURER = const(0xFF)
# from aioble.client import _FLAG_READ, ...
_FLAG_READ = const(0x0002)
_FLAG_WRITE_NO_RESPONSE = const(0x0004)
_FLAG_WRITE = const(0x0008)
_FLAG_NOTIFY = const(0x0010)
_FLAG_INDICATE = const(0x0020)

Properties = {
    _FLAG_READ: "read",
    _FLAG_WRITE_NO_RESPONSE: "writeWithoutResponse",
    _FLAG_WRITE: "write",
    _FLAG_NOTIFY: "notify",
    _FLAG_INDICATE: "indicate",
}

onlyHexName = re.compile(
    "^[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]$"
)


def debug(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)


def lowest_set_bit(n: int) -> Generator[int, None, None]:
    """
    A generator for the lowest set bit(s) of n.
    """
    while n != 0:
        i = n & -n
        n &= ~i
        yield i


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
    return str(uuid).replace("UUID(", "", 1).replace("'", "").replace("0x", "", 1).replace(")", "", 1)


async def send(ws, data):
    payload = json.dumps(data)
    debug(payload)
    await ws.send(payload)


def web_server():
    print("DEBUG =", DEBUG)
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
            debug(data)

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
                return  # close websocket
            elif action == "stopScanning":
                cancel = True
            elif action == "explore":
                rsp = {
                    "type": "explore",
                    "peripheralId": data["peripheralId"],
                    "state": "missing",
                }
                try:
                    peripheralId = data["peripheralId"]
                    peripheral = peripherals[peripheralId]
                except KeyError:
                    await send(ws, rsp)
                    return
                rsp["state"] = "start"
                await send(ws, rsp)
                rsp["state"] = "failed"
                try:
                    connection = await peripheral.device.connect()
                except asyncio.TimeoutError:
                    rsp["error"] = str(asyncio.TimeoutError)
                    await send(ws, rsp)
                    return
                async with connection:
                    # aioble allows only one discovery at a time so collect all the services then collect characteristics for each
                    services = []
                    async for service in connection.services():
                        services.append(
                            {
                                "startHandle": service._start_handle,
                                "endHandle": service._end_handle,
                                "uuid": PrettyUUID(service.uuid),
                                "characteristics": [],
                            }
                        )
                    debug(services)
                    for s in services:
                        uuid = s["uuid"]
                        if len(uuid) <= 4:
                            uuid = int(uuid, 16)
                        service = await connection.service(bluetooth.UUID(uuid))
                        debug(service)
                        async for characteristic in service.characteristics():
                            debug(characteristic)
                            s["characteristics"].append(
                                {
                                    "valueHandle": characteristic._value_handle,
                                    "endHandle": characteristic._end_handle,
                                    "uuid": PrettyUUID(characteristic.uuid),
                                    "properties": [Properties[x] for x in lowest_set_bit(characteristic.properties)],
                                }
                            )
                    rsp["state"] = "finished"
                    rsp["servicesJsonData"] = services
                    await send(ws, rsp)
            else:
                await send(
                    ws,
                    {
                        "type": "error",
                        "message": action + ": not implemented",
                    },
                )

    app.run(port=0xB1E, debug=True)


if __name__ == "__main__":
    web_server()

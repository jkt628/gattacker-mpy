import json

from microdot import Microdot
from microdot.websocket import with_websocket


def web_server():
    app = Microdot()

    @app.route('/')
    @with_websocket
    async def ws(request, ws):
        print("Connect from", request.client_addr)
        await ws.send(json.dumps({
            "type":  "stateChange",
            "state": "poweredOn",
        }))
        while True:
            raw = await ws.receive()
            data = json.loads(raw)
            print(data)

    app.run(port=2846, debug=True)


if __name__ == '__main__':
    web_server()

import websockets.sync.client
from protocol import Protocol
websocket = websockets.sync.client.connect('ws://localhost:8550')

websocket.send(Protocol.USER_TRANSCRIPT + "Hello from client")

while True:
    print(websocket.recv())

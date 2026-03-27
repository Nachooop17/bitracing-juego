# -*- coding: utf-8 -*-
import asyncio
import websockets
import json
import time
import urllib.parse
from http import HTTPStatus
import os
from config import LISTA_PISTAS

class Room:
    """Gestiona el estado y la comunicación de una única sala de juego."""
    def __init__(self, name, on_state_change):
        self.name = name
        self.on_state_change = on_state_change  # Callback para notificar al lobby
        self.players = {}  # {websocket: client_id}
        self.game_state = {"players": {}}
        self.session_state = {"state": "LOBBY", "track_idx": 0, "track_name": "Unknown"}
        self.host_id = None
        self.broadcast_task = asyncio.create_task(self._broadcast_loop())
        print(f"Sala '{self.name}' creada.")

    async def handle_player(self, websocket):
        """Gestiona la conexión completa de un jugador en esta sala."""
        client_id = str(websocket.remote_address)
        self.players[websocket] = client_id
        is_host = not self.host_id
        if is_host:
            self.host_id = client_id
        
        print(f"[{self.name}] Jugador {client_id} conectado. Total: {len(self.players)}. Host: {is_host}")
        self.on_state_change()

        try:
            await websocket.send(json.dumps({"type": "welcome", "id": client_id, "is_host": is_host}))
            await websocket.send(json.dumps({"type": "session_update", "payload": self.session_state}))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if not isinstance(data, dict):
                        print(f"[{self.name}] WARNING: Received non-dict message from {client_id}")
                        continue
                    
                    msg_type = data.get('type')
                    if not msg_type:
                        print(f"[{self.name}] WARNING: Received message without type from {client_id}")
                        continue

                    if msg_type == 'player_update':
                        if client_id not in self.game_state["players"]:
                            self.game_state["players"][client_id] = {}
                        self.game_state["players"][client_id].update(data['payload'])
                        self.game_state["players"][client_id]['id'] = client_id
                    
                    elif msg_type == 'set_game_info' and is_host:
                        payload = data.get('payload', {})
                        self.session_state['track_idx'] = payload.get('track_idx', 0)
                        try:
                            self.session_state['track_name'] = LISTA_PISTAS[self.session_state['track_idx']]['nombre']
                        except IndexError:
                            self.session_state['track_name'] = "Pista Desconocida"
                        print(f"[{self.name}] Host ha seleccionado la pista: {self.session_state['track_name']}")
                        self.on_state_change()

                    elif msg_type == 'host_action' and is_host and data.get('action') == 'start_race':
                        if self.session_state['state'] == 'LOBBY':
                            print(f"[{self.name}] El Host ha iniciado la carrera!")
                            self.session_state['state'] = 'CUENTA_ATRAS'
                            self.on_state_change()
                except json.JSONDecodeError:
                    print(f"[{self.name}] WARNING: Received invalid JSON from {client_id}: {message}")
                except Exception:
                    import traceback
                    print(f"[{self.name}] ERROR: Unhandled exception for client {client_id}:")
                    traceback.print_exc()
                    break  # Cierra la conexión para este cliente
        finally:
            print(f"[{self.name}] Jugador {client_id} desconectado.")
            del self.players[websocket]
            if client_id in self.game_state["players"]:
                del self.game_state["players"][client_id]
            
            if is_host and self.players:
                # Si el host se va, nombramos a otro como nuevo host
                new_host_ws = next(iter(self.players))
                self.host_id = self.players[new_host_ws]
                print(f"[{self.name}] Host anterior desconectado. Nuevo host: {self.host_id}")
                await new_host_ws.send(json.dumps({"type": "promotion", "reason": "El host anterior se ha desconectado."}))
            elif not self.players:
                self.host_id = None
            
            self.on_state_change()

    async def _broadcast_loop(self):
        """Envía el estado de esta sala a sus jugadores."""
        while True:
            try:
                if self.players:
                    message = json.dumps({
                        "type": "state_update",
                        "payload": {
                            "session": self.session_state,
                            "players": list(self.game_state["players"].values()),
                            "host_id": self.host_id
                        }
                    })
                    await asyncio.gather(*[ws.send(message) for ws in self.players.keys()], return_exceptions=True)
                await asyncio.sleep(1/30)
            except asyncio.CancelledError:
                break
    
    def get_info(self):
        """Devuelve un diccionario con información pública de la sala para el lobby."""
        return {
            "name": self.name,
            "player_count": len(self.players),
            "track_name": self.session_state.get('track_name', '---'),
            "state": self.session_state.get('state', 'LOBBY')
        }

    async def close(self):
        """Cierra la sala y desconecta a todos los jugadores."""
        print(f"Cerrando sala '{self.name}'...")
        self.broadcast_task.cancel()
        await asyncio.gather(*[ws.close(1001, 'La sala se ha cerrado.') for ws in self.players.keys()], return_exceptions=True)

# --- GESTOR GLOBAL DEL SERVIDOR ---
ROOMS = {}
LOBBY_CLIENTS = set()

async def broadcast_to_lobby():
    """Envía la lista de salas actualizadas a todos los clientes en el lobby."""
    if LOBBY_CLIENTS:
        room_list = [room.get_info() for room in ROOMS.values()]
        message = json.dumps({"type": "room_list", "rooms": room_list})
        await asyncio.gather(*[ws.send(message) for ws in LOBBY_CLIENTS], return_exceptions=True)

async def process_request(path, request_headers):
    """Procesa peticiones HTTP antes del handshake de WebSocket."""
    # Render envía peticiones HEAD o GET a la raíz para comprobar la salud del servicio.
    if path == "/":
        print("Health check recibido. Respondiendo 200 OK.")
        return HTTPStatus.OK, [], b"OK\n"
    return None  # Procede con el handshake de WebSocket

async def cleanup_empty_rooms():
    """Tarea periódica para encontrar y cerrar salas vacías."""
    while True:
        await asyncio.sleep(60)
        empty_rooms = [name for name, room in ROOMS.items() if not room.players]
        if empty_rooms:
            for name in empty_rooms:
                if name in ROOMS:
                    await ROOMS[name].close()
                    del ROOMS[name]
            await broadcast_to_lobby()

async def handler(websocket, path):
    """Punto de entrada para todas las conexiones. Enruta al lobby o a una sala."""
    if path == "/lobby":
        LOBBY_CLIENTS.add(websocket)
        try:
            await broadcast_to_lobby()
            await websocket.wait_closed()
        finally:
            LOBBY_CLIENTS.remove(websocket)
    else:
        room_name_encoded = path.strip('/')
        if not room_name_encoded: return # Ignorar conexiones a la raíz
        room_name = urllib.parse.unquote(room_name_encoded)

        # Crea la sala si no existe, o la obtiene si ya existe.
        room = ROOMS.setdefault(room_name, Room(room_name, on_state_change=broadcast_to_lobby))
        await room.handle_player(websocket)

async def main():
    # Render proporciona la variable de entorno PORT
    port = int(os.environ.get("PORT", 8765))
    
    # Iniciar la tarea de limpieza de salas
    asyncio.create_task(cleanup_empty_rooms())

    print(f"Servidor dedicado iniciado en 0.0.0.0:{port}")
    async with websockets.serve(handler, "0.0.0.0", port, process_request=process_request):
        await asyncio.Future()  # Correr indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
# -*- coding: utf-8 -*-
import pygame
import sys
import asyncio
from config import *
from utils import obtener_ruta, GameExit
import websockets
import json

async def ejecutar_menu(pantalla, reloj):
    estado_menu = "PRINCIPAL"
    foco_principal = 0
    opciones_principal = ["UN JUGADOR", "CONTRARRELOJ", "MULTIJUGADOR", "OPCIONES", "SALIR"]
    
    modo_juego = "CARRERA"
    idx_clase = 0
    idx_auto = 0
    idx_pista = 0
    foco_seleccion = 0 # 0 = Clase, 1 = Auto, 2 = Pista
    foco_opciones = 0
    
    # --- ESTADO DEL LOBBY MULTIJUGADOR ---
    lobby_ws = None
    lobby_task = None
    lista_salas = []
    foco_lobby = 0
    estado_conexion_lobby = "Conectando..."

    # --- ESTADO DE CREACIÓN DE SALA ---
    nombre_sala_input = "Mi Partida"
    escribiendo_nombre = False
    foco_crear_sala = 0 # 0: Nombre, 1: Botón Crear

    nombre_sala_seleccionada = None

    # --- CARGAR FONDO DEL MENÚ ---
    try:
        # Asumimos que la imagen se llama fondo.png, si se llama distinto cámbialo aquí
        fondo_img = pygame.image.load(obtener_ruta("assets/sprites/fondo.png")).convert()
    except Exception:
        fondo_img = None

    try:
        ruta_fuente = obtener_ruta("assets/fuentes/minecraft.ttf")
        fuente_titulo = pygame.font.Font(ruta_fuente, 50)
        fuente_opciones = pygame.font.Font(ruta_fuente, 35)
        fuente_instrucciones = pygame.font.Font(ruta_fuente, 20)
    except Exception:
        fuente_titulo = pygame.font.SysFont("Arial", 50, bold=True)
        fuente_opciones = pygame.font.SysFont("Arial", 35)
        fuente_instrucciones = pygame.font.SysFont("Arial", 20)

    async def conectar_al_lobby():
        nonlocal lobby_ws, estado_conexion_lobby, lista_salas
        try:
            lobby_ws = await websockets.connect(f"{DEDICATED_SERVER_URI}/lobby")
            estado_conexion_lobby = "Conectado"
            async for message in lobby_ws:
                data = json.loads(message)
                if data.get("type") == "room_list":
                    lista_salas = data.get("rooms", [])
        except Exception as e:
            estado_conexion_lobby = f"Error: {e}"
            lista_salas = []
        finally:
            estado_conexion_lobby = "Desconectado"

    while True:
        pantalla = pygame.display.get_surface()
        cw, ch = pantalla.get_size()
        
        if fondo_img:
            fondo_escalado = pygame.transform.scale(fondo_img, (cw, ch))
            pantalla.blit(fondo_escalado, (0, 0))
            
            filtro_oscuro = pygame.Surface((cw, ch))
            filtro_oscuro.set_alpha(150)
            pantalla.blit(filtro_oscuro, (0, 0)) # Oscurece un poco la imagen para leer bien el texto
        else:
            pantalla.fill(NEGRO)
            
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                if lobby_task:
                    lobby_task.cancel()
                if lobby_ws:
                    # No usamos await aquí porque estamos saliendo
                    asyncio.create_task(lobby_ws.close())
                raise GameExit
            elif evento.type == pygame.VIDEORESIZE:
                if sys.platform != "emscripten" and not (pantalla.get_flags() & pygame.FULLSCREEN):
                    pygame.display.set_mode((evento.w, evento.h), pygame.RESIZABLE)
            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_F11:
                    if sys.platform != "emscripten":
                        if pantalla.get_flags() & pygame.FULLSCREEN:
                            pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
                        else:
                            # Iniciar en 900p y escalar al monitor (mantiene proporciones)
                            try:
                                pygame.display.set_mode((1600, 900), pygame.FULLSCREEN | pygame.SCALED)
                            except pygame.error:
                                try:
                                    pygame.display.set_mode((1600, 900), pygame.FULLSCREEN)
                                except pygame.error:
                                    pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                if estado_menu == "PRINCIPAL":
                    if evento.key == pygame.K_UP:
                        foco_principal = max(0, foco_principal - 1)
                    elif evento.key == pygame.K_DOWN:
                        foco_principal = min(len(opciones_principal) - 1, foco_principal + 1)
                    elif evento.key == pygame.K_RETURN:
                        if foco_principal == 0:
                            modo_juego = "CARRERA"
                            estado_menu = "SELECCION"
                        elif foco_principal == 1:
                            modo_juego = "CONTRARRELOJ"
                            estado_menu = "SELECCION"
                        elif foco_principal == 2:
                            estado_menu = "LOBBY"
                            estado_conexion_lobby = "Conectando..."
                            lista_salas = []
                            if not lobby_task or lobby_task.done():
                                lobby_task = asyncio.create_task(conectar_al_lobby())
                        elif foco_principal == 3:
                            estado_menu = "OPCIONES"
                        elif foco_principal == 4:
                            if lobby_task:
                                lobby_task.cancel()
                            if lobby_ws:
                                asyncio.create_task(lobby_ws.close())
                            raise GameExit
                elif estado_menu == "SELECCION":
                    # El modo de juego (CARRERA, MULTIJUGADOR_HOST, etc.) ya está definido
                    if evento.key == pygame.K_ESCAPE:
                        estado_menu = "PRINCIPAL"
                    elif evento.key == pygame.K_UP:
                        foco_seleccion = max(0, foco_seleccion - 1)
                    elif evento.key == pygame.K_DOWN:
                        foco_seleccion = min(3, foco_seleccion + 1)
                    elif evento.key == pygame.K_LEFT:
                        if foco_seleccion == 0:
                            idx_clase = (idx_clase - 1) % len(CLASES_AUTOS)
                            idx_auto = 0
                        elif foco_seleccion == 1:
                            if CLASES_AUTOS[idx_clase]["autos"]:
                                idx_auto = (idx_auto - 1) % len(CLASES_AUTOS[idx_clase]["autos"])
                        elif foco_seleccion == 2: # Dificultad
                            current_diff = OPCIONES["dificultad_ia"]
                            OPCIONES["dificultad_ia"] = (current_diff - 1) % len(DIFICULTADES_IA)
                        elif foco_seleccion == 3:
                            idx_pista = (idx_pista - 1) % len(LISTA_PISTAS)
                    elif evento.key == pygame.K_RIGHT:
                        if foco_seleccion == 0:
                            idx_clase = (idx_clase + 1) % len(CLASES_AUTOS)
                            idx_auto = 0
                        elif foco_seleccion == 1:
                            if CLASES_AUTOS[idx_clase]["autos"]:
                                idx_auto = (idx_auto + 1) % len(CLASES_AUTOS[idx_clase]["autos"])
                        elif foco_seleccion == 2: # Dificultad
                            current_diff = OPCIONES["dificultad_ia"]
                            OPCIONES["dificultad_ia"] = (current_diff + 1) % len(DIFICULTADES_IA)
                        elif foco_seleccion == 3:
                            idx_pista = (idx_pista + 1) % len(LISTA_PISTAS)
                    elif evento.key == pygame.K_RETURN:
                        autos_actuales = CLASES_AUTOS[idx_clase]["autos"]
                        pista_valida = "PRONTO" not in LISTA_PISTAS[idx_pista]["nombre"].upper()
                        if autos_actuales and pista_valida:
                            if modo_juego.startswith("MULTIJUGADOR"):
                                return modo_juego, idx_clase, idx_auto, idx_pista, nombre_sala_seleccionada
                            return modo_juego, idx_clase, idx_auto, idx_pista, None
                
                elif estado_menu == "LOBBY":
                    if evento.key == pygame.K_ESCAPE:
                        estado_menu = "PRINCIPAL"
                        if lobby_task:
                            lobby_task.cancel()
                        if lobby_ws:
                            asyncio.create_task(lobby_ws.close())
                            lobby_ws = None
                    elif evento.key == pygame.K_UP:
                        foco_lobby = max(0, foco_lobby - 1)
                    elif evento.key == pygame.K_DOWN:
                        foco_lobby = min(len(lista_salas), foco_lobby + 1) # +1 para el botón de crear
                    elif evento.key == pygame.K_RETURN:
                        if foco_lobby < len(lista_salas): # Unirse a una sala existente
                            nombre_sala_seleccionada = lista_salas[foco_lobby]['name']
                            modo_juego = "MULTIJUGADOR_CLIENTE"
                            estado_menu = "SELECCION"
                        else: # Botón "Crear Sala"
                            estado_menu = "CREAR_SALA"
                            foco_crear_sala = 0

                elif estado_menu == "CREAR_SALA":
                    if evento.key == pygame.K_ESCAPE:
                        estado_menu = "LOBBY"
                        escribiendo_nombre = False
                    elif escribiendo_nombre:
                        if evento.key == pygame.K_RETURN:
                            escribiendo_nombre = False
                        elif evento.key == pygame.K_BACKSPACE:
                            nombre_sala_input = nombre_sala_input[:-1]
                        else:
                            nombre_sala_input += evento.unicode
                    else: # No está escribiendo, navega por los botones
                        if evento.key == pygame.K_UP:
                            foco_crear_sala = max(0, foco_crear_sala - 1)
                        elif evento.key == pygame.K_DOWN:
                            foco_crear_sala = min(1, foco_crear_sala + 1)
                        elif evento.key == pygame.K_RETURN:
                            if foco_crear_sala == 0: # Clic en el campo de texto
                                escribiendo_nombre = True
                            elif foco_crear_sala == 1: # Clic en "Crear y Unirse"
                                if nombre_sala_input:
                                    print(f"Intentando crear y unirse a la sala '{nombre_sala_input}'...")
                                    nombre_sala_seleccionada = nombre_sala_input
                                    modo_juego = "MULTIJUGADOR_HOST"
                                    estado_menu = "SELECCION"

                elif estado_menu == "OPCIONES":
                    if evento.key == pygame.K_ESCAPE:
                        estado_menu = "PRINCIPAL"
                    elif evento.key == pygame.K_LEFT or evento.key == pygame.K_RIGHT:
                        if foco_opciones == 0: # Modo Camara
                            current_mode = OPCIONES["modo_camara"]
                            if evento.key == pygame.K_LEFT:
                                OPCIONES["modo_camara"] = (current_mode - 1) % len(MODOS_CAMARA)
                            else:
                                OPCIONES["modo_camara"] = (current_mode + 1) % len(MODOS_CAMARA)
                    
        # Renderizar Textos del Menú
        tit = fuente_titulo.render("BITRACING", True, BLANCO)
        pantalla.blit(tit, (cw//2 - tit.get_width()//2, 80))
        
        if estado_menu == "PRINCIPAL":
            for i, opc in enumerate(opciones_principal):
                texto = opc
                    
                if i == foco_principal:
                    color = ROJO
                    texto = f"< {texto} >"
                else:
                    color = BLANCO
                    
                txt_opc = fuente_opciones.render(texto, True, color)
                pantalla.blit(txt_opc, (cw//2 - txt_opc.get_width()//2, 220 + i * 70))
                
            instrucciones = fuente_instrucciones.render("Usa las FLECHAS para elegir. ENTER para confirmar.", True, (150, 150, 150))
            pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 100))
            
        elif estado_menu == "LOBBY":
            titulo_lobby = fuente_opciones.render("Salas Disponibles", True, BLANCO)
            pantalla.blit(titulo_lobby, (cw//2 - titulo_lobby.get_width()//2, 150))

            if estado_conexion_lobby != "Conectado":
                txt_estado = fuente_instrucciones.render(estado_conexion_lobby, True, (255, 100, 100))
                pantalla.blit(txt_estado, (cw//2 - txt_estado.get_width()//2, 200))

            y_offset = 240
            for i, sala in enumerate(lista_salas):
                estado_sala = sala.get('state', 'LOBBY')
                nombre_pista_sala = sala.get('track_name', '---')
                color = ROJO if i == foco_lobby else BLANCO
                texto = f"{sala['name']} [{estado_sala}] - Pista: {nombre_pista_sala} ({sala['player_count']} jug.)"
                if i == foco_lobby: texto = f"> {texto} <"
                txt_sala = fuente_instrucciones.render(texto, True, color)
                pantalla.blit(txt_sala, (cw//2 - txt_sala.get_width()//2, y_offset + i * 30))
            
            # Botón de Crear Sala
            color_crear = ROJO if foco_lobby == len(lista_salas) else BLANCO
            texto_crear = "< Crear Sala Nueva >" if foco_lobby == len(lista_salas) else "Crear Sala Nueva"
            txt_crear = fuente_opciones.render(texto_crear, True, color_crear)
            pantalla.blit(txt_crear, (cw//2 - txt_crear.get_width()//2, y_offset + len(lista_salas) * 30 + 20))

            instrucciones = fuente_instrucciones.render("ESC para volver. ENTER para confirmar.", True, (150, 150, 150))
            pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 100))

        elif estado_menu == "CREAR_SALA":
            titulo_crear = fuente_opciones.render("Crear Sala", True, BLANCO)
            pantalla.blit(titulo_crear, (cw//2 - titulo_crear.get_width()//2, 150))

            # Input para el nombre
            color_nombre = ROJO if foco_crear_sala == 0 else BLANCO
            cursor = "|" if escribiendo_nombre and pygame.time.get_ticks() % 1000 < 500 else ""
            texto_nombre = f"Nombre: < {nombre_sala_input}{cursor} >"
            txt_nombre = fuente_opciones.render(texto_nombre, True, color_nombre)
            pantalla.blit(txt_nombre, (cw//2 - txt_nombre.get_width()//2, 250))

            # Botón de confirmación
            color_boton = ROJO if foco_crear_sala == 1 else BLANCO
            texto_boton = "< Crear y Unirse >" if foco_crear_sala == 1 else "Crear y Unirse"
            txt_opc = fuente_opciones.render(texto_boton, True, color_boton)
            pantalla.blit(txt_opc, (cw//2 - txt_opc.get_width()//2, 350))

            instrucciones = fuente_instrucciones.render("ESC para volver. ENTER para confirmar.", True, (150, 150, 150))
            pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 100))
            
        elif estado_menu == "SELECCION":
            color_clase = ROJO if foco_seleccion == 0 else BLANCO
            txt_clase = fuente_opciones.render(f"< CLASE: {CLASES_AUTOS[idx_clase]['nombre']} >", True, color_clase)
            pantalla.blit(txt_clase, (cw//2 - txt_clase.get_width()//2, 190))
            
            color_auto = ROJO if foco_seleccion == 1 else BLANCO
            autos_actuales = CLASES_AUTOS[idx_clase]["autos"]
            if autos_actuales:
                texto_auto = f"< AUTO: {autos_actuales[idx_auto]['nombre']} >"
            else:
                texto_auto = "< AUTO: PRONTO... >"
            txt_auto = fuente_opciones.render(texto_auto, True, color_auto)
            pantalla.blit(txt_auto, (cw//2 - txt_auto.get_width()//2, 260))
            
            color_dificultad = ROJO if foco_seleccion == 2 else BLANCO
            texto_dificultad_val = DIFICULTADES_IA[OPCIONES["dificultad_ia"]]
            txt_dificultad = fuente_opciones.render(f"< DIFICULTAD: {texto_dificultad_val} >", True, color_dificultad)
            pantalla.blit(txt_dificultad, (cw//2 - txt_dificultad.get_width()//2, 330))
            
            color_pista = ROJO if foco_seleccion == 3 else BLANCO
            texto_pista_nombre = LISTA_PISTAS[idx_pista]['nombre']
            txt_pista = fuente_opciones.render(f"< PISTA: {texto_pista_nombre} >", True, color_pista)
            pantalla.blit(txt_pista, (cw//2 - txt_pista.get_width()//2, 400))
            
            pista_es_valida = "PRONTO" not in texto_pista_nombre.upper()
            if autos_actuales and pista_es_valida:
                texto_inst = "ESC para volver. ENTER para iniciar."
                color_inst = (150, 150, 150)
            else:
                texto_inst = "Seleccion no disponible todavia... (ESC para volver)"
                color_inst = (255, 100, 100)
                
            instrucciones = fuente_instrucciones.render(texto_inst, True, color_inst)
            pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 100))
            
        elif estado_menu == "OPCIONES":
            opciones_disponibles = ["MODO DE CAMARA"]
            for i, opc in enumerate(opciones_disponibles):
                color = ROJO if i == foco_opciones else BLANCO
                
                valor_actual = MODOS_CAMARA[OPCIONES["modo_camara"]]
                texto = f"{opc}: < {valor_actual} >"
                
                txt_opc = fuente_opciones.render(texto, True, color)
                pantalla.blit(txt_opc, (cw//2 - txt_opc.get_width()//2, 220 + i * 70))
            instrucciones = fuente_instrucciones.render("Usa las FLECHAS para cambiar. ESC para volver.", True, (150, 150, 150))
            pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 100))
            
        # --- DIBUJAR VERSIÓN DEL JUEGO ---
        texto_version = fuente_instrucciones.render("v0.1", True, (100, 100, 100))
        pantalla.blit(texto_version, (cw - texto_version.get_width() - 10, ch - texto_version.get_height() - 10))
        
        pygame.display.flip()
        reloj.tick(60)
        await asyncio.sleep(0)

async def ejecutar_lobby_partida(pantalla, reloj, modo_juego, nombre_sala, idx_clase, idx_auto, idx_pista):
    """Gestiona la pantalla de lobby pre-carrera, esperando a otros jugadores."""
    # --- Fuentes ---
    try:
        ruta_fuente = obtener_ruta("assets/fuentes/minecraft.ttf")
        fuente_titulo = pygame.font.Font(ruta_fuente, 50)
        fuente_texto = pygame.font.Font(ruta_fuente, 28)
        fuente_jugador = pygame.font.Font(ruta_fuente, 24)
    except Exception:
        fuente_titulo = pygame.font.SysFont("Arial", 50, bold=True)
        fuente_texto = pygame.font.SysFont("Arial", 30)
        fuente_jugador = pygame.font.SysFont("Arial", 24)

    # --- Estado de Red ---
    websocket = None
    my_id = None
    game_state = {"session": {"state": "LOBBY", "track_name": "Cargando..."}, "players": []}
    estado_conexion = "Conectando..."
    is_host = False # El servidor nos dirá si somos el host

    # --- Estado de la UI ---
    foco_lobby = 0 # 0: Botón principal (Iniciar/Listo), 1: Volver

    async def network_task():
        nonlocal websocket, my_id, game_state, estado_conexion, is_host
        uri = f"{DEDICATED_SERVER_URI}/{nombre_sala}"
        try:
            async with websockets.connect(uri) as ws:
                websocket = ws
                estado_conexion = "Conectado"
                
                # 1. Esperar mensaje de bienvenida del servidor
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                if welcome_data['type'] == 'welcome':
                    my_id = welcome_data['id']
                    is_host = welcome_data.get('is_host', False)
                else:
                    raise Exception("Protocolo incorrecto: No se recibió bienvenida.")

                # 2. Si somos el host (o nos acaban de ascender), enviamos la configuración de la partida
                # El modo_juego original nos dice si fuimos los que creamos la sala.
                if is_host:
                    await websocket.send(json.dumps({
                        "type": "set_game_info", 
                        "payload": {
                            "track_idx": idx_pista,
                            "track_name": LISTA_PISTAS[idx_pista]['nombre']
                        }
                    }))
                
                # 3. Bucle principal de red: enviar nuestro estado y recibir el de todos
                while True:
                    # Enviar la información de nuestro auto para que otros nos vean en el lobby
                    my_info_payload = {"auto_info": {"clase": idx_clase, "auto": idx_auto}}
                    await websocket.send(json.dumps({"type": "player_update", "payload": my_info_payload}))

                    # Escuchar actualizaciones del estado general del juego
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    if data.get('type') == 'state_update':
                        game_state = data.get('payload', game_state)
                        # Si el estado de la sesión ya no es LOBBY, la carrera ha empezado.
                        if game_state.get("session", {}).get("state") != "LOBBY":
                            break # Salimos del bucle para empezar la carrera
                    
                    elif data.get('type') == 'promotion':
                        print("¡He sido ascendido a Host!")
                        is_host = True

                    await asyncio.sleep(0.5) # Actualizamos nuestra presencia 2 veces por segundo

        except Exception as e:
            estado_conexion = f"Error de conexión: {e}"
            print(f"Error en el lobby de partida: {e}")
            websocket = None # Señalamos que la conexión falló

    net_task = asyncio.create_task(network_task())

    # Bucle principal de renderizado y eventos del lobby
    while not net_task.done():
        pantalla.fill(NEGRO)
        cw, ch = pantalla.get_size()

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                net_task.cancel()
                raise GameExit
            if evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    net_task.cancel()
                    return None, None # Volver al menú principal
                if evento.key in (pygame.K_UP, pygame.K_DOWN):
                    foco_lobby = 1 - foco_lobby # Alternar entre 0 y 1
                if evento.key == pygame.K_RETURN:
                    if foco_lobby == 1: # Botón "Volver"
                        net_task.cancel()
                        return None, None
                    if foco_lobby == 0 and is_host and websocket: # Botón "Iniciar Carrera"
                        await websocket.send(json.dumps({"type": "host_action", "action": "start_race"}))
                        # La tarea de red detectará el cambio de estado y terminará el bucle.
        
        # --- Renderizar UI ---
        titulo_txt = fuente_titulo.render("Lobby de Partida", True, BLANCO)
        pantalla.blit(titulo_txt, (cw // 2 - titulo_txt.get_width() // 2, 40))

        estado_txt = fuente_texto.render(f"Estado: {estado_conexion}", True, BLANCO if estado_conexion == "Conectado" else ROJO)
        pantalla.blit(estado_txt, (50, 120))
        track_name = game_state.get("session", {}).get("track_name", "Cargando...")
        track_txt = fuente_texto.render(f"Pista: {track_name}", True, BLANCO)
        pantalla.blit(track_txt, (50, 160))

        nombre_sala_txt = fuente_texto.render(f"Sala: {nombre_sala}", True, (180, 180, 180))
        pantalla.blit(nombre_sala_txt, (cw // 2 - nombre_sala_txt.get_width() // 2, 90))

        players_title = fuente_texto.render(f"Jugadores ({len(game_state.get('players', []))}/5):", True, BLANCO)
        pantalla.blit(players_title, (50, 220))
        
        host_id = game_state.get('host_id')
        y_offset = 270
        for i, player_data in enumerate(game_state.get("players", [])):
            player_id = player_data.get('id')
            is_me = (player_id == my_id)
            is_player_host = (player_id == host_id)
            try:
                auto_nombre = CLASES_AUTOS[player_data['auto_info']['clase']]['autos'][player_data['auto_info']['auto']]['nombre']
            except (KeyError, IndexError):
                auto_nombre = "Eligiendo..."
            player_str = f"  - {auto_nombre}"
            color = (255, 215, 0) if is_me else ((100, 255, 100) if is_player_host else BLANCO)
            player_txt = fuente_jugador.render(f"{i+1}. Jugador {player_id[-5:]}{' (Host)' if is_player_host else ''}{' (Tú)' if is_me else ''}", True, color)
            auto_txt = fuente_jugador.render(player_str, True, (200, 200, 200))
            pantalla.blit(player_txt, (70, y_offset))
            pantalla.blit(auto_txt, (70, y_offset + 25))
            y_offset += 60

        y_buttons = ch - 150
        color_start = ROJO if foco_lobby == 0 else BLANCO
        text_start = "Iniciar Carrera" if is_host else "Esperando al host..."
        start_txt = fuente_texto.render(f"< {text_start} >" if foco_lobby == 0 and is_host else text_start, True, color_start if is_host else (150,150,150))
        pantalla.blit(start_txt, (cw // 2 - start_txt.get_width() // 2, y_buttons))

        color_back = ROJO if foco_lobby == 1 else BLANCO
        back_txt = fuente_texto.render("< Volver >" if foco_lobby == 1 else "Volver", True, color_back)
        pantalla.blit(back_txt, (cw // 2 - back_txt.get_width() // 2, y_buttons + 60))

        pygame.display.flip()
        reloj.tick(60)
        await asyncio.sleep(0)

    # El bucle ha terminado, ya sea por éxito o por fallo
    if websocket and game_state.get("session", {}).get("state") != "LOBBY":
        print("¡La carrera va a comenzar!")
        return websocket, my_id
    else:
        print("Saliendo del lobby (error o cancelado por el usuario).")
        if websocket:
            await websocket.close()
        return None, None
# -*- coding: utf-8 -*-
import pygame
import sys
import math
import asyncio
import websockets
import json
import threading
from auto import Auto
from config import *
from utils import obtener_ruta, formato_tiempo, GameExit
from hud import HUD
from menu import ejecutar_menu, ejecutar_lobby_partida
from pista import Pista
from audio import GestorAudio
from huellas import GestorHuellas
from ia import AutoIA

async def jugar_partida(pantalla, reloj, modo_juego, idx_clase, idx_auto, idx_pista, websocket=None, my_id=None):
    """Función que contiene toda la lógica de una carrera, desde el setup hasta el final."""
    # --- SETUP DE LA PARTIDA ---
    autos_disponibles = CLASES_AUTOS[idx_clase]["autos"]

    # Cargar e inicializar el Circuito seleccionado
    circuito = Pista(idx_pista)

    # Cargar el sprite del auto
    archivo_auto_sel = autos_disponibles[idx_auto]["archivo"]
    imagen_original = pygame.image.load(obtener_ruta(f"assets/sprites/{archivo_auto_sel}")).convert_alpha()

    # Redimensionar el sprite. Lo dejamos en 1.0 para que el auto tenga el tamaño que querías
    factor_escala = 1.0
    nuevo_ancho = int(imagen_original.get_width() * factor_escala)
    nuevo_alto = int(imagen_original.get_height() * factor_escala)
    sprite_auto = pygame.transform.scale(imagen_original, (nuevo_ancho, nuevo_alto))

    angulo_volante = 0.0 # Controla la rotación

    x_jugador, y_jugador = circuito.obtener_posicion_spawn(0)
    jugador = Auto(x_jugador, y_jugador, sprite_auto)

    # --- LÓGICA MULTIJUGADOR (INICIALIZACIÓN) ---
    remote_players = {} # Reemplaza a 'bots' en modo multijugador
    huellas_remotos = {} # Cada jugador remoto necesita su propio gestor de huellas

    # --- Crear Pilotos Rivales (IA) ---
    bots = []
    huellas_bots = []
    if modo_juego == "CARRERA":
        # Leer la dificultad seleccionada desde la configuración global
        idx_dificultad = OPCIONES["dificultad_ia"]
        velocidad_max_ia = VALORES_DIFICULTAD[idx_dificultad]

        # Bot 1 (Trazada Principal)
        x_bot1, y_bot1 = circuito.obtener_posicion_spawn(1)
        idx_r1 = (idx_auto + 1) % len(autos_disponibles)
        img_r1 = pygame.transform.scale(pygame.image.load(obtener_ruta(f"assets/sprites/{autos_disponibles[idx_r1]['archivo']}")).convert_alpha(), (nuevo_ancho, nuevo_alto))
        nodos_sec = circuito.nodos_ia_secundarios if circuito.nodos_ia_secundarios else circuito.nodos_ia
        bot1 = AutoIA(x_bot1, y_bot1, img_r1, circuito.nodos_ia, nodos_sec)
        bot1.velocidad_maxima_base = velocidad_max_ia
        bots.append(bot1)
        huellas_bots.append(GestorHuellas())

        # Bot 2 (Trazada Secundaria)
        x_bot2, y_bot2 = circuito.obtener_posicion_spawn(2)
        idx_r2 = (idx_auto + 2) % len(autos_disponibles)
        img_r2 = pygame.transform.scale(pygame.image.load(obtener_ruta(f"assets/sprites/{autos_disponibles[idx_r2]['archivo']}")).convert_alpha(), (nuevo_ancho, nuevo_alto))
        bot2 = AutoIA(x_bot2, y_bot2, img_r2, circuito.nodos_ia, nodos_sec)
        bot2.velocidad_maxima_base = velocidad_max_ia
        # Hacemos que el bot 2 inicie prefiriendo la línea secundaria para esparcirlos al inicio
        bot2.cambiar_linea(True)
        bots.append(bot2)
        huellas_bots.append(GestorHuellas())

        # Bot 3 (Trazada Principal - Atrás de la parrilla)
        x_bot3, y_bot3 = circuito.obtener_posicion_spawn(3)
        idx_r3 = (idx_auto + 3) % len(autos_disponibles)
        img_r3 = pygame.transform.scale(pygame.image.load(obtener_ruta(f"assets/sprites/{autos_disponibles[idx_r3]['archivo']}")).convert_alpha(), (nuevo_ancho, nuevo_alto))
        bot3 = AutoIA(x_bot3, y_bot3, img_r3, circuito.nodos_ia, nodos_sec)
        bot3.velocidad_maxima_base = velocidad_max_ia
        bots.append(bot3)
        huellas_bots.append(GestorHuellas())

        # Bot 4 (Trazada Secundaria - Final de la parrilla)
        x_bot4, y_bot4 = circuito.obtener_posicion_spawn(4)
        idx_r4 = (idx_auto + 4) % len(autos_disponibles)
        img_r4 = pygame.transform.scale(pygame.image.load(obtener_ruta(f"assets/sprites/{autos_disponibles[idx_r4]['archivo']}")).convert_alpha(), (nuevo_ancho, nuevo_alto))
        bot4 = AutoIA(x_bot4, y_bot4, img_r4, circuito.nodos_ia, nodos_sec)
        bot4.velocidad_maxima_base = velocidad_max_ia
        bot4.cambiar_linea(True) # Inicia prefiriendo la línea secundaria
        bots.append(bot4)
        huellas_bots.append(GestorHuellas())
    # -------------------------------

    # Instanciar Gestor de Audio
    audio = GestorAudio()

    # Instanciar sistema de partículas/huellas
    huellas = GestorHuellas()

    mostrar_telemetria = False

    # Instanciar el HUD
    hud = HUD()

    # Cargar fuentes para los menús en partida
    try:
        ruta_fuente = obtener_ruta("assets/fuentes/minecraft.ttf")
        fuente_titulo_pausa = pygame.font.Font(ruta_fuente, 50)
        fuente_opciones_pausa = pygame.font.Font(ruta_fuente, 35)
    except Exception:
        fuente_titulo_pausa = pygame.font.SysFont("Arial", 50, bold=True)
        fuente_opciones_pausa = pygame.font.SysFont("Arial", 35)

    def dibujar_menu_pausa(pantalla, foco):
        cw, ch = pantalla.get_size()
        filtro_oscuro = pygame.Surface((cw, ch))
        filtro_oscuro.set_alpha(180)
        pantalla.blit(filtro_oscuro, (0, 0))

        tit = fuente_titulo_pausa.render("PAUSA", True, BLANCO)
        pantalla.blit(tit, (cw//2 - tit.get_width()//2, 150))

        opciones_pausa = ["Reanudar", "Opciones", "Menu"]
        for i, opc in enumerate(opciones_pausa):
            texto = opc
            color = ROJO if i == foco else BLANCO
            if i == foco: texto = f"< {texto} >"

            txt_opc = fuente_opciones_pausa.render(texto, True, color)
            pantalla.blit(txt_opc, (cw//2 - txt_opc.get_width()//2, 280 + i * 70))

    def dibujar_menu_opciones(pantalla, foco):
        cw, ch = pantalla.get_size()
        filtro_oscuro = pygame.Surface((cw, ch))
        filtro_oscuro.set_alpha(180)
        pantalla.blit(filtro_oscuro, (0, 0))

        tit = fuente_titulo_pausa.render("OPCIONES", True, BLANCO)
        pantalla.blit(tit, (cw//2 - tit.get_width()//2, 150))

        opciones_disponibles = ["MODO DE CAMARA"]
        for i, opc in enumerate(opciones_disponibles):
            color = ROJO if i == foco else BLANCO
            valor_actual = MODOS_CAMARA[OPCIONES["modo_camara"]]
            texto = f"{opc}: < {valor_actual} >"
            txt_opc = fuente_opciones_pausa.render(texto, True, color)
            pantalla.blit(txt_opc, (cw//2 - txt_opc.get_width()//2, 280 + i * 70))
        instrucciones = fuente_opciones_pausa.render("ESC para volver", True, (150, 150, 150))
        pantalla.blit(instrucciones, (cw//2 - instrucciones.get_width()//2, ch - 150))

    # Variables de estado de la carrera
    tiempo_inicio_cuenta = pygame.time.get_ticks()
    tiempo_inicio_carrera = 0
    # El estado ahora lo dicta el servidor, pero mantenemos una copia local para la lógica de renderizado
    estado_carrera = "CUENTA_ATRAS"
    cuenta_atras_finalizada = False
    TOTAL_VUELTAS = 10
    posicion_jugador = 1
    tiempo_fin_carrera = 0
    foco_pausa = 0
    foco_opciones = 0
    tiempo_inicio_pausa = 0

    # --- BUCLE PRINCIPAL DE LA PARTIDA ---
    corriendo = True
    while corriendo:
        if modo_juego.startswith("MULTIJUGADOR"):
            todos_autos = [jugador] + list(remote_players.values())
        else:
            todos_autos = [jugador] + bots

        # A. Manejo de Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
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
                if estado_carrera == "PAUSA":
                    if evento.key == pygame.K_ESCAPE or (evento.key == pygame.K_RETURN and foco_pausa == 0):
                        # --- REANUDAR ---
                        tiempo_pausado = pygame.time.get_ticks() - tiempo_inicio_pausa
                        tiempo_inicio_cuenta += tiempo_pausado
                        if tiempo_inicio_carrera > 0: tiempo_inicio_carrera += tiempo_pausado
                        if circuito.tiempo_inicio_vuelta > 0: circuito.tiempo_inicio_vuelta += tiempo_pausado
                        for auto in todos_autos:
                            if auto.ultimo_tiempo_meta > 0: auto.ultimo_tiempo_meta += tiempo_pausado
                        
                        estado_carrera = "CARRERA"
                        audio.canal_aceleracion.unpause()
                        audio.canal_desaceleracion.unpause()
                        audio.canal_derrape.unpause()
                    elif evento.key == pygame.K_UP:
                        foco_pausa = max(0, foco_pausa - 1)
                    elif evento.key == pygame.K_DOWN:
                        foco_pausa = min(2, foco_pausa + 1)
                    elif evento.key == pygame.K_RETURN:
                        if foco_pausa == 1: # Opciones
                            estado_carrera = "PAUSA_OPCIONES"
                            foco_opciones = 0
                        elif foco_pausa == 2: # Menú
                            corriendo = False
                elif estado_carrera == "PAUSA_OPCIONES":
                    if evento.key == pygame.K_ESCAPE:
                        estado_carrera = "PAUSA"
                    elif evento.key == pygame.K_LEFT or evento.key == pygame.K_RIGHT:
                        if foco_opciones == 0: # Modo Camara
                            current_mode = OPCIONES["modo_camara"]
                            if evento.key == pygame.K_LEFT:
                                OPCIONES["modo_camara"] = (current_mode - 1) % len(MODOS_CAMARA)
                            else:
                                OPCIONES["modo_camara"] = (current_mode + 1) % len(MODOS_CAMARA)
                else: # Si no está en pausa
                    if evento.key == pygame.K_ESCAPE and estado_carrera == "CARRERA":
                        # --- PAUSAR ---
                        estado_carrera = "PAUSA"
                        tiempo_inicio_pausa = pygame.time.get_ticks()
                        audio.canal_aceleracion.pause()
                        audio.canal_desaceleracion.pause()
                        audio.canal_derrape.pause()
                    elif evento.key == pygame.K_TAB:
                        mostrar_telemetria = not mostrar_telemetria
                    elif evento.key == pygame.K_r:
                        # Reiniciar posición y físicas del auto
                        x_jugador, y_jugador = circuito.obtener_posicion_spawn(0)
                        jugador.x = x_jugador
                        jugador.y = y_jugador
                        jugador.vector_velocidad = pygame.math.Vector2(0, 0)
                        jugador.velocidad = 0
                        jugador.angulo = 0
                        jugador.nivel_derrape = 0
                        jugador.vueltas = 1
                        jugador.ultimo_tiempo_meta = 0
                        jugador.nodo_actual_idx = 0
                        circuito.reiniciar_tiempos()
                        jugador.tiempo_final_ms = 0
                        
                        # Reiniciar a los rivales
                        for i, bot in enumerate(bots):
                            x_bot, y_bot = circuito.obtener_posicion_spawn(i + 1)
                            bot.x = x_bot
                            bot.y = y_bot
                            bot.vector_velocidad = pygame.math.Vector2(0, 0)
                            bot.velocidad = 0
                            bot.angulo = 0
                            bot.nivel_derrape = 0
                            bot.vueltas = 1
                            bot.ultimo_tiempo_meta = 0
                            bot.nodo_actual_idx = 0
                            bot.tiempo_final_ms = 0
                            if bot.nodos: bot.nodo_objetivo_idx = bot._encontrar_nodo_mas_cercano()
                        
                        tiempo_inicio_cuenta = pygame.time.get_ticks()
                        estado_carrera = "CUENTA_ATRAS"
                        cuenta_atras_finalizada = False

        # B. Lógica del Juego
        teclas = pygame.key.get_pressed()
        tiempo_actual = pygame.time.get_ticks()
        texto_cuenta = ""

        if estado_carrera == "PAUSA" or estado_carrera == "PAUSA_OPCIONES":
            # Si el juego está en cualquier estado de pausa, no actualizamos la lógica del mundo
            pass
        else:
            # --- LÓGICA DE RED (si aplica) ---
            if websocket and my_id:
                # 1. Enviar mi estado al servidor
                player_payload = {
                    "x": jugador.x, "y": jugador.y, "angulo": jugador.angulo,
                    "vueltas": jugador.vueltas, "progreso": jugador.progreso,
                    "tiempo_final_ms": jugador.tiempo_final_ms, "nivel_derrape": jugador.nivel_derrape,
                    "auto_info": {"clase": idx_clase, "auto": idx_auto} # Para que otros sepan qué auto dibujar
                }
                await websocket.send(json.dumps({"type": "player_update", "payload": player_payload}))

                # 2. Recibir estado del juego y actualizar jugadores remotos (de forma no bloqueante)
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.02)
                    data = json.loads(message)

                    if data['type'] == 'state_update':
                        game_state_payload = data['payload']
                        session_data = game_state_payload.get('session', {})
                        all_players_data = game_state_payload.get('players', [])
                        
                        # Sincronizar el estado de la carrera con el servidor
                        estado_carrera = session_data.get('state', estado_carrera)

                        current_remote_ids = set()
                        for data in all_players_data:
                            player_id = data['id']
                            if player_id == my_id:
                                continue # Soy yo, no necesito actualizarme desde el servidor
                            
                            current_remote_ids.add(player_id)

                            if player_id not in remote_players:
                                # Jugador nuevo, lo creamos
                                print(f"Nuevo jugador detectado: {player_id}")
                                try:
                                    remote_auto_info = data['auto_info']
                                    remote_clase_idx = remote_auto_info['clase']
                                    remote_auto_idx = remote_auto_info['auto']
                                    remote_autos_disp = CLASES_AUTOS[remote_clase_idx]["autos"]
                                    remote_archivo = remote_autos_disp[remote_auto_idx]['archivo']
                                    remote_img_orig = pygame.image.load(obtener_ruta(f"assets/sprites/{remote_archivo}")).convert_alpha()
                                    remote_sprite = pygame.transform.scale(remote_img_orig, (nuevo_ancho, nuevo_alto))
                                    
                                    remote_players[player_id] = Auto(data['x'], data['y'], remote_sprite)
                                    huellas_remotos[player_id] = GestorHuellas()
                                except (KeyError, IndexError):
                                    # Si falla, usamos un sprite por defecto para no crashear
                                    remote_players[player_id] = Auto(data['x'], data['y'], sprite_auto)
                                    huellas_remotos[player_id] = GestorHuellas()
                            
                            # Actualizar estado del jugador remoto (teletransportación por ahora)
                            p = remote_players[player_id]
                            p.x, p.y, p.angulo = data['x'], data['y'], data['angulo']
                            p.nivel_derrape = data.get('nivel_derrape', 0)

                        # Eliminar jugadores que se desconectaron
                        disconnected_ids = set(remote_players.keys()) - current_remote_ids
                        for player_id in disconnected_ids:
                            print(f"Jugador {player_id} se ha desconectado.")
                            del remote_players[player_id]
                            del huellas_remotos[player_id]

                except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                    pass # No hay mensaje nuevo o se cerró la conexión

            # --- LÓGICA DE JUEGO ACTIVO ---
            if estado_carrera == "CUENTA_ATRAS": # Sub-estado: Cuenta atrás
                tiempo_transcurrido = tiempo_actual - tiempo_inicio_cuenta
                if tiempo_transcurrido < 1000:
                    texto_cuenta = "3"
                elif tiempo_transcurrido < 2000:
                    texto_cuenta = "2"
                elif tiempo_transcurrido < 3000:
                    texto_cuenta = "1"
                elif tiempo_transcurrido < 4000:
                    texto_cuenta = "¡YA!"
                    if not cuenta_atras_finalizada:
                        tiempo_inicio_carrera = pygame.time.get_ticks()
                        circuito.reiniciar_tiempos()
                        for auto in [jugador] + bots:
                            auto.ultimo_tiempo_meta = pygame.time.get_ticks()
                            auto.vueltas = 1
                        cuenta_atras_finalizada = True
                else:
                    estado_carrera = "CARRERA"
                    
                if tiempo_transcurrido < 3000:
                    # Un pequeño truco para crear un "teclado" que siempre diga que no estás apretando nada
                    class TeclasVacias:
                        def __getitem__(self, key): return False
                    teclas = TeclasVacias()

            if estado_carrera == "FIN_CARRERA": # Sub-estado: Carrera terminada
                class TeclasVacias:
                    def __getitem__(self, key): return False
                teclas = TeclasVacias()

            # --- Lógica de animación del volante visual ---
            # El volante gira más o menos dependiendo de la capacidad real de giro del auto
            max_giro_volante = min((jugador.tasa_giro / 5.0) * 90.0, 90.0)
            angulo_objetivo = 0.0
            
            if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                angulo_objetivo = max_giro_volante
            elif teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                angulo_objetivo = -max_giro_volante
                
            # Interpolar suavemente hacia el ángulo objetivo (hace el giro más natural)
            angulo_volante += (angulo_objetivo - angulo_volante) * 0.15

            # Detectar el terreno en el que está el auto y aplicar la física
            circuito.actualizar_superficie(jugador)

            # Actualizar la física del auto llamando al método de la clase
            jugador.actualizar(teclas)
            
            # Actualizar sistema de sonido
            audio.actualizar_derrape(jugador.nivel_derrape > 0.2)
            audio.actualizar_motor(jugador.velocidad, jugador.velocidad_maxima, teclas[pygame.K_UP] or teclas[pygame.K_w], jugador.nivel_derrape > 0.2)
            
            # Actualizar sistema de huellas de derrape
            huellas.actualizar(jugador, circuito)
            
            if estado_carrera == "CUENTA_ATRAS": # Re-evaluamos por si cambió en la lógica anterior
                tiempo_transcurrido = tiempo_actual - tiempo_inicio_cuenta
            
            # Actualizar bots o huellas de jugadores remotos
            if modo_juego.startswith("MULTIJUGADOR"):
                for remote_p_id, remote_p in remote_players.items():
                    # Los jugadores remotos no se "actualizan", solo reciben estado.
                    # Pero sí necesitamos actualizar sus sistemas de partículas como las huellas.
                    huellas_remotos[remote_p_id].actualizar(remote_p, circuito)
            else: # Modo Carrera con bots
                for i, bot in enumerate(bots):
                    if estado_carrera == "CUENTA_ATRAS" and tiempo_transcurrido < 3000:
                        bot.actualizar(teclas) # Anula su cerebro y se quedan quietos
                    else:
                        bot.actualizar_ia(circuito, todos_autos)
                    huellas_bots[i].actualizar(bot, circuito)
            # -----------------------------
            
            # --- COLISIONES CHAPA A CHAPA ---
            radio_colision = 16.0  # Aproximadamente el tamaño desde el centro hasta la puerta
            
            # Comprobar choques entre TODOS los autos (Tú vs Bot1, Tú vs Bot2, Bot1 vs Bot2)
            for i in range(len(todos_autos)):
                for j in range(i + 1, len(todos_autos)):
                    auto_a = todos_autos[i]
                    auto_b = todos_autos[j]
                    dist_actual = pygame.math.Vector2(auto_a.x, auto_a.y).distance_to((auto_b.x, auto_b.y))
                    
                    if 0 < dist_actual < (radio_colision * 2):
                        superposicion = (radio_colision * 2) - dist_actual
                        vector_choque = pygame.math.Vector2(auto_a.x - auto_b.x, auto_a.y - auto_b.y).normalize()
                        
                        mitad_empuje = vector_choque * (superposicion * 0.5)
                        auto_a.x += mitad_empuje.x
                        auto_a.y += mitad_empuje.y
                        auto_b.x -= mitad_empuje.x
                        auto_b.y -= mitad_empuje.y
            # --------------------------------
            
            # --- SISTEMA DE POSICIONES Y VUELTAS (REVISADO) ---
            # 1. Registrar el tiempo final de cualquier auto que haya completado la carrera
            if tiempo_inicio_carrera > 0:
                for auto in todos_autos:
                    if auto.vueltas > TOTAL_VUELTAS and auto.tiempo_final_ms == 0:
                        auto.tiempo_final_ms = pygame.time.get_ticks() - tiempo_inicio_carrera
            
            # 2. Calcular el progreso de cada auto
            if circuito.nodos_ia and modo_juego == "CARRERA":
                num_nodos = len(circuito.nodos_ia)
                for auto in todos_autos:
                    if auto.tiempo_final_ms > 0:
                        # Si ya terminó, su progreso es un número muy grande menos su tiempo.
                        # Menor tiempo = mayor progreso.
                        # El multiplicador asegura que siempre sea mayor que un auto en carrera.
                        auto.progreso = (TOTAL_VUELTAS + 1) * num_nodos * 1000 - auto.tiempo_final_ms
                    else:
                        # Si sigue en carrera, usamos la fórmula original.
                        min_dist = float('inf')
                        idx_mas_cercano = 0
                        pos_auto = pygame.math.Vector2(auto.x, auto.y)
                        for k, nodo in enumerate(circuito.nodos_ia):
                            dist = pos_auto.distance_squared_to(nodo)
                            if dist < min_dist:
                                min_dist = dist
                                idx_mas_cercano = k
                        
                        # Lógica anti-oscilación para evitar que la posición salte hacia atrás.
                        nodo_actual = auto.nodo_actual_idx
                        if (idx_mas_cercano - nodo_actual + num_nodos) % num_nodos < num_nodos / 2:
                            auto.nodo_actual_idx = idx_mas_cercano
                                
                        auto.progreso = (auto.vueltas * num_nodos) + auto.nodo_actual_idx
                
                # 3. Ordenar y obtener la posición del jugador
                autos_ordenados = sorted(todos_autos, key=lambda a: a.progreso, reverse=True)
                # Solo actualizamos la posición del jugador mientras está en carrera.
                # Al terminar, su posición se congela para evitar el salto a P1.
                if jugador.tiempo_final_ms == 0:
                    if jugador in autos_ordenados:
                        posicion_jugador = autos_ordenados.index(jugador) + 1
                    
            if jugador.tiempo_final_ms > 0 and estado_carrera != "FIN_CARRERA": # El jugador ha terminado
                estado_carrera = "FIN_CARRERA"
                tiempo_fin_carrera = pygame.time.get_ticks()

            if estado_carrera == "FIN_CARRERA":
                if modo_juego == "CARRERA":
                    texto_cuenta = f"PUESTO {posicion_jugador}"
                else:
                    texto_cuenta = f"{formato_tiempo(jugador.tiempo_final_ms)}"
                # Después de 3 segundos, salimos del bucle de la partida para volver al menú
                if tiempo_actual - tiempo_fin_carrera > 3000:
                    corriendo = False

        # C. Renderizado
        pantalla = pygame.display.get_surface()
        cw, ch = pantalla.get_size()
        ANCHO_VIRTUAL = int(cw / ZOOM_CAMARA)
        ALTO_VIRTUAL = int(ch / ZOOM_CAMARA)
        
        # Si la cámara es persiguiendo el auto, el mapa base (antes de girar)
        # tiene que ser al menos igual a la hipotenusa (diagonal) de la pantalla.
        if OPCIONES["modo_camara"] == 1: # CHASING
            diagonal = int(math.hypot(ANCHO_VIRTUAL, ALTO_VIRTUAL))
            render_w, render_h = diagonal, diagonal
        else:
            render_w, render_h = ANCHO_VIRTUAL, ALTO_VIRTUAL
            
        superficie_juego = pygame.Surface((render_w, render_h))

        # Calcular la posición de la cámara usando el tamaño VIRTUAL
        camara_x = jugador.x - (render_w // 2)
        camara_y = jugador.y - (render_h // 2)

        # Limpiar la superficie virtual con negro
        superficie_juego.fill(NEGRO)

        # Dibujar la pista desplazada por la cámara (se mueve en dirección contraria, por eso el menos)
        circuito.dibujar(superficie_juego, camara_x, camara_y)
        
        # Dibujar las marcas de derrape en el suelo
        huellas.dibujar(superficie_juego, camara_x, camara_y)
        if modo_juego.startswith("MULTIJUGADOR"):
            for h_remoto in huellas_remotos.values():
                h_remoto.dibujar(superficie_juego, camara_x, camara_y)
        else:
            for hb in huellas_bots:
                hb.dibujar(superficie_juego, camara_x, camara_y)
        
        # Dibujar el auto usando el método de la clase
        jugador.dibujar(superficie_juego, camara_x, camara_y)
        if modo_juego.startswith("MULTIJUGADOR"):
            for remote_p in remote_players.values():
                remote_p.dibujar(superficie_juego, camara_x, camara_y)
        else:
            for bot in bots:
                bot.dibujar(superficie_juego, camara_x, camara_y)
                
        # APLICAR EL ZOOM Y ROTACIÓN DE CÁMARA
        if OPCIONES["modo_camara"] == 1: # 1 es "CHASING"
            # Rotamos la vista en dirección contraria al auto para que el auto siempre apunte "arriba"
            superficie_rotada = pygame.transform.rotate(superficie_juego, -jugador.angulo)
            
            # Extraemos un recorte EXACTO del centro rotado, dejando fuera las esquinas que quedaron negras
            superficie_final = pygame.Surface((ANCHO_VIRTUAL, ALTO_VIRTUAL))
            rect_rotado = superficie_rotada.get_rect(center=(ANCHO_VIRTUAL//2, ALTO_VIRTUAL//2))
            superficie_final.blit(superficie_rotada, rect_rotado)
            
            pantalla.blit(pygame.transform.scale(superficie_final, (cw, ch)), (0, 0))
        else: # 0 es "CENITAL"
            pantalla.blit(pygame.transform.scale(superficie_juego, (cw, ch)), (0, 0))

        # --- DIBUJAR INTERFAZ DE USUARIO (HUD) ---
        if not cuenta_atras_finalizada and estado_carrera != "PAUSA" and estado_carrera != "PAUSA_OPCIONES":
            tiempo_actual_ms = 0
        else:
            tiempo_actual_ms = pygame.time.get_ticks() - circuito.tiempo_inicio_vuelta
            
        hud.dibujar(pantalla, jugador, tiempo_actual_ms, circuito.mejor_tiempo_vuelta, angulo_volante, mostrar_telemetria, texto_cuenta, posicion=posicion_jugador, total_autos=len(todos_autos), vuelta=jugador.vueltas, total_vueltas=TOTAL_VUELTAS)
        # -------------------------------------

        # Dibujar el menú de pausa por encima de todo si es necesario
        if estado_carrera == "PAUSA":
            dibujar_menu_pausa(pantalla, foco_pausa)
        elif estado_carrera == "PAUSA_OPCIONES":
            dibujar_menu_opciones(pantalla, foco_opciones)

        # Actualizar la ventana completa con lo que acabamos de dibujar
        pygame.display.flip()
        
        # Limitar el juego a 60 fotogramas por segundo (FPS)
        reloj.tick(60)
        await asyncio.sleep(0)

async def main():
    """Función principal que inicializa Pygame y gestiona el bucle de la aplicación."""
    # 1. Inicializar Pygame
    pygame.init()

    # 2. Configurar la pantalla como RESIZABLE por defecto
    if sys.platform == "emscripten":
        pantalla = pygame.display.set_mode((ANCHO, ALTO))
    else:
        try: # Intentar usar SCALED por defecto para mejor calidad en monitores HiDPI
            pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE | pygame.SCALED)
        except pygame.error:
            pantalla = pygame.display.set_mode((ANCHO, ALTO), pygame.RESIZABLE)
    pygame.display.set_caption("im stupid")
    reloj = pygame.time.Clock()

    try:
        while True:
            # El menú se ejecuta en un bucle. Si el usuario lo cierra, el programa termina.
            # Si elige una carrera, devuelve los parámetros y continúa.
            menu_result = await ejecutar_menu(pantalla, reloj) # Devuelve (modo, clase, auto, pista, ip)
            if not menu_result: continue # Si el menú devuelve None, reiniciamos el bucle

            modo_juego, idx_clase, idx_auto, idx_pista, nombre_sala = menu_result

            if modo_juego.startswith("MULTIJUGADOR"):
                websocket, my_id = await ejecutar_lobby_partida(pantalla, reloj, modo_juego, nombre_sala, idx_clase, idx_auto, idx_pista)
                if websocket: # Si el lobby fue exitoso y no se canceló
                    await jugar_partida(pantalla, reloj, modo_juego, idx_clase, idx_auto, idx_pista, websocket, my_id)
            else: # Un Jugador o Contrarreloj
                await jugar_partida(pantalla, reloj, modo_juego, idx_clase, idx_auto, idx_pista)
    except GameExit:
        print("Saliendo del juego...")
    finally:
        pygame.quit()
        print("Pygame cerrado. Adiós.")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except GameExit:
        # Atrapa la excepción si se lanza antes de que comience el bucle principal de `main`.
        pass
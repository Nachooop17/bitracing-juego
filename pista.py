# -*- coding: utf-8 -*-
import pygame
from config import *
from utils import obtener_ruta

class Pista:
    def __init__(self, idx_pista):
        archivo_pista_sel = LISTA_PISTAS[idx_pista]["archivo"]
        archivo_mascara_sel = LISTA_PISTAS[idx_pista]["mascara"]
        imagen_pista = pygame.image.load(obtener_ruta(f"assets/tracks/{archivo_pista_sel}")).convert()

        try:
            imagen_mascara = pygame.image.load(obtener_ruta(f"assets/tracks/{archivo_mascara_sel}")).convert()
        except FileNotFoundError:
            imagen_mascara = pygame.Surface(imagen_pista.get_size())
            imagen_mascara.fill(NEGRO)

        FACTOR_ZOOM = 3
        self.ancho_pista = ANCHO * FACTOR_ZOOM
        self.alto_pista = ALTO * FACTOR_ZOOM
        self.fondo_pista = pygame.transform.scale(imagen_pista, (self.ancho_pista, self.alto_pista))
        self.fondo_mascara = pygame.transform.scale(imagen_mascara, (self.ancho_pista, self.alto_pista))

        # --- BUSCAR PUNTOS DE SPAWN EN LA MÁSCARA (COLOR ROJO) ---
        self.puntos_spawn = []
        escala_x = self.ancho_pista / imagen_mascara.get_width()
        escala_y = self.alto_pista / imagen_mascara.get_height()

        for y in range(0, imagen_mascara.get_height(), 5):
            for x in range(0, imagen_mascara.get_width(), 5):
                color = imagen_mascara.get_at((x, y))
                if color[0] == 255 and color[1] == 0 and color[2] == 0:  # Rojo puro (#FF0000)
                    nuevo_punto = pygame.math.Vector2(x * escala_x, y * escala_y)
                    # Agrupamos píxeles: si está a más de 100px de otro punto guardado, es un box nuevo
                    if not any(p.distance_to(nuevo_punto) < 100 for p in self.puntos_spawn):
                        self.puntos_spawn.append(nuevo_punto)

        if self.puntos_spawn:
            self.spawn_x = self.puntos_spawn[0].x
            self.spawn_y = self.puntos_spawn[0].y
            print(f"Encontrados {len(self.puntos_spawn)} lugares de salida.")
        else:
            self.spawn_x = self.ancho_pista // 2
            self.spawn_y = self.alto_pista - 400
            print("AVISO: No se encontró ningún píxel ROJO puro (255, 0, 0) en la máscara.")
            
        # --- BUSCAR NODOS PARA LAS IAs ---
        print("Generando Trazada Principal (Magenta)...")
        self.nodos_ia = self._extraer_trazada(imagen_mascara, escala_x, escala_y, (255, 0, 255))
        
        print("Generando Trazada Secundaria (Naranja)...")
        self.nodos_ia_secundarios = self._extraer_trazada(imagen_mascara, escala_x, escala_y, (255, 128, 0))
            
        # --- SISTEMA DE TIEMPOS ---
        self.tiempo_inicio_vuelta = pygame.time.get_ticks()
        self.mejor_tiempo_vuelta = None
        self.en_meta = False
        self.primera_vuelta = True
        
        self.color_superficie = (0, 0, 0, 255)

    def reiniciar_tiempos(self):
        self.primera_vuelta = True
        self.tiempo_inicio_vuelta = pygame.time.get_ticks()

    def obtener_posicion_spawn(self, indice):
        if self.puntos_spawn and indice < len(self.puntos_spawn):
            return self.puntos_spawn[indice].x, self.puntos_spawn[indice].y
        
        # Plan B por si dibujaste menos boxes de los que se necesitan
        if indice == 0: return self.spawn_x, self.spawn_y
        elif indice == 1: return self.spawn_x + 80, self.spawn_y + 80
        elif indice == 2: return self.spawn_x - 80, self.spawn_y + 80
        else: return self.spawn_x, self.spawn_y + (indice * 80)

    def _extraer_trazada(self, imagen_mascara, escala_x, escala_y, color_obj):
        puntos = []
        for y in range(0, imagen_mascara.get_height(), 5):
            for x in range(0, imagen_mascara.get_width(), 5):
                c = imagen_mascara.get_at((x, y))
                # Comprobamos los canales RGB sin importar el canal Alfa
                if c[0] == color_obj[0] and c[1] == color_obj[1] and c[2] == color_obj[2]:
                    puntos.append(pygame.math.Vector2(x * escala_x, y * escala_y))
        nodos = []
        if puntos:
            actual = puntos.pop(0)
            nodos.append(actual)
            while puntos:
                actual = min(puntos, key=lambda p: actual.distance_squared_to(p))
                puntos.remove(actual)
                if nodos[-1].distance_to(actual) >= 80:
                    nodos.append(actual)
        return nodos

    def actualizar_superficie(self, auto_obj, es_jugador=True):
        x_int = int(auto_obj.x)
        y_int = int(auto_obj.y)

        if 0 <= x_int < self.ancho_pista and 0 <= y_int < self.alto_pista:
            self.color_superficie = self.fondo_mascara.get_at((x_int, y_int))
            
            if self.color_superficie != (0, 255, 255, 255):
                auto_obj.en_meta = False
                
            if self.color_superficie == (0, 255, 0, 255): # Pasto
                auto_obj.velocidad_maxima = 8.0
                auto_obj.friccion_libre = 0.1
                auto_obj.estres_llantas = 1.0
            elif self.color_superficie == (0, 0, 255, 255): # Pitstop
                auto_obj.velocidad_maxima = 3.0
                auto_obj.friccion_libre = 0.02
                auto_obj.desgaste_neumaticos = max(0.0, auto_obj.desgaste_neumaticos - 0.005)
            elif self.color_superficie == (255, 255, 0, 255): # Muro
                # Separación posicional: empujamos el auto hacia atrás para que no se atasque
                if auto_obj.vector_velocidad.length() > 0.1:
                    retroceso = auto_obj.vector_velocidad.normalize()
                    auto_obj.x -= retroceso.x * 5.0
                    auto_obj.y -= retroceso.y * 5.0
                auto_obj.vector_velocidad *= 0.8 # Pierde velocidad al raspar contra el muro
                auto_obj.velocidad_maxima = 3.0
                auto_obj.friccion_libre = 0.3
            elif self.color_superficie == (0, 255, 255, 255): # Meta
                auto_obj.velocidad_maxima, auto_obj.friccion_libre = auto_obj.velocidad_maxima_base, 0.02
                if not auto_obj.en_meta:
                    tiempo_actual = pygame.time.get_ticks()
                    # Prevenir que cuente vuelta nomás al arrancar (debe pasar tiempo)
                    if auto_obj.ultimo_tiempo_meta > 0:
                        tiempo_vuelta = tiempo_actual - auto_obj.ultimo_tiempo_meta
                        if tiempo_vuelta > 5000:
                            auto_obj.vueltas += 1
                            if es_jugador:
                                if self.mejor_tiempo_vuelta is None or tiempo_vuelta < self.mejor_tiempo_vuelta:
                                    self.mejor_tiempo_vuelta = tiempo_vuelta
                                self.tiempo_inicio_vuelta = tiempo_actual
                            auto_obj.ultimo_tiempo_meta = tiempo_actual
                    else:
                        auto_obj.ultimo_tiempo_meta = tiempo_actual
                        if es_jugador:
                            self.tiempo_inicio_vuelta = tiempo_actual
                    auto_obj.en_meta = True
            else: # Asfalto normal
                auto_obj.velocidad_maxima, auto_obj.friccion_libre = auto_obj.velocidad_maxima_base, 0.02

    def dibujar(self, superficie, camara_x, camara_y):
        superficie.blit(self.fondo_pista, (-camara_x, -camara_y))
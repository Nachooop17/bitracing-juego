# -*- coding: utf-8 -*-
import pygame
import math
from config import *
from utils import formato_tiempo, obtener_ruta

class HUD:
    def __init__(self):
        try:
            self.fuente_telemetria = pygame.font.Font(obtener_ruta("assets/fuentes/minecraft.ttf"), 20)
            self.fuente_cuenta = pygame.font.Font(obtener_ruta("assets/fuentes/minecraft.ttf"), 120)
        except Exception:
            self.fuente_telemetria = pygame.font.SysFont("Arial", 20)
            self.fuente_cuenta = pygame.font.SysFont("Arial", 120, bold=True)
            
        try:
            self.fuente_posicion = pygame.font.Font(obtener_ruta("assets/fuentes/minecraft.ttf"), 70)
            self.fuente_vuelta = pygame.font.Font(obtener_ruta("assets/fuentes/minecraft.ttf"), 20)
        except Exception:
            self.fuente_posicion = pygame.font.SysFont("Arial", 70, bold=True)
            self.fuente_vuelta = pygame.font.SysFont("Arial", 20, bold=True)
        
        # --- CARGAR EL VOLANTE VISUAL ---
        try:
            imagen_cargada = pygame.image.load(obtener_ruta("assets/HUD/volante.png")).convert_alpha()
            nuevo_ancho = int(imagen_cargada.get_width() * 2.5)
            nuevo_alto = int(imagen_cargada.get_height() * 2.5)
            self.imagen_volante = pygame.transform.scale(imagen_cargada, (nuevo_ancho, nuevo_alto))
        except Exception:
            # Fallback en caso de que no encuentre la imagen
            self.imagen_volante = pygame.Surface((60, 40), pygame.SRCALPHA)
            pygame.draw.rect(self.imagen_volante, (40, 40, 40), (5, 5, 50, 30), border_radius=10)
            pygame.draw.rect(self.imagen_volante, (20, 20, 20), (0, 5, 12, 30), border_radius=5)
            pygame.draw.rect(self.imagen_volante, (20, 20, 20), (48, 5, 12, 30), border_radius=5)

        # --- CARGAR VELOCÍMETRO ---
        try:
            bg_cargado = pygame.image.load(obtener_ruta("assets/HUD/velocimetro_bg.png")).convert_alpha()
            nuevo_ancho_bg = int(bg_cargado.get_width() * 2.0)
            nuevo_alto_bg = int(bg_cargado.get_height() * 2.0)
            self.bg_velocimetro = pygame.transform.scale(bg_cargado, (nuevo_ancho_bg, nuevo_alto_bg))
            
            aguja_cargada = pygame.image.load(obtener_ruta("assets/HUD/velocimetro_aguja.png")).convert_alpha()
            nuevo_ancho_aguja = int(aguja_cargada.get_width() * 1.5)
            nuevo_alto_aguja = int(aguja_cargada.get_height() * 1.5)
            self.aguja_velocimetro = pygame.transform.scale(aguja_cargada, (nuevo_ancho_aguja, nuevo_alto_aguja))
        except Exception:
            # Fallback en caso de que no encuentre los sprites
            self.bg_velocimetro = pygame.Surface((120, 120), pygame.SRCALPHA)
            pygame.draw.circle(self.bg_velocimetro, (30, 30, 30), (60, 60), 60)
            pygame.draw.circle(self.bg_velocimetro, (150, 150, 150), (60, 60), 60, 3)
            
            # Dibujar marcas del tacómetro (180 grados de arco)
            for ang in range(-45, 136, 18):
                rad = math.radians(ang)
                x1 = 60 + math.cos(rad) * 45
                y1 = 60 - math.sin(rad) * 45
                x2 = 60 + math.cos(rad) * 55
                y2 = 60 - math.sin(rad) * 55
                pygame.draw.line(self.bg_velocimetro, BLANCO, (x1, y1), (x2, y2), 2)
                
            self.aguja_velocimetro = pygame.Surface((120, 120), pygame.SRCALPHA)
            # La aguja DEBE estar apuntando a la derecha (0 grados) y tener el eje en el centro
            pygame.draw.polygon(self.aguja_velocimetro, ROJO, [(60, 56), (105, 60), (60, 64)])
            pygame.draw.circle(self.aguja_velocimetro, (100, 0, 0), (60, 60), 6)
            
        # --- CARGAR CHASIS DEL VISUALIZADOR DE LLANTAS ---
        self.sprites_chasis = {}
        try:
            # Intentamos cargar los 3 estados. Si el verde se llama solo "chasis.png", lo cubre.
            try: img_v = pygame.image.load(obtener_ruta("assets/HUD/chasis_verde.png")).convert_alpha()
            except: img_v = pygame.image.load(obtener_ruta("assets/HUD/chasis.png")).convert_alpha()
            
            img_a = pygame.image.load(obtener_ruta("assets/HUD/chasis_amarillo.png")).convert_alpha()
            img_r = pygame.image.load(obtener_ruta("assets/HUD/chasis_rojo.png")).convert_alpha()
            
            for estado, img in [("verde", img_v), ("amarillo", img_a), ("rojo", img_r)]:
                w, h = int(img.get_width() * 2), int(img.get_height() * 1.5)
                self.sprites_chasis[estado] = pygame.transform.scale(img, (w, h))
        except Exception:
            self.sprites_chasis = None

    def dibujar(self, pantalla, jugador, tiempo_actual_ms, mejor_tiempo_vuelta, angulo_volante, mostrar_telemetria, texto_cuenta="", posicion=1, total_autos=5, vuelta=1, total_vueltas=10):
        cw, ch = pantalla.get_size()
        
        if mostrar_telemetria:
            self._dibujar_telemetria(pantalla, jugador)
        
        self._dibujar_tiempos(pantalla, tiempo_actual_ms, mejor_tiempo_vuelta, cw)
        self._dibujar_visualizador_llantas(pantalla, jugador, cw, ch)
        self._dibujar_volante(pantalla, angulo_volante, cw, ch)
        self._dibujar_velocimetro(pantalla, jugador, ch)
        self._dibujar_posicion_vueltas(pantalla, posicion, total_autos, vuelta, total_vueltas)
        
        if texto_cuenta:
            # Darle un contorno negro para que resalte
            txt_sombra = self.fuente_cuenta.render(texto_cuenta, True, NEGRO)
            txt = self.fuente_cuenta.render(texto_cuenta, True, (255, 255, 0)) # Amarillo
            rect = txt.get_rect(center=(cw//2, ch//3))
            pantalla.blit(txt_sombra, (rect.x + 4, rect.y + 4))
            pantalla.blit(txt, rect.topleft)

    def _dibujar_posicion_vueltas(self, pantalla, posicion, total_autos, vuelta, total_vueltas):
        if total_autos > 1:
            texto_pos = self.fuente_posicion.render(f"P{posicion}", True, (255, 215, 0)) # Dorado
        else:
            texto_pos = self.fuente_posicion.render("RELOJ", True, (0, 255, 255)) # Cyan
        
        color_vuelta = BLANCO
        if vuelta == total_vueltas: color_vuelta = (0, 255, 0)
        elif vuelta > total_vueltas: color_vuelta = ROJO
        
        v_mostrar = min(vuelta, total_vueltas)
        texto_vuelta = self.fuente_vuelta.render(f"VUELTA: {v_mostrar}/{total_vueltas}", True, color_vuelta)
        
        pantalla.blit(texto_pos, (20, 10))
        # Posicionamos la vuelta justo debajo de la posición usando su altura
        pantalla.blit(texto_vuelta, (25, 15 + texto_pos.get_height()))

    def _dibujar_telemetria(self, pantalla, jugador):
        texto_velocidad = self.fuente_telemetria.render(f"Velocidad: {abs(jugador.velocidad):.1f} / {jugador.velocidad_maxima}", True, BLANCO)
        texto_giro = self.fuente_telemetria.render(f"Cap. de giro: {jugador.tasa_giro:.2f}", True, BLANCO)
        
        estado_peso = "Neutral"
        if jugador.peso_longitudinal > 0.55: estado_peso = "Adelante (+ Giro)"
        elif jugador.peso_longitudinal < 0.45: estado_peso = "Atras (- Giro)"
        texto_peso = self.fuente_telemetria.render(f"Peso frontal: {jugador.peso_longitudinal*100:.0f}% ({estado_peso})", True, BLANCO)
        
        color_desgaste = ROJO if jugador.desgaste_neumaticos > 0.75 else BLANCO
        texto_desgaste = self.fuente_telemetria.render(f"Desgaste Neumaticos: {jugador.desgaste_neumaticos*100:.1f}%", True, color_desgaste)

        # Bajamos la telemetría para que no tape la interfaz de las posiciones
        pantalla.blit(texto_velocidad, (10, 140))
        pantalla.blit(texto_giro, (10, 165))
        pantalla.blit(texto_peso, (10, 190))
        pantalla.blit(texto_desgaste, (10, 215))

    def _dibujar_tiempos(self, pantalla, tiempo_actual_ms, mejor_tiempo_vuelta, cw):
        texto_tiempo = self.fuente_telemetria.render(f"Tiempo: {formato_tiempo(tiempo_actual_ms)}", True, BLANCO)
        texto_mejor = self.fuente_telemetria.render(f"Mejor: {formato_tiempo(mejor_tiempo_vuelta)}", True, (0, 255, 255))
        
        # Anclamos el texto a una posición X fija (230 píxeles desde el borde derecho) para evitar que vibre
        pos_x = cw - 230
        pantalla.blit(texto_tiempo, (pos_x, 10))
        pantalla.blit(texto_mejor, (pos_x, 35))

    def _dibujar_visualizador_llantas(self, pantalla, jugador, cw, ch):
        derrape_base = jugador.nivel_derrape * 70
        
        mod_delantero = max(0, (0.5 - jugador.peso_longitudinal) * 150) if jugador.nivel_derrape > 0.2 else 0
        mod_trasero = max(0, (jugador.peso_longitudinal - 0.5) * 150) if jugador.nivel_derrape > 0.2 else 0

        r_del = min(255, int(derrape_base + mod_delantero))
        color_del = (r_del, max(0, 255 - r_del), 0)
        
        r_tras = min(255, int(derrape_base + mod_trasero))
        color_tras = (r_tras, max(0, 255 - r_tras), 0)

        hud_x, hud_y = cw - 70, ch - 80
        
        # Determinamos el estado global del derrape para elegir qué sprite mostrar
        max_r = max(r_del, r_tras)
        if max_r < 85: estado_llantas = "verde"
        elif max_r < 170: estado_llantas = "amarillo"
        else: estado_llantas = "rojo"
        
        if self.sprites_chasis and estado_llantas in self.sprites_chasis:
            rect_chasis = self.sprites_chasis[estado_llantas].get_rect(center=(hud_x + 20, hud_y + 25))
            pantalla.blit(self.sprites_chasis[estado_llantas], rect_chasis.topleft)
        else:
            # Fallback en caso de que falten los sprites
            pygame.draw.rect(pantalla, color_del, (hud_x, hud_y + 5, 8, 12))            
            pygame.draw.rect(pantalla, color_del, (hud_x + 32, hud_y + 5, 8, 12))       
            pygame.draw.rect(pantalla, color_tras, (hud_x, hud_y + 33, 8, 12))          
            pygame.draw.rect(pantalla, color_tras, (hud_x + 32, hud_y + 33, 8, 12))
            pygame.draw.rect(pantalla, (80, 80, 80), (hud_x + 10, hud_y, 20, 50))

        ancho_barra, alto_barra = 8, 50
        desgaste_restante = 1.0 - jugador.desgaste_neumaticos
        altura_actual = int(alto_barra * desgaste_restante)
        
        r_bar = int(min(255, jugador.desgaste_neumaticos * 2 * 255))
        g_bar = int(min(255, desgaste_restante * 2 * 255))
        color_barra = (max(0, min(255, r_bar)), max(0, min(255, g_bar)), 0)
        
        pygame.draw.rect(pantalla, (50, 0, 0), (hud_x - 30, hud_y, ancho_barra, alto_barra))
        if altura_actual > 0:
            pygame.draw.rect(pantalla, color_barra, (hud_x - 30, hud_y + (alto_barra - altura_actual), ancho_barra, altura_actual))
        pygame.draw.rect(pantalla, BLANCO, (hud_x - 30, hud_y, ancho_barra, alto_barra), 1)

    def _dibujar_volante(self, pantalla, angulo_volante, cw, ch):
        centro_x, centro_y = (cw - 70) - 100, (ch - 80) + 25  # Movido hacia la izquierda
        volante_rotado = pygame.transform.rotate(self.imagen_volante, angulo_volante)
        rect_volante = volante_rotado.get_rect(center=(centro_x, centro_y))
        pantalla.blit(volante_rotado, rect_volante.topleft)

    def _dibujar_velocimetro(self, pantalla, jugador, ch):
        centro_x, centro_y = 90, ch - 50  # Bajamos el velocímetro 30 píxeles
        
        # 1. Dibujar el fondo del velocímetro
        rect_bg = self.bg_velocimetro.get_rect(center=(centro_x, centro_y))
        pantalla.blit(self.bg_velocimetro, rect_bg.topleft)
        
        # 2. Calcular el ángulo de la aguja según la velocidad
        velocidad_maxima_reloj = 8.0  # Usamos 8 como el tope máximo físico
        velocidad_actual = min(abs(jugador.velocidad), velocidad_maxima_reloj)
        porcentaje = velocidad_actual / velocidad_maxima_reloj
        
        # Como la aguja está dibujada hacia ARRIBA y el medidor es un semicírculo:
        # 90° es Izquierda (0 km/h), 0° es Arriba (mitad) y -90° es Derecha (max km/h)
        angulo_aguja = 90 - (porcentaje * 180)
        
        # 3. Rotar la aguja
        aguja_rotada = pygame.transform.rotate(self.aguja_velocimetro, angulo_aguja)
        rect_aguja = aguja_rotada.get_rect(center=(centro_x, centro_y))
        pantalla.blit(aguja_rotada, rect_aguja.topleft)
        
        # 4. Texto digital opcional en el centro
        texto_vel = self.fuente_telemetria.render(f"{abs(jugador.velocidad)*30:.0f} km/h", True, BLANCO)
        pantalla.blit(texto_vel, (centro_x - texto_vel.get_width()//2, centro_y + 20))
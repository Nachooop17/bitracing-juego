# -*- coding: utf-8 -*-
import pygame
import math
import random

class GestorHuellas:
    def __init__(self):
        self.historial_derrapes = []
        self.derrape_actual = []

    def actualizar(self, jugador, circuito):
        if jugador.nivel_derrape > 0.2:
            # Color: Café si está en el pasto, Gris oscuro en asfalto/pista
            color_actual = circuito.color_superficie
            color_marca = (90, 60, 30) if color_actual == (0, 255, 0, 255) else (40, 40, 40)
            
            # Calcular posición de las ruedas traseras según el ángulo
            rad = math.radians(jugador.angulo)
            frente_x = -math.sin(rad)
            frente_y = -math.cos(rad)
            derecha_x = -frente_y
            derecha_y = frente_x
            
            # Ajustamos ~8px hacia atrás desde el centro
            atras_x = jugador.x - frente_x * 8
            atras_y = jugador.y - frente_y * 8
            
            # --- AÑADIR TEXTURA ---
            ruido_x = random.uniform(-0.5, 0.5)
            ruido_y = random.uniform(-0.5, 0.5)
            
            rueda_izq = (atras_x - derecha_x * 4 + ruido_x, atras_y - derecha_y * 4 + ruido_y)
            rueda_der = (atras_x + derecha_x * 4 + ruido_x, atras_y + derecha_y * 4 + ruido_y)
            
            var = random.randint(-12, 12)
            color_textura = (
                max(0, min(255, color_marca[0] + var)),
                max(0, min(255, color_marca[1] + var)),
                max(0, min(255, color_marca[2] + var))
            )
            
            grosor_aleatorio = random.choice([1, 2, 2])
            
            self.derrape_actual.append({'izq': rueda_izq, 'der': rueda_der, 'color': color_textura, 'grosor': grosor_aleatorio})
        else:
            if len(self.derrape_actual) > 0:
                self.historial_derrapes.append(self.derrape_actual)
                self.derrape_actual = []
                # Limitar el historial para no saturar la memoria
                if len(self.historial_derrapes) > 2:
                    self.historial_derrapes.pop(0)

    def dibujar(self, superficie_juego, camara_x, camara_y):
        for derrape in self.historial_derrapes + [self.derrape_actual]:
            if len(derrape) > 1:
                for i in range(1, len(derrape)):
                    p1 = derrape[i-1]
                    p2 = derrape[i]
                    
                    # Convertir a coordenadas de cámara (pantalla virtual)
                    izq1 = (p1['izq'][0] - camara_x, p1['izq'][1] - camara_y)
                    izq2 = (p2['izq'][0] - camara_x, p2['izq'][1] - camara_y)
                    der1 = (p1['der'][0] - camara_x, p1['der'][1] - camara_y)
                    der2 = (p2['der'][0] - camara_x, p2['der'][1] - camara_y)
                    
                    pygame.draw.line(superficie_juego, p2['color'], izq1, izq2, p2.get('grosor', 2))
                    pygame.draw.line(superficie_juego, p2['color'], der1, der2, p2.get('grosor', 2))
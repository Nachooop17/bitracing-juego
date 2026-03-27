# -*- coding: utf-8 -*-
import pygame
import math
import random
from auto import Auto

class AutoIA(Auto):
    def __init__(self, x, y, imagen, nodos_principal, nodos_secundario):
        super().__init__(x, y, imagen)
        self.nodos_principal = nodos_principal
        self.nodos_secundario = nodos_secundario if nodos_secundario else nodos_principal
        self.nodos = self.nodos_principal
        self.usando_secundaria = False
        # Empezamos buscando el nodo más cercano a donde apareció para no dar una vuelta entera
        self.nodo_objetivo_idx = self._encontrar_nodo_mas_cercano() if self.nodos else 0
        
        self.tiempo_ultima_decision = 0
        self.frames_error = 0
        
        # --- VENTAJAS DE LA IA ---
        # Le damos un poco más de agarre mínimo al derrapar para que no pierda el control tan fácil.
        # (El jugador tiene 0.01 de agarre mínimo)
        self.agarre_minimo = 0.09

    def _encontrar_nodo_mas_cercano(self):
        if not self.nodos: return 0
        pos = pygame.math.Vector2(self.x, self.y)
        distancias = [pos.distance_squared_to(nodo) for nodo in self.nodos]
        idx_cercano = distancias.index(min(distancias))
        # Saltamos un par de nodos hacia adelante para evitar que intente retroceder al arrancar
        return (idx_cercano + 2) % len(self.nodos)

    def cambiar_linea(self, usar_secundaria):
        if self.usando_secundaria != usar_secundaria:
            self.usando_secundaria = usar_secundaria
            self.nodos = self.nodos_secundario if usar_secundaria else self.nodos_principal
            if self.nodos:
                self.nodo_objetivo_idx = self._encontrar_nodo_mas_cercano()

    def actualizar_ia(self, circuito, todos_autos):
        teclas_virtuales = {
            pygame.K_UP: False, pygame.K_DOWN: False,
            pygame.K_LEFT: False, pygame.K_RIGHT: False,
            pygame.K_w: False, pygame.K_s: False,
            pygame.K_a: False, pygame.K_d: False
        }

        if not self.nodos:
            teclas_virtuales[pygame.K_DOWN] = True # Frena si no sabe a dónde ir
            circuito.actualizar_superficie(self, es_jugador=False)
            self.actualizar(teclas_virtuales)
            return

        # --- CEREBRO DINÁMICO (Decisiones de carrera) ---
        tiempo_actual = pygame.time.get_ticks()
        if tiempo_actual - self.tiempo_ultima_decision > 1500: # Piensa/revalúa cada 1.5 segundos
            self.tiempo_ultima_decision = tiempo_actual
            
            # Buscar si hay un rival (jugador u otro bot) cerca
            hay_rival_cerca = False
            for otro in todos_autos:
                if otro == self: continue
                dist = pygame.math.Vector2(self.x, self.y).distance_to((otro.x, otro.y))
                if dist < 250: # Aprox 3-4 autos de distancia adelante, atrás o a los lados
                    hay_rival_cerca = True
                    break
                    
            # 1 en 3 de tomar la trazada secundaria si hay pelea
            if hay_rival_cerca and random.randint(1, 3) == 1:
                self.cambiar_linea(True)
            else:
                self.cambiar_linea(False)
                
            # 1 en 10 de dudar/cometer error (incentiva el chapa a chapa)
            if random.randint(1, 10) == 1:
                self.frames_error = 20 # Duda por ~0.3 segundos
        # ------------------------------------------------

        # 1. ¿A qué nodo vamos?
        objetivo = self.nodos[self.nodo_objetivo_idx]
        
        # 2. La Zanahoria: Si estamos a menos de 150 píxeles, cambiamos al siguiente nodo (Look-ahead)
        distancia = pygame.math.Vector2(self.x, self.y).distance_to(objetivo)
        if distancia < 100:  # 100 píxeles da un giro mucho más fluido y natural sin cortar tanta pista
            self.nodo_objetivo_idx = (self.nodo_objetivo_idx + 1) % len(self.nodos)
            objetivo = self.nodos[self.nodo_objetivo_idx]

        # 3. Calcular qué ángulo necesita para apuntar al nodo
        dx = objetivo.x - self.x
        dy = objetivo.y - self.y
        angulo_hacia_objetivo = math.degrees(math.atan2(-dx, -dy))
        
        # 4. Ajustar el volante virtual
        diferencia_angulo = (angulo_hacia_objetivo - self.angulo) % 360
        if diferencia_angulo > 180: diferencia_angulo -= 360

        margen_giro = 3
        if diferencia_angulo > margen_giro: teclas_virtuales[pygame.K_LEFT] = True
        elif diferencia_angulo < -margen_giro: teclas_virtuales[pygame.K_RIGHT] = True

        # 5. Ajustar acelerador y freno (Predicción de curvas)
        # Miramos 2 nodos más adelante para saber si se aproxima una curva cerrada
        nodo_futuro_idx = (self.nodo_objetivo_idx + 2) % len(self.nodos)
        objetivo_futuro = self.nodos[nodo_futuro_idx]
        
        dx_futuro = objetivo_futuro.x - self.x
        dy_futuro = objetivo_futuro.y - self.y
        angulo_futuro = math.degrees(math.atan2(-dx_futuro, -dy_futuro))
        
        dif_futura = (angulo_futuro - self.angulo) % 360
        if dif_futura > 180: dif_futura -= 360

        # Evaluamos la severidad de la curva tomando el mayor ángulo de giro
        severidad_curva = max(abs(diferencia_angulo), abs(dif_futura))

        # IA BUFEADA: Mucho más agresiva, toma curvas rápidas a fondo
        if severidad_curva > 35 and self.velocidad > 5.0:
            pass # Curva muy pronunciada: Solo suelta el acelerador
        else:
            teclas_virtuales[pygame.K_UP] = True # Curvas normales y rectas: Acelera a fondo

        # --- APLICAR ERROR HUMANO ---
        if self.frames_error > 0:
            self.frames_error -= 1
            teclas_virtuales[pygame.K_UP] = False   # Suelta el acelerador por miedo
            teclas_virtuales[pygame.K_DOWN] = False # No frena brusco, solo se deja llevar perdiendo inercia
            
        circuito.actualizar_superficie(self, es_jugador=False)
        self.actualizar(teclas_virtuales)
# -*- coding: utf-8 -*-
import pygame
import math

class Auto:
    def __init__(self, x, y, imagen):
        self.x = float(x)
        self.y = float(y)
        
        # NUEVO: Inercia real con vectores
        self.vector_velocidad = pygame.math.Vector2(0, 0)
        self.velocidad = 0  # Mantenemos este escalar para que la telemetría siga funcionando
        self.angulo = 0
        
        # Progreso de Carrera
        self.vueltas = 1
        self.en_meta = False
        self.ultimo_tiempo_meta = 0
        self.progreso = 0
        self.nodo_actual_idx = 0
        self.tiempo_final_ms = 0 # 0 = no ha terminado, > 0 = tiempo total de carrera en ms
        
        # Físicas Ajustadas
        self.aceleracion = 0.12
        self.freno = 0.2
        self.friccion_libre = 0.02
        self.desgaste_neumaticos = 0.0  # 0.0 = Nuevos, 1.0 = Destruidos
        self.agarre_minimo = 0.01  # Grip al derrapar al máximo
        self.estres_llantas = 0.0  # "Calor" o saturación de llantas (0.0 a 1.0)
        self.nivel_derrape = 0.0 # Guardará qué tanto resbala el auto
        self.velocidad_maxima = 6
        self.velocidad_maxima_base = 6
        
        self.peso_longitudinal = 0.5
        self.imagen_original = imagen
        self.tasa_giro = 0

    def actualizar(self, teclas):
        # 1. Calcular Vectores de Dirección del auto
        rad = math.radians(self.angulo)
        # Calculamos el frente (-sin y -cos es por cómo Pygame dibuja las Y invertidas)
        frente_x = -math.sin(rad)
        frente_y = -math.cos(rad)
        vector_frente = pygame.math.Vector2(frente_x, frente_y)
        
        # El vector lateral (hacia las puertas) está a 90 grados del frente
        vector_derecha = pygame.math.Vector2(-frente_y, frente_x)
        
        objetivo_peso = 0.5  # Estado neutral por defecto
        aceleracion_actual = 0

        # 2. Aceleración y Freno
        if teclas[pygame.K_UP] or teclas[pygame.K_w]:
            aceleracion_actual = self.aceleracion
            objetivo_peso = 0.35
        elif teclas[pygame.K_DOWN] or teclas[pygame.K_s]:
            aceleracion_actual = -self.freno
            # Si tenemos inercia hacia adelante, estamos frenando (peso adelante)
            if self.vector_velocidad.dot(vector_frente) > 0:
                objetivo_peso = 0.75
            else:
                objetivo_peso = 0.35

        # Aplicar fuerza al motor (Inercia vectorial)
        if aceleracion_actual != 0:
            self.vector_velocidad += vector_frente * aceleracion_actual

        # Fricción natural por rodamiento (frena el auto si no aceleras)
        if self.vector_velocidad.length() > 0:
            if self.vector_velocidad.length() <= self.friccion_libre:
                self.vector_velocidad = pygame.math.Vector2(0, 0)
            else:
                self.vector_velocidad -= self.vector_velocidad.normalize() * self.friccion_libre

        self.peso_longitudinal += (objetivo_peso - self.peso_longitudinal) * 0.15

        # Limitar a la velocidad máxima absoluta
        if self.vector_velocidad.length() > self.velocidad_maxima:
            self.vector_velocidad.scale_to_length(self.velocidad_maxima)

        # 3. LA MAGIA: Físicas de Derrape (Grip Lateral)
        if self.vector_velocidad.length() > 0:
            # Proyectar cuánta inercia va hacia adelante y cuánta de costado
            vel_frente = vector_frente * self.vector_velocidad.dot(vector_frente)
            vel_lateral = vector_derecha * self.vector_velocidad.dot(vector_derecha)
            
            fuerza_centrifuga = vel_lateral.length()

            # --- DESGASTE DE NEUMÁTICOS ---
            # Se gastan un poquito al rodar, y mucho más al soportar fuerza centrífuga (curvas/derrapes)
            desgaste_rodamiento = abs(self.velocidad) * 0.000002
            desgaste_curva = fuerza_centrifuga * 0.00005
            self.desgaste_neumaticos += desgaste_rodamiento + desgaste_curva
            self.desgaste_neumaticos = min(1.0, self.desgaste_neumaticos)

            # --- SISTEMA DE ESTRÉS DE LLANTAS (Saturación) ---
            if abs(self.velocidad) > 3.0:
                if fuerza_centrifuga > 0.1:
                    # A velocidad 6 o menos, el estrés sube MUY lentamente (casi 10x más lento)
                    tasa_estres = 0.0015 if abs(self.velocidad) <= 6.0 else 0.015
                    self.estres_llantas += fuerza_centrifuga * tasa_estres
                else:
                    self.estres_llantas -= 0.04  # Se enfrían al ir recto
            else:
                self.estres_llantas -= 0.1 # Se enfrían rápidamente a baja velocidad
                
            self.estres_llantas = max(0.0, min(1.0, self.estres_llantas))

            # --- CURVA DE AGARRE DINÁMICA (Basada en desgaste) ---
            # A 0% desgaste: tolerancia 0.6, agarre 0.7
            # A 50% desgaste (estado anterior): tolerancia 0.3, agarre 0.5
            # A 100% desgaste: tolerancia casi 0, agarre 0.3
            tolerancia_estres = max(0.01, 0.6 - (self.desgaste_neumaticos * 0.6))
            agarre_dinamico = 0.7 - (self.desgaste_neumaticos * 0.4)

            if abs(self.velocidad) < 3.0:
                agarre_actual = 1.0  # Grip 100% perfecto a baja velocidad
            elif abs(self.velocidad) < 5.0:
                # Transición súper suave entre el grip perfecto (1.0) y el grip normal
                factor = (abs(self.velocidad) - 3.0) / 2.0
                agarre_actual = 1.0 - (factor * (1.0 - agarre_dinamico))
            elif self.estres_llantas < tolerancia_estres:
                agarre_actual = agarre_dinamico # "Aguanta un ratito"
            else:
                # Pierde grip gradualmente hasta el mínimo
                porc_perdida = (self.estres_llantas - tolerancia_estres) / (1.0 - tolerancia_estres)
                agarre_actual = agarre_dinamico - (porc_perdida * (agarre_dinamico - self.agarre_minimo))

            # Aplicamos la reducción de deslizamiento con el agarre calculado
            vel_lateral *= (1.0 - agarre_actual)
            
            # Medimos el derrape final para enviarlo al HUD del jugador
            self.nivel_derrape = vel_lateral.length()

            # Reconstruir la inercia total con la corrección del derrape
            self.vector_velocidad = vel_frente + vel_lateral
        else:
            self.nivel_derrape = 0.0
            self.estres_llantas = max(0.0, self.estres_llantas - 0.1)

        # 4. Calcular velocidad para la telemetría y para el radio de giro
        producto_punto = self.vector_velocidad.dot(vector_frente)
        # Mantenemos 'self.velocidad' como escalar (+ si va adelante, - si va en reversa)
        self.velocidad = self.vector_velocidad.length() * (1 if producto_punto >= 0 else -1)

        tasa_giro_base = max(1.5, 5.0 - (abs(self.velocidad) * 0.4))
        self.tasa_giro = tasa_giro_base * (self.peso_longitudinal * 2.0)

        if abs(self.velocidad) > 0.1:
            direccion = 1 if self.velocidad > 0 else -1
            if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
                self.angulo += self.tasa_giro * direccion
            elif teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
                self.angulo -= self.tasa_giro * direccion

        # 5. Aplicar la inercia finalmente a la posición en el mundo
        self.x += self.vector_velocidad.x
        self.y += self.vector_velocidad.y

    def dibujar(self, pantalla, camara_x=0, camara_y=0):
        sprite_rotado = pygame.transform.rotate(self.imagen_original, self.angulo)
        # Posición relativa a la cámara
        pos_pantalla = (int(self.x - camara_x), int(self.y - camara_y))
        rect_rotado = sprite_rotado.get_rect(center=pos_pantalla)
        pantalla.blit(sprite_rotado, rect_rotado.topleft)
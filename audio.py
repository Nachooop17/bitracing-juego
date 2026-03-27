# -*- coding: utf-8 -*-
import pygame
from utils import obtener_ruta

class GestorAudio:
    def __init__(self):
        pygame.mixer.init()
        self.sonidos_activos = False
        try:
            self.sonido_derrape = pygame.mixer.Sound(obtener_ruta("assets/sonidos/derrape.wav"))
            # Bajamos el volumen del derrape de forma estática para que sea sutil
            self.sonido_derrape.set_volume(0.07)
            self.canal_derrape = pygame.mixer.Channel(1)
            self.sonidos_activos = True
        except Exception as e:
            print("Aviso: No se encontró derrape.wav en assets/sonidos/")
            
        self.motor_activo = False
        try:
            # Sonido para cuando se presiona el acelerador
            self.sonido_aceleracion = pygame.mixer.Sound(obtener_ruta("assets/sonidos/motor_gt3.wav"))
            self.canal_aceleracion = pygame.mixer.Channel(2)
            self.canal_aceleracion.play(self.sonido_aceleracion, loops=-1)
            self.vol_acel_actual = 0.0
            self.canal_aceleracion.set_volume(self.vol_acel_actual)

            # Sonido para cuando se suelta el acelerador (pero hay inercia)
            self.sonido_desaceleracion = pygame.mixer.Sound(obtener_ruta("assets/sonidos/desaceleracion.wav"))
            self.canal_desaceleracion = pygame.mixer.Channel(3)
            self.canal_desaceleracion.play(self.sonido_desaceleracion, loops=-1)
            self.vol_decel_actual = 0.0
            self.canal_desaceleracion.set_volume(self.vol_decel_actual)

            self.motor_activo = True
        except Exception as e:
            print(f"Aviso: No se pudo cargar un sonido de motor: {e}")
            
    def actualizar_derrape(self, esta_derrapando):
        if not self.sonidos_activos:
            return
            
        if esta_derrapando:
            if not self.canal_derrape.get_busy():
                self.canal_derrape.play(self.sonido_derrape, loops=-1)
        else:
            if self.canal_derrape.get_busy():
                self.canal_derrape.stop()

    def actualizar_motor(self, velocidad, maxima_velocidad, acelerando, derrapando):
        if not self.motor_activo:
            return
            
        # --- VOLUMEN OBJETIVO ---
        volumen_ralenti = 0.007
        volumen_maximo_acel = 0.02 # Se mantiene bajito como pediste
        volumen_maximo_decel = 0.1 # Subimos un poco la desaceleración para que se note
        
        porcentaje_velocidad = min(1.0, abs(velocidad) / maxima_velocidad)
        volumen_dinamico_acel = volumen_ralenti + (porcentaje_velocidad * (volumen_maximo_acel - volumen_ralenti))
        volumen_dinamico_decel = volumen_ralenti + (porcentaje_velocidad * (volumen_maximo_decel - volumen_ralenti))
        
        target_vol_acel = 0.0
        target_vol_decel = 0.0

        if derrapando:
            # Al derrapar, dejamos el volumen muy bajito en lugar de apagarlo
            if acelerando:
                target_vol_acel = 0.01
            else:
                target_vol_decel = 0.01
        elif acelerando:
            target_vol_acel = volumen_dinamico_acel
        else:
            # Si no acelera pero se mueve, suena la desaceleración
            if porcentaje_velocidad > 0.05:
                target_vol_decel = volumen_dinamico_decel
            # Si está casi quieto, suena el ralentí (que es el de aceleración bajito)
            else:
                target_vol_acel = volumen_ralenti
        
        # --- INTERPOLACIÓN SUAVE (Cross-fade) ---
        factor_suavizado = 0.04 # Ajustado para una transición fluida sin cortarse
        
        self.vol_acel_actual += (target_vol_acel - self.vol_acel_actual) * factor_suavizado
        self.canal_aceleracion.set_volume(self.vol_acel_actual)
        
        self.vol_decel_actual += (target_vol_decel - self.vol_decel_actual) * factor_suavizado
        self.canal_desaceleracion.set_volume(self.vol_decel_actual)
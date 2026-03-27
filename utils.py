# -*- coding: utf-8 -*-
# utils.py
import os
import sys

def obtener_ruta(ruta_relativa):
    """ Obtiene la ruta absoluta al recurso, compatible con PyInstaller """
    try:
        ruta_base = sys._MEIPASS
    except Exception:
        ruta_base = os.path.abspath(".")
    return os.path.join(ruta_base, ruta_relativa)

def formato_tiempo(ms):
    if ms is None:
        return "--:--.---"
    minutos = int(ms // 60000)
    segundos = int((ms % 60000) // 1000)
    milisegundos = int(ms % 1000)
    return f"{minutos:02d}:{segundos:02d}.{milisegundos:03d}"

class GameExit(Exception):
    """Excepción personalizada para señalar una salida limpia del juego."""
    pass
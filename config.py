# -*- coding: utf-8 -*-
# config.py

# Pantalla y Cámara
ANCHO = 800
ALTO = 600
ZOOM_CAMARA = 2.0
ANCHO_VIRTUAL = int(ANCHO / ZOOM_CAMARA)
ALTO_VIRTUAL = int(ALTO / ZOOM_CAMARA)

# Colores en formato RGB
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)

# Opciones de Juego (Globales)
MODOS_CAMARA = ["CENITAL", "CHASING"]
DIFICULTADES_IA = ["80%", "90%", "100%"]
VALORES_DIFICULTAD = [5.6, 5.8, 6.0]

OPCIONES = {
    "modo_camara": 0, # Indice de MODOS_CAMARA
    "dificultad_ia": 2 # Indice de DIFICULTADES_IA
}

# Redes
# Esta será la URL que Render te dará después de desplegar tu servidor.
# Usamos 'wss' (WebSocket Secure) porque es el estándar para conexiones web.
# El path '/lobby' será un endpoint especial para obtener la lista de salas.
DEDICATED_SERVER_URI = "wss://bitracing-server.onrender.com" # ¡Cambia 'bitracing-server' por el nombre de tu app!

# Listas de recursos
CLASES_AUTOS = [
    {
        "nombre": "GT3",
        "autos": [
            {"nombre": "Porsche GT3", "archivo": "porsche_gt3.png"},
            {"nombre": "Ferrari GT3", "archivo": "ferrari_gt3.png"},
            {"nombre": "BMW GT3", "archivo": "bmw_gt3.png"},
            {"nombre": "Mercedes GT3", "archivo": "mercedes_gt3.png"},
            {"nombre": "Mustang GT3", "archivo": "mustang_gt3.png"}
        ]
    },
    {
        "nombre": "LMP1",
        "autos": [] # Lista vacía para indicar "Pronto..."
    },
    {
        "nombre": "Formula 1",
        "autos": []
    }
]
LISTA_PISTAS = [
    {"nombre": "Circuito Road", "archivo": "road.png", "mascara": "road_mask.png"},
    {"nombre": "PRONTO MAS..."}
]
"""
Configuración global de la aplicación Ving
"""

# Colores de la aplicación
COLORS = {
    "background": "#ecebe7",
    "primary": "#0c344e",
    "secondary": "#2a7078",
    "accent": "#577782",
    "danger": "#d4412d",
    "text_light": "#ecebe7",
    "text_dark": "#0c344e",
    "text_medium": "#577782"
}

# Tipos de dispositivos disponibles
DEVICE_TYPES = sorted([
    "Sensor_de_Movimiento_Universal",
    "Cerradura_Inteligente",
    "Detector_de_Humo",
    "Camara_por_Fotogramas",
    "Simulador_de_Presencia",
    "Boton_de_Panico",
    "Sensor_de_Movimiento_para_Entradas",
    "Alarma_Silenciosa",
    "Detector_de_Placas",
    "Detector_Laser"
])

# Configuración de la ventana principal
WINDOW_CONFIG = {
    "title": "Aplicación Ving (Demo)",
    "width": 900,
    "height": 700,
    "resizable": False
}

# Configuración del splash screen
SPLASH_CONFIG = {
    "width": 480,
    "height": 260,
    "duration": 3  # segundos
}

# Días de la semana
DAYS_OF_WEEK = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Horas del día (formato 24h)
HOURS_OF_DAY = list(range(24))

# 🎥 Sistema de Detección de Movimiento por Cámara v2.0

## 🆕 ¿Qué hay de nuevo?

### ✅ Correcciones Críticas

1. **🐛 FIX: Crash al reiniciar**
   - **Problema**: La app se caía por completo al detener y volver a iniciar
   - **Solución**: 
     - Implementado `threading.Event` para control robusto de threads
     - Manejo seguro de liberación de recursos de cámara
     - Timeout en `thread.join()` para evitar bloqueos infinitos
     - Limpieza completa del estado al detener

2. **🔒 FIX: Controles bloqueados durante ejecución**
   - **Problema**: Se podía modificar sensibilidad y resolución mientras corría (causaba comportamiento impredecible)
   - **Solución**:
     - Sliders se deshabilitan automáticamente al iniciar
     - Radiobuttons de resolución también se bloquean
     - Solo se puede configurar cuando está detenido
     - Indicador visual claro: "⚠️ Solo editable cuando está detenido"

3. **📸 NUEVO: Botón de captura manual**
   - **Feature**: Tomar foto independientemente de si se detectó movimiento
   - **Detalles**:
     - Botón morado "📸 Captura Manual"
     - No afecta el cooldown de capturas automáticas
     - Capturas manuales tienen prefijo `manual_` en el archivo
     - Se distinguen claramente en eventos y historial
     - Solo disponible cuando está activo (no pausado)

### 🎨 Mejoras de UX

- **Mejor feedback visual**: Estado del detector más claro (🟢/⏸️/⚫)
- **Control de cooldown mejorado**: Slider para configurar de 1-30 segundos
- **Eventos detallados**: Distingue entre capturas automáticas y manuales
- **Ventana modal**: La ventana de configuración es modal (bloquea la principal)

## 📦 Estructura de Archivos

```
sistema_camaras_v2/
│
├── detector_movimiento_v2.py          # ⭐ Core del sistema (nuevo)
│   └── Clase DetectorMovimiento mejorada
│
├── ventana_camara_fotogramas.py       # ⭐ Para integrar en tu app (nuevo)
│   └── Ventana de control standalone
│
├── app_tkinter_v2.py                  # 🧪 App de prueba standalone (nuevo)
│   └── Aplicación completa para testing
│
├── GUIA_INTEGRACION.md                # 📚 Guía paso a paso
│   └── Cómo integrar en tu app principal
│
└── README.md                          # 📖 Este archivo
```

## 🚀 Inicio Rápido

### Opción 1: Probar la App Standalone

```bash
# Instalar dependencias
pip install opencv-python pillow numpy

# Ejecutar app de prueba
python app_tkinter_v2.py
```

### Opción 2: Integrar en Tu App Principal

1. **Copia estos archivos a tu proyecto:**
   - `detector_movimiento_v2.py`
   - `ventana_camara_fotogramas.py`

2. **Importa el módulo:**
```python
from ventana_camara_fotogramas import VentanaCamaraFotogramas
```

3. **Abre la ventana cuando edites un dispositivo tipo "cámara":**
```python
def editar_dispositivo(self, dispositivo_id):
    if tipo_dispositivo == "camara_fotogramas":
        ventana = VentanaCamaraFotogramas(
            ventana_padre=self.root,
            dispositivo_id=dispositivo_id,
            nombre_dispositivo="Mi Cámara",
            callback_guardar=self.guardar_config
        )
```

4. **Lee la GUIA_INTEGRACION.md para más detalles**

## 🎯 Características Principales

### Sistema de Detección

- ✅ Detección de movimiento por diferencia de frames
- ✅ Sistema de estabilización (espera 5 frames antes de capturar)
- ✅ Selección automática del frame más nítido
- ✅ Cooldown configurable entre capturas (1-30 segundos)
- ✅ Compresión JPEG optimizada (calidad 50-100%)
- ✅ Múltiples resoluciones: SD, HD, Full HD

### Controles

- ▶️ **Iniciar/Detener**: Control principal del detector
- ⏸️ **Pausar/Reanudar**: Pausa la detección sin cerrar la cámara
- 📸 **Captura Manual**: Tomar foto en cualquier momento
- 🔧 **Configuración**: Sensibilidad, calidad, resolución, cooldown

### Estadísticas en Tiempo Real

- 📊 Movimientos detectados
- 📸 Capturas guardadas
- 🟢 Estado actual (Activo/Pausado/Detenido)
- ⏱️ Cooldown activo y tiempo restante
- 📝 Log de eventos en tiempo real

## 🔧 API del Detector

```python
from detector_movimiento_v2 import DetectorMovimiento

# Crear instancia
detector = DetectorMovimiento(
    carpeta_capturas="mis_capturas",
    carpeta_historial="mi_historial"
)

# Configurar (solo cuando está detenido)
detector.configurar_sensibilidad(3000)      # 500-10000
detector.configurar_compresion(
    calidad=80,                              # 50-100
    resolucion=(1920, 1080)                  # (width, height)
)
detector.configurar_cooldown(7)              # segundos

# Iniciar
if detector.iniciar(indice_camara=0):
    print("Detector iniciado")

# Captura manual
detector.capturar_manual()

# Pausar/Reanudar
detector.pausar()
detector.reanudar()

# Obtener información
stats = detector.obtener_estadisticas()
# Retorna: {
#     'movimientos_detectados': int,
#     'capturas_guardadas': int,
#     'estado': str,
#     'pausado': bool,
#     'cooldown_activo': bool,
#     'tiempo_restante_cooldown': float
# }

frame = detector.obtener_frame_actual()      # numpy array o None

evento = detector.obtener_evento()           # dict o None
# Tipos de eventos: 'captura', 'error', 'info'

# Detener limpiamente
detector.detener()
```

## 📁 Organización de Archivos

Cada dispositivo genera su propia carpeta:

```
tu_proyecto/
├── capturas_1/                    # Dispositivo ID 1
│   ├── 2024-03-15_10-30-45.jpg
│   ├── 2024-03-15_10-35-52.jpg
│   └── manual_2024-03-15_11-00-15.jpg
│
├── capturas_2/                    # Dispositivo ID 2
│   └── ...
│
├── historial_1/
│   └── historial_movimientos.txt  # Log de todas las capturas
│
└── historial_2/
    └── historial_movimientos.txt
```

### Formato del Historial

```
=== HISTORIAL DE MOVIMIENTOS ===
Creado: 2024-03-15 10:00:00

2024-03-15 10:30:45 - Movimiento detectado - 2024-03-15_10-30-45.jpg
2024-03-15 10:35:52 - Movimiento detectado - 2024-03-15_10-35-52.jpg
2024-03-15 11:00:15 - Captura manual - manual_2024-03-15_11-00-15.jpg
```

## 🎨 Interfaz de Usuario

### Panel de Control
- Botones grandes y claros con iconos
- Estados visuales (colores verde/naranja/rojo)
- Grid 2x2 para controles principales
- Botón de captura manual destacado

### Panel de Estadísticas
- Contadores grandes y legibles
- Actualización en tiempo real
- Indicador de cooldown activo

### Panel de Configuración
- Advertencia clara cuando está bloqueado
- Sliders para ajustes rápidos
- Radiobuttons para resolución predefinida

### Log de Eventos
- Scroll automático
- Timestamps en cada evento
- Iconos distintivos (📸/🔴/⚠️/ℹ️)
- Límite de 100 líneas (auto-limpieza)

## 🔐 Thread Safety

El sistema es **completamente thread-safe**:

- ✅ Uso de `threading.Lock()` para variables compartidas
- ✅ Cola thread-safe (`queue.Queue`) para eventos
- ✅ Métodos públicos protegidos con locks
- ✅ Copia defensiva de frames (`.copy()`)
- ✅ Event system para parada limpia

## 🐛 Manejo de Errores

El sistema captura y reporta errores:

- ❌ Cámara no disponible
- ❌ Error al guardar imagen
- ❌ Error al leer frame
- ❌ Configuración inválida durante ejecución

Todos los errores se reportan vía:
1. Cola de eventos (`obtener_evento()`)
2. Log de eventos en UI
3. Retorno False en métodos críticos

## 📊 Configuración Recomendada

### Para Alta Sensibilidad (Detectar todo)
```python
sensibilidad: 500-1500
cooldown: 2-3 segundos
```

### Para Uso Balanceado (Recomendado)
```python
sensibilidad: 2000-3000
cooldown: 5-7 segundos
calidad: 75-85
resolución: 1280x720
```

### Para Baja Sensibilidad (Solo movimientos grandes)
```python
sensibilidad: 5000-10000
cooldown: 10-15 segundos
```

## 💾 Integración con Base de Datos

Campos sugeridos para tu tabla:

```sql
CREATE TABLE dispositivos_camaras (
    id INTEGER PRIMARY KEY,
    nombre TEXT NOT NULL,
    tipo TEXT DEFAULT 'camara_fotogramas',
    
    -- Configuración
    indice_camara INTEGER DEFAULT 0,
    sensibilidad INTEGER DEFAULT 2500,
    calidad_jpeg INTEGER DEFAULT 75,
    resolucion_width INTEGER DEFAULT 1280,
    resolucion_height INTEGER DEFAULT 720,
    cooldown INTEGER DEFAULT 5,
    
    -- Estado
    activo BOOLEAN DEFAULT 0,
    
    -- Estadísticas
    movimientos_detectados INTEGER DEFAULT 0,
    capturas_guardadas INTEGER DEFAULT 0,
    
    -- Metadata
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultima_actualizacion TIMESTAMP
);
```

## 🔄 Ciclo de Vida

```
[Crear Dispositivo] 
    ↓
[Abrir Ventana de Control]
    ↓
[Configurar Parámetros] ← Solo cuando está detenido
    ↓
[Iniciar Detector] → [Capturando...] → [Pausar] → [Reanudar]
    ↓                      ↓                           ↑
[Capturas Automáticas] [Captura Manual] ←────────────┘
    ↓
[Detener Detector]
    ↓
[Guardar Configuración]
    ↓
[Cerrar Ventana]
```

## 📝 Notas de Migración (v1 → v2)

Si tienes código usando la versión anterior:

### Cambios en la API

```python
# ANTES (v1)
detector.configurar_sensibilidad(3000)  # Funcionaba en cualquier momento
detector.configurar_compresion(80)      # Funcionaba en cualquier momento

# AHORA (v2)
# Solo funciona cuando está detenido, retorna bool
if detector.configurar_sensibilidad(3000):
    print("Configurado")
else:
    print("No se puede configurar mientras está activo")
```

### Nuevo Método
```python
# NUEVO en v2
detector.capturar_manual()  # Tomar foto en cualquier momento
```

### Threading Mejorado
```python
# ANTES (v1)
detector.ejecutando = False  # Podía causar race conditions

# AHORA (v2)
detector.detener()  # Limpieza completa y segura
```

## 🤝 Contribución

Para reportar bugs o sugerir mejoras:
1. Describe el problema con detalle
2. Incluye pasos para reproducir
3. Adjunta logs si es posible

## 📄 Licencia

Este código es parte de tu proyecto principal.

## 🙏 Créditos

Desarrollado como módulo de cámaras de fotogramas para sistema de automatización del hogar.

---

**¿Necesitas ayuda?** Consulta la `GUIA_INTEGRACION.md` para instrucciones detalladas.

**¿Quieres probar rápido?** Ejecuta `python app_tkinter_v2.py`

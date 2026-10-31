# SensorLang — Compilador para ESP32 con Soporte WiFi, OTA y Estudio Web 3D

**SensorLang** es un lenguaje de programación específico de dominio (DSL) diseñado para simplificar la adquisición de datos de sensores y el control de actuadores en sistemas embebidos. Traduce el código fuente `.sl` a C++ nativo para el microcontrolador **ESP32**, incorporando conectividad WiFi autónoma, servidor web local, telemetría inalámbrica en tiempo real y actualización de firmware Over-The-Air (OTA).

---

## 📚 Documentación Técnica

La documentación completa del proyecto se encuentra organizada en el directorio [`docs/`](docs/):

- 📐 **[Guía de Armado en Protoboard (docs/guia_protoboard.md)](docs/guia_protoboard.md):** Mapa orificio por orificio para protoboards de 30 filas, conexionado de sensores de 4 pines (DHT11 y MQ), actuador LED y prevención de cortos en bucles de brownout.
- 🔌 **[Guía de Conexión y Flasheo del ESP32 (docs/guia_conexion_esp32.md)](docs/guia_conexion_esp32.md):** Procedimiento de primer flasheo USB, detección de puertos, modo Punto de Acceso (AP), cliente WiFi y subida OTA.
- 🏛️ **[Arquitectura del Compilador (docs/arquitectura.md)](docs/arquitectura.md):** Descripción interna del pipeline (Lexer, Parser, AST, Generador C++), servidor web y motor 3D en Three.js.

---

## ✨ Características Principales

1. **SensorLang Web Studio en Localhost (`http://localhost:5000`):**
   * Editor de código con numeración de líneas, atajos (`Ctrl+Enter` para compilar, `Tab` para 4 espacios) y guardado en caché.
   * **Divisores arrastrables (Splitters):** Redimensionamiento fluido de las columnas izquierda, derecha e inferior con memoria en `localStorage`.
   * **Visor 3D Three.js:** Protoboard 100% sólida (incluyendo base con textura de espuma adhesiva industrial), controles de órbita 360°, componentes realistas y selector de sensor (DHT11 / MQ).
   * **Telemetría analógica en vivo:** Gráfica temporal en tiempo real con selector de fuente (WiFi OTA o USB serie).
2. **Detección Automática de Placas ESP32:**
   * Reconocimiento de chips UART por hardware (Silicon Labs CP210x, WCH CH340, Espressif Native USB y FTDI) para conexión inmediata.
3. **Flujo Inalámbrico "Flashea una vez por USB, opera por WiFi":**
   * El ESP32 crea su propio Punto de Acceso (`SensorLang-ESP32` en `192.168.4.1`) o se conecta a la red de tu laboratorio.
   * Flasheo inalámbrico de firmware mediante HTTP multipart a `/update` sin reconectar cables.
4. **Mapeo de Compatibilidad de Pines:**
   * Soporte automático para alias analógicos (`A0`–`A7`) mapeados a los canales ADC internos del ESP32 (ej. `A1` $\rightarrow$ `GPIO 39 / VN`).

---

## 🚀 Inicio Rápido

### 1. Iniciar el Entorno Web en Localhost
```bash
python3 -m sensorlang
```
Este comando arranca el servidor HTTP local y abre automáticamente la interfaz en `http://localhost:5000`.

Opciones adicionales:
```bash
# Iniciar en un puerto específico
python3 -m sensorlang --port 8080

# Iniciar sin abrir el navegador automáticamente
python3 -m sensorlang --no-browser
```

### 2. Uso desde la Línea de Comandos (CLI)
```bash
# Solo compilar a C++ (genera salida_compilador/salida_compilador.ino)
python3 -m sensorlang ejemplos/prender_led.sl

# Compilar binario con arduino-cli
python3 -m sensorlang ejemplos/prender_led.sl -c

# Compilar y subir inalámbricamente por WiFi (OTA)
python3 -m sensorlang ejemplos/prender_led.sl --upload-wifi 192.168.4.1

# Compilar y subir por cable USB (autodetectando el puerto)
python3 -m sensorlang ejemplos/prender_led.sl --upload-usb

# Compilar y subir por cable USB a un puerto específico
python3 -m sensorlang ejemplos/prender_led.sl --upload-usb /dev/ttyUSB0
```

---

## 📝 Sintaxis de SensorLang

```sensorlang
// 1. Declaración de pines
pin led = 2;
pin sensor = A1;

// 2. Lectura analógica o digital
temp = leer_analogo(sensor);

// 3. Emisión de telemetría hacia el dashboard
mostrar(temp);

// 4. Estructura condicional
si (temp > 600) {
    encender(led);
    alerta("¡Límite de temperatura superado!");
} sino {
    apagar(led);
}

// 5. Retardo en milisegundos
esperar(400);
```

---

## 📁 Estructura del Proyecto

```text
sensorlang/
├── docs/                        # Documentación técnica y guías de hardware
│   ├── arquitectura.md          # Arquitectura del compilador y sistema web
│   ├── entrega2.md              # Versión Markdown del informe de entrega 2
│   ├── guia_conexion_esp32.md   # Guía de conexión, drivers y red WiFi
│   └── guia_protoboard.md       # Mapa orificio por orificio en protoboard
├── ejemplos/                    # Sketches de ejemplo en sintaxis SensorLang
│   ├── alerta_temperatura.sl
│   ├── parpadeo_wifi.sl
│   └── prender_led.sl
├── pruebas/                     # Casos de prueba del compilador
│   ├── validos/                 # Programas válidos de prueba
│   └── errores/                 # Casos de errores léxicos y sintácticos
├── sensorlang/                  # Paquete principal de Python
│   ├── __init__.py              # Exportaciones públicas de la API
│   ├── __main__.py              # Punto de entrada CLI con opciones --tokens, --arbol, --ast y --todo
│   ├── esp32_tools.py           # Herramientas de hardware, USB y arduino-cli
│   ├── generador.py             # Traducción del AST a C++ para ESP32
│   ├── lexer.py                 # Tokens, patrones regulares, comentarios y errores léxicos
│   ├── parser.py                # Parser recursivo, árbol sintáctico (NodoArbol), expresiones y AST
│   ├── visualizador_3d.py       # Visor de soporte de escritorio (Tkinter)
│   ├── web_server.py            # API /api/compilar (ahora devuelve tokens y árbol) y servidor local
│   └── web/                     # Frontend del Web Studio
├── tests/                       # Suite de pruebas unitarias e integración
│   ├── test_entrega2.py         # Pruebas de lexer, parser, árbol, AST y expresiones
│   ├── test_sensorlang.py
│   └── test_web_server.py
├── .gitignore                   # Exclusión de artefactos de compilación
└── README.md                    # Documentación general del repositorio
```

---

## 🧪 Pruebas Automatizadas y Ejecución

**Requisito:** Python 3.10 o superior (solo biblioteca estándar).

Para inspeccionar el flujo completo de un programa (Tokens, Árbol y AST):
```bash
python3 -m sensorlang pruebas/validos/control_invernadero.sl --todo
```

Para compilar un sketch a C++ para el ESP32:
```bash
python3 -m sensorlang ejemplos/alerta_temperatura.sl
```

Para ejecutar las pruebas específicas de la etapa de análisis (Lexer, Parser y AST):
```bash
python3 -m unittest tests.test_entrega2 -v
```

Para ejecutar la suite completa de pruebas unitarias y de integración del proyecto:
```bash
python3 -m unittest discover tests
```

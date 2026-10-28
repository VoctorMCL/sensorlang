# Arquitectura del Sistema SensorLang

Este documento describe la arquitectura de software del compilador **SensorLang**, la estructura de sus componentes internos, el flujo de procesamiento de código y la integración de hardware con microcontroladores ESP32.

---

## 1. Visión General de la Arquitectura

El ecosistema de SensorLang se compone de cuatro capas principales:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        INTERFAZ DE USUARIO                            │
│  - SensorLang Web Studio (HTML5 / Three.js / CSS Grid & Flex)          │
│  - Interfaz de Línea de Comandos (CLI via argparse)                    │
│  - Interfaz de Escritorio Clásica (Tkinter Legacy)                     │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                     SERVIDOR LOCAL (web_server.py)                     │
│  - HTTP Threading Server en localhost:5000                             │
│  - API REST endpoints (/api/compilar, /api/puertos, /api/telemetria)   │
│  - Gestor de archivos estáticos y librerías locales                    │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                  PIPELINE DEL COMPILADOR SENSORLANG                     │
│  1. Analizador Léxico (lexer.py): Tokens tipados con fila/columna      │
│  2. Analizador Sintáctico (parser.py): AST jerárquico recursivo        │
│  3. Generador C++ (generador.py): Sketch Arduino ESP32 optimizado     │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│               INTEGRACIÓN CON HARDWARE (esp32_tools.py)                │
│  - Compilación con arduino-cli (FQBN: esp32:esp32:esp32)               │
│  - Detección automática USB (Silicon Labs CP210x, CH340, Espressif)    │
│  - Flasheo inalámbrico WiFi (HTTP OTA multipart /update)              │
│  - Flasheo por cable serie USB (arduino-cli compile --upload)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Pipeline del Compilador

### 2.1. Analizador Léxico (`sensorlang/lexer.py`)
Convierte el flujo de caracteres del archivo `.sl` en una secuencia de objetos `Token`.
* **Características:**
  * Uso de expresiones regulares compiladas con grupos nombrados (`re.finditer`).
  * Soporte para comentarios de una línea (`//`, `#`) y bloques multilínea (`/* ... */`).
  * Reconocimiento de literales de cadena tanto con comillas dobles (`"..."`) como simples (`'...'`).
  * Registro de números de línea y columna para mensajes de error precisos.

### 2.2. Analizador Sintáctico (`sensorlang/parser.py`)
Implementa un analizador descendente recursivo (*Recursive Descent Parser*) que valida la gramática libre de contexto y construye un Árbol de Sintaxis Abstracta (AST).
* **Nodos del AST:**
  * `declaracion_pin`: Asignación de alias a pines (`pin led = 2;`, `pin sensor = A1;`).
  * `asignacion`: Asignación de variables (`temp = 25;`).
  * `lectura`: Invocación de lecturas analógicas o digitales (`valor = leer_analogo(sensor);`).
  * `mostrar`: Emisión de telemetría por el canal serie y buffer circular (`mostrar(valor);`).
  * `alerta`: Disparo de mensaje de advertencia (`alerta("Límite superado");`).
  * `accion`: Control digital de actuadores (`encender(pin);`, `apagar(pin);`).
  * `esperar`: Retardo temporal (`esperar(500);`).
  * `si`: Estructura de control condicional (`si (condicion) { ... } sino { ... }`).

### 2.3. Generador de Código C++ (`sensorlang/generador.py`)
Traduce el AST a un archivo `.ino` compatible con la biblioteca base de Arduino para ESP32:
* **Mapeo de pines:** Resuelve automáticamente identificadores analógicos como `A0`–`A7` asignándolos a sus canales ADC de ESP32 (`GPIO 36`, `GPIO 39`, etc.).
* **Servidor Web integrado:** Genera un servidor HTTP en el puerto 80 que expone:
  * `/`: Dashboard web autónomo para visualización de telemetría y subida de firmware.
  * `/telemetria`: Endpoint en texto plano con el buffer circular de logs.
  * `/update`: Receptor de imágenes de firmware para actualización OTA.
* **Manejo de red:** Configura el modo Punto de Acceso (AP) por defecto o se une como estación (STA) si se proveen credenciales.

---

## 3. Capa de Integración con Hardware (`sensorlang/esp32_tools.py`)

Esta capa aísla la comunicación con las utilidades externas del sistema operativo:
1. **Detección USB:** Escanea `serial.tools.list_ports` buscando coincidencias con los VIDs de fabricantes de convertidores USB-UART (Silicon Labs, WCH, Espressif, FTDI) y descarta puertos serie virtuales del chipset del sistema.
2. **Toolchain `arduino-cli`:** Orquesta la invocación del compilador de Arduino usando el FQBN oficial `esp32:esp32:esp32`.
3. **Flasheo OTA:** Construye una petición HTTP multipart `POST /update` que transmite el archivo `.bin` directamente a la memoria flash del ESP32 mediante sockets o `urllib.request`.

---

## 4. Servidor Web y Visualizador 3D (`sensorlang/web/`)

* **Servidor Local (`web_server.py`):**
  * Basado en `ThreadingHTTPServer` de la biblioteca estándar de Python.
  * No requiere frameworks externos pesados (como Flask o FastAPI), garantizando portabilidad instantánea.
* **Frontend (`index.html`, `style.css`, `app.js`):**
  * **Splitters arrastrables:** Tres divisores móviles con eventos de puntero y almacenamiento en `localStorage`.
  * **Motor 3D Three.js:**
    * Renderizado en WebGL mediante geometría tridimensional sólida (`THREE.BoxGeometry`).
    * Fondo sellado con textura de espuma adhesiva industrial y tira protectora roja (cero huecos desde cualquier perspectiva).
    * Modelos realistas con mallas procedurales: LED 5mm abombado, resistencia con bandas de código de color de 220 Ω, sensor seleccionable DHT11 / MQ y placa ESP32.
    * Mapeo de coordenadas con espejo horizontal: fila 30 a la izquierda y fila 1 a la derecha.

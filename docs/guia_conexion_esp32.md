# Guía de Conexión y Operación del ESP32 con SensorLang
## Configuración Inicial por USB, Red Inalámbrica y Flasheo OTA

Esta guía detalla el procedimiento para conectar, compilar y operar la placa ESP32 con SensorLang, cubriendo tanto la conexión inicial por cable USB como el flujo de trabajo permanente inalámbrico vía WiFi.

---

## 1. Filosofía de Operación: "Flasheo Inicial USB, Operación Inalámbrica"

1. **Flasheo Inicial (1 sola vez por USB):** Se programa el firmware base generado por SensorLang que incluye el soporte de red WiFi, servidor HTTP y el gestor de actualización Over-The-Air (OTA).
2. **Operación Inalámbrica Permanente (WiFi):** Una vez cargado el firmware base, el microcontrolador puede desconectarse del ordenador y alimentarse desde una fuente externa (cargador de 5V, batería LiPo o powerbank). Todo el envío de nuevo firmware y la telemetría en tiempo real se realizan vía WiFi.

---

## 2. Fase 1: Conexión Inicial por Cable USB

### Requisitos del Cable y Permisos de Sistema
* **Cable de Datos:** Utiliza un cable Micro-USB con líneas de datos conectadas (D+ y D-). Los cables diseñados exclusivamente para carga no transmiten señales y no serán detectados en el bus del sistema.
* **Permisos de Puerto Serie en Linux:**
  En distribuciones Linux (Ubuntu, Debian, Fedora, Arch), los puertos serie `/dev/ttyUSB*` o `/dev/ttyACM*` requieren membresía en el grupo `dialout` (o `uucp`):
  ```bash
  sudo usermod -a -G dialout $USER
  ```
  *(Cierra y vuelve a iniciar tu sesión de usuario para que la regla tome efecto).*

### Detección Automática de Puertos
SensorLang inspecciona el bus USB y reconoce automáticamente los chips convertidores USB-Serial más habituales mediante su Vendor ID (VID):
* **Silicon Labs CP2102 / CP2104** (VID: `10C4`)
* **WCH CH340 / CH341** (VID: `1A86`)
* **Espressif Native USB** (ESP32-S2/S3/C3, VID: `303A`)
* **FTDI FT232** (VID: `0403`)

El IDE web muestra el estado de detección mediante el indicador de hardware superior:
`● ESP32 en /dev/ttyUSB0`

### Maniobra del Botón "BOOT" (Modo Programación)
Si al iniciar la subida por cable la consola de `arduino-cli` se detiene en:
```text
Connecting........_____.....
```
Mantén presionado el pulsador marcado como **BOOT** (o **IO0**) en la placa durante 2 segundos hasta que comience la escritura en la memoria flash:
```text
Writing at 0x00010000... (100 %)
```

---

## 3. Fase 2: Configuración de Red WiFi

El código C++ generado por SensorLang permite operar en dos modalidades:

### Modo A: Punto de Acceso Autónomo (AP por Defecto — Recomendado)
El ESP32 crea su propia red inalámbrica independiente, permitiendo trabajar en laboratorio o campo sin depender de un router externo:
* **Nombre de red (SSID):** `SensorLang-ESP32`
* **Contraseña:** `12345678`
* **Dirección IP fija:** `192.168.4.1`

Para conectarte:
1. Desde la computadora, abre el selector de redes WiFi.
2. Selecciona la red `SensorLang-ESP32` e ingresa la contraseña `12345678`.
3. El ESP32 responderá directamente en la IP `192.168.4.1`.

### Modo B: Conexión a Red Existente (Modo Estación / STA)
Si deseas que el ESP32 se integre a tu red local existente:
1. En el panel izquierdo del IDE web, ingresa el **SSID** y la **Clave** de tu red WiFi.
2. Al compilar y flashear, el ESP32 solicitará una dirección IP al servidor DHCP de tu router.
3. La IP asignada se notificará por monitor serie y en la consola del servidor local.

---

## 4. Fase 3: Compilación y Flasheo Inalámbrico (OTA)

Con la computadora conectada a la red WiFi del ESP32:

### Desde el IDE Web (`http://localhost:5000`):
1. Verifica que la casilla de IP indique `192.168.4.1` (o la IP asignada en tu red).
2. Haz clic en el botón **Flash WiFi (OTA)** en la barra de herramientas.
3. El servidor compila el código en segundo plano con `arduino-cli` y transmite el binario compilado mediante una petición HTTP POST multipart al endpoint `/update` del ESP32.
4. El microcontrolador escribe la nueva imagen en la partición OTA, valida la firma y se reinicia en menos de 4 segundos.

### Desde la Línea de Comandos (CLI):
```bash
python3 -m sensorlang ejemplos/alerta_temperatura.sl --upload-wifi 192.168.4.1
```

---

## 5. Fase 4: Monitoreo y Telemetría en Vivo

El código generado incluye un buffer circular en RAM para registrar las lecturas producidas por `mostrar(...)` y los mensajes de `alerta(...)`.

1. En el IDE web, abre la pestaña **Telemetría**.
2. Selecciona la fuente de datos (**WiFi** o **USB Serial**).
3. Haz clic en **Iniciar Monitoreo**.
4. La gráfica analógica trazará en tiempo real las muestras del conversor analógico-digital (ADC) y actualizará el estado lógico del sistema.

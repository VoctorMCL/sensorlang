"""
Módulo de Herramientas de Hardware y Compilación ESP32 para SensorLang.

Contiene funciones utilitarias para:
- Detección automática de puertos serie USB de microcontroladores ESP32.
- Compilación de código SensorLang a C++ y verificación con arduino-cli.
- Flasheo inalámbrico de firmware mediante WiFi (OTA HTTP /update).
- Flasheo directo por cable USB.
"""

import os
import re
import sys
import uuid
import subprocess
import urllib.request
from typing import Optional, List, Tuple, Dict, Any

from .lexer import lexer
from .parser import parsear
from .generador import generar_cpp

# Detección opcional de pyserial para conexión USB
try:
    import serial
    import serial.tools.list_ports
    SERIAL_DISPONIBLE = True
except ImportError:
    SERIAL_DISPONIBLE = False

FQBN_ESP32 = "esp32:esp32:esp32"

# VIDs de fabricantes comunes de adaptadores USB-Serie en placas ESP32
ESP32_VIDS: Dict[int, str] = {
    0x10C4: "Silicon Labs CP210x (ESP32)",
    0x1A86: "WCH CH340/CH341 (ESP32)",
    0x303A: "Espressif Native USB (ESP32)",
    0x0403: "FTDI FT232 (ESP32)",
}


def detectar_info_puertos_usb() -> List[Tuple[str, bool, str]]:
    """
    Escanea los puertos serie del sistema.
    Retorna una lista de tuplas: (dispositivo, es_esp32_probable, descripcion_detallada).
    Descarta puertos serie virtuales del chipset (/dev/ttyS*) y prioriza placas ESP32.
    """
    puertos: List[Tuple[str, bool, str]] = []
    if SERIAL_DISPONIBLE:
        try:
            for p in serial.tools.list_ports.comports():
                # Descartar puertos internos virtuales (/dev/ttyS0, etc.)
                if re.match(r'^/dev/ttyS\d+$', p.device):
                    continue

                es_esp32 = False
                desc = p.description or ""

                if p.vid in ESP32_VIDS:
                    es_esp32 = True
                    desc = f"{ESP32_VIDS[p.vid]} [{p.device}]"
                elif any(kw in desc.lower() for kw in ["esp32", "cp210", "ch340", "ch341", "uart", "usb to uart", "usb serial"]):
                    es_esp32 = True
                    desc = f"{desc} [{p.device}]"
                else:
                    desc = f"{desc} [{p.device}]" if desc else p.device

                puertos.append((p.device, es_esp32, desc))
        except Exception:
            pass

    # Si pyserial no arrojó dispositivos o no está instalado, inspeccionar rutas de Linux
    if not puertos:
        for dev in ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0", "/dev/ttyACM1"]:
            if os.path.exists(dev):
                puertos.append((dev, True, f"Puerto USB [{dev}]"))

    # Ordenar priorizando los puertos identificados como ESP32
    puertos.sort(key=lambda x: not x[1])
    return puertos


def detectar_puerto_esp32_automatico() -> Optional[str]:
    """Retorna el primer puerto de ESP32 detectado en el bus, o None si no hay placas."""
    puertos = detectar_info_puertos_usb()
    if puertos:
        return puertos[0][0]
    return None


def listar_puertos_usb() -> List[str]:
    """Retorna la lista de identificadores de puertos serie disponibles (ej. ['/dev/ttyUSB0'])."""
    return [p[0] for p in detectar_info_puertos_usb()]


def compilar_sensorlang_a_cpp(codigo_sl: str, wifi_ssid: str = "", wifi_pass: str = "") -> Tuple[str, Any]:
    """
    Compila el código SensorLang y retorna el código C++ generado para ESP32 y el AST.
    Lanza LexerError o ParserError si existen fallas de sintaxis.
    """
    tokens = list(lexer(codigo_sl))
    ast = parsear(tokens)
    cpp = generar_cpp(ast, wifi_ssid=wifi_ssid, wifi_pass=wifi_pass)
    return cpp, ast


def compilar_con_arduino_cli(ruta_sketch_dir: str, ruta_output_bin: Optional[str] = None) -> Tuple[bool, str]:
    """
    Invoca arduino-cli para compilar el sketch C++ (.ino) generando el binario ejecutable para ESP32.
    """
    comando = ["arduino-cli", "compile", "--fqbn", FQBN_ESP32]
    if ruta_output_bin:
        comando.extend(["--output-dir", ruta_output_bin])
    comando.append(ruta_sketch_dir)

    try:
        res = subprocess.run(comando, check=True, text=True, capture_output=True)
        salida = res.stdout + ("\n" + res.stderr if res.stderr else "")
        return True, salida
    except subprocess.CalledProcessError as e:
        salida = (e.stdout or "") + "\n" + (e.stderr or str(e))
        return False, salida
    except FileNotFoundError:
        return False, "Error: 'arduino-cli' no se encuentra instalado en el sistema o no está en el PATH."


def subir_firmware_wifi(ip_esp32: str, ruta_binario: str, timeout: int = 35) -> Tuple[bool, str]:
    """
    Envía el archivo binario (.bin) al servidor web del ESP32 mediante HTTP POST multipart a /update (OTA).
    """
    ip = ip_esp32.strip()
    if ip.startswith("http://"):
        ip = ip[7:]
    ip = ip.rstrip("/")
    url = f"http://{ip}/update"
    boundary = f"----SensorLangBoundary{uuid.uuid4().hex}"

    try:
        with open(ruta_binario, 'rb') as f:
            contenido_bin = f.read()
    except Exception as e:
        return False, f"No se pudo leer el archivo binario: {e}"

    cabecera = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="update"; filename="firmware.bin"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode('utf-8')
    pie = f"\r\n--{boundary}--\r\n".encode('utf-8')
    cuerpo = cabecera + contenido_bin + pie

    req = urllib.request.Request(
        url,
        data=cuerpo,
        headers={
            'Content-Type': f'multipart/form-data; boundary={boundary}',
            'Content-Length': str(len(cuerpo)),
            'Connection': 'close'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            respuesta = resp.read().decode('utf-8', errors='ignore')
            return True, respuesta
    except Exception as e:
        return False, f"Fallo al conectar con el ESP32 en {url}: {e}"


def subir_firmware_usb(puerto: str, ruta_sketch_dir: str) -> Tuple[bool, str]:
    """
    Sube el sketch C++ directamente por el cable USB serie usando arduino-cli.
    """
    comando = [
        "arduino-cli", "compile", "--upload",
        "--fqbn", FQBN_ESP32,
        "--port", puerto,
        ruta_sketch_dir
    ]
    try:
        res = subprocess.run(comando, check=True, text=True, capture_output=True)
        salida = res.stdout + ("\n" + res.stderr if res.stderr else "")
        return True, salida
    except subprocess.CalledProcessError as e:
        salida = (e.stdout or "") + "\n" + (e.stderr or str(e))
        return False, salida
    except FileNotFoundError:
        return False, "Error: 'arduino-cli' no se encuentra instalado en el sistema."

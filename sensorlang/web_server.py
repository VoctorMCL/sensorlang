"""
Servidor Web Local para SensorLang (ESP32 Web Studio).

Proporciona una interfaz web completa en localhost con:
- API REST para compilación SensorLang -> C++ con validación mediante arduino-cli.
- Detección automática y gestión de puertos serie USB para ESP32.
- Flasheo inalámbrico mediante WiFi (OTA HTTP /update) y flasheo por cable USB.
- Flujo de telemetría en vivo vía WiFi y monitor serie USB.
- Servicio de archivos estáticos (HTML, CSS, JS, Three.js y OrbitControls).
"""

import os
import sys
import json
import time
import socket
import urllib.request
import urllib.parse
import threading
import mimetypes
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, List

from .lexer import LexerError
from .parser import ParserError
from .esp32_tools import (
    FQBN_ESP32,
    detectar_info_puertos_usb,
    detectar_puerto_esp32_automatico,
    compilar_sensorlang_a_cpp,
    compilar_con_arduino_cli,
    subir_firmware_wifi,
    subir_firmware_usb,
    SERIAL_DISPONIBLE
)

try:
    import serial
except ImportError:
    serial = None

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EJEMPLOS_DIR = os.path.join(BASE_DIR, "ejemplos")
SALIDA_DIR = os.path.join(BASE_DIR, "salida_compilador")

# Manejo de conexión serie activa para telemetría USB
_serial_activo: Optional[Any] = None
_serial_lock = threading.Lock()
_serial_buffer: List[str] = []


def _leer_serial_en_segundo_plano(puerto: str, baudrate: int = 115200):
    global _serial_activo, _serial_buffer
    with _serial_lock:
        if _serial_activo and _serial_activo.is_open:
            try:
                _serial_activo.close()
            except Exception:
                pass
            _serial_activo = None

        if not serial:
            return

        try:
            _serial_activo = serial.Serial(puerto, baudrate=baudrate, timeout=1.0)
        except Exception:
            _serial_activo = None
            return

    while True:
        with _serial_lock:
            if not _serial_activo or not _serial_activo.is_open or _serial_activo.port != puerto:
                break
            try:
                linea = _serial_activo.readline().decode('utf-8', errors='ignore').strip()
                if linea:
                    _serial_buffer.append(linea)
                    if len(_serial_buffer) > 100:
                        _serial_buffer.pop(0)
            except Exception:
                break
        time.sleep(0.05)


class SensorLangWebHandler(BaseHTTPRequestHandler):
    """Manejador HTTP para la API REST y los archivos estáticos del Web IDE."""

    server_version = "SensorLangWeb/2.0"

    def _responder_json(self, data: Dict[str, Any], status: int = 200):
        cuerpo = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _responder_error(self, mensaje: str, status: int = 400):
        self._responder_json({"ok": False, "error": mensaje}, status=status)

    def _servir_archivo(self, ruta_completa: str):
        if not os.path.exists(ruta_completa) or os.path.isdir(ruta_completa):
            self.send_error(404, "Recurso no encontrado")
            return

        tipo, _ = mimetypes.guess_type(ruta_completa)
        if ruta_completa.endswith('.js'):
            tipo = 'application/javascript; charset=utf-8'
        elif ruta_completa.endswith('.css'):
            tipo = 'text/css; charset=utf-8'
        elif ruta_completa.endswith('.html'):
            tipo = 'text/html; charset=utf-8'
        elif not tipo:
            tipo = 'application/octet-stream'

        try:
            tamano = os.path.getsize(ruta_completa)
            with open(ruta_completa, 'rb') as f:
                contenido = f.read()

            self.send_response(200)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(tamano))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(contenido)
        except Exception as e:
            self.send_error(500, f"Error al leer el archivo: {e}")

    def do_GET(self):
        global _serial_activo, _serial_buffer
        url_parsed = urllib.parse.urlparse(self.path)
        ruta = url_parsed.path
        query = urllib.parse.parse_qs(url_parsed.query)

        # 1. API: Estado del entorno de desarrollo
        if ruta == "/api/status":
            self._responder_json({
                "ok": True,
                "version": "2.0.0",
                "fqbn": FQBN_ESP32,
                "serial_disponible": SERIAL_DISPONIBLE,
                "plataforma": sys.platform
            })
            return

        # 2. API: Puertos serie USB disponibles
        if ruta == "/api/puertos":
            puertos = []
            for dev, es_esp, desc in detectar_info_puertos_usb():
                puertos.append({
                    "device": dev,
                    "es_esp32": es_esp,
                    "descripcion": desc
                })
            puerto_auto = detectar_puerto_esp32_automatico()
            self._responder_json({
                "ok": True,
                "puertos": puertos,
                "puerto_recomendado": puerto_auto
            })
            return

        # 3. API: Ejemplos de código .sl precargados
        if ruta == "/api/ejemplos":
            ejemplos = []
            if os.path.exists(EJEMPLOS_DIR):
                for arch in sorted(os.listdir(EJEMPLOS_DIR)):
                    if arch.endswith('.sl'):
                        ruta_ex = os.path.join(EJEMPLOS_DIR, arch)
                        try:
                            with open(ruta_ex, 'r', encoding='utf-8') as f:
                                cod = f.read()
                            titulo = arch.replace('.sl', '').replace('_', ' ').capitalize()
                            ejemplos.append({
                                "archivo": arch,
                                "titulo": titulo,
                                "codigo": cod
                            })
                        except Exception:
                            pass
            self._responder_json({"ok": True, "ejemplos": ejemplos})
            return

        # 4. API: Telemetría WiFi / USB
        if ruta == "/api/telemetria":
            origen = query.get("origen", ["wifi"])[0]
            ip = query.get("ip", ["192.168.4.1"])[0].strip()

            if origen == "wifi":
                url_esp32 = f"http://{ip}/telemetria"
                try:
                    req = urllib.request.Request(url_esp32, headers={'User-Agent': 'SensorLangWeb/2.0'})
                    with urllib.request.urlopen(req, timeout=1.8) as resp:
                        texto = resp.read().decode('utf-8', errors='ignore')
                        lineas = [ln.strip() for ln in texto.strip().split('\n') if ln.strip()]

                        valor_sensor = None
                        for ln in reversed(lineas):
                            if "[Lectura Sensor]:" in ln:
                                part = ln.split(":", 1)[1].strip()
                                try:
                                    valor_sensor = int(part)
                                    break
                                except ValueError:
                                    pass

                        self._responder_json({
                            "ok": True,
                            "lineas": lineas,
                            "datos": {
                                "valor": valor_sensor,
                                "adc": valor_sensor,
                                "estado": "NORMAL" if (valor_sensor is None or valor_sensor < 600) else "ALERTA"
                            }
                        })
                        return
                except Exception as e:
                    self._responder_json({
                        "ok": False,
                        "error": f"Sin conexión WiFi con {ip}: {e}",
                        "datos": None
                    })
                    return
            else:
                puerto = query.get("puerto", [""])[0]
                lineas_disponibles = list(_serial_buffer)
                valor_sensor = None
                for ln in reversed(lineas_disponibles):
                    if "[Lectura Sensor]:" in ln:
                        part = ln.split(":", 1)[1].strip()
                        try:
                            valor_sensor = int(part)
                            break
                        except ValueError:
                            pass

                self._responder_json({
                    "ok": True,
                    "lineas": lineas_disponibles,
                    "datos": {
                        "valor": valor_sensor,
                        "adc": valor_sensor,
                        "estado": "NORMAL" if (valor_sensor is None or valor_sensor < 600) else "ALERTA"
                    }
                })
                return

        # 5. API: Monitor de stream serie USB
        if ruta == "/api/serial-stream":
            puerto = query.get("puerto", [""])[0]
            if not puerto:
                puerto = detectar_puerto_esp32_automatico() or ""

            with _serial_lock:
                if not _serial_activo or not _serial_activo.is_open or _serial_activo.port != puerto:
                    threading.Thread(target=_leer_serial_en_segundo_plano, args=(puerto,), daemon=True).start()

                lineas = list(_serial_buffer)
                _serial_buffer.clear()

            self._responder_json({"ok": True, "lineas": lineas})
            return

        # 6. Servir archivos estáticos del IDE Web (HTML, CSS, JS, etc.)
        if ruta == "/" or ruta == "":
            ruta = "/index.html"

        ruta_archivo = os.path.join(WEB_DIR, ruta.lstrip("/"))
        if os.path.exists(ruta_archivo) and os.path.isfile(ruta_archivo):
            self._servir_archivo(ruta_archivo)
        else:
            self.send_error(404, f"Archivo no encontrado: {ruta}")

    def do_POST(self):
        longitud = int(self.headers.get("Content-Length", 0))
        cuerpo_bytes = self.rfile.read(longitud) if longitud > 0 else b"{}"

        try:
            req_data = json.loads(cuerpo_bytes.decode('utf-8'))
        except Exception:
            self._responder_error("El cuerpo de la petición no es un JSON válido.")
            return

        # 1. API: Compilar código SensorLang
        if self.path == "/api/compilar":
            codigo_sl = req_data.get("codigo", "")
            wifi_ssid = req_data.get("wifi_ssid", "")
            wifi_pass = req_data.get("wifi_pass", "")
            verificar_arduino = req_data.get("verificar_arduino", False)

            if not codigo_sl.strip():
                self._responder_error("El código fuente está vacío.")
                return

            try:
                cpp_generado, ast = compilar_sensorlang_a_cpp(codigo_sl, wifi_ssid=wifi_ssid, wifi_pass=wifi_pass)
            except (LexerError, ParserError) as e:
                self._responder_error(str(e))
                return
            except Exception as e:
                self._responder_error(f"Fallo interno en compilador: {e}")
                return

            os.makedirs(SALIDA_DIR, exist_ok=True)
            ruta_ino = os.path.join(SALIDA_DIR, "salida_compilador.ino")
            try:
                with open(ruta_ino, "w", encoding="utf-8") as f:
                    f.write(cpp_generado)
            except Exception as e:
                self._responder_error(f"No se pudo escribir el sketch .ino: {e}")
                return

            logs_arduino = None
            if verificar_arduino:
                ok_cli, logs_cli = compilar_con_arduino_cli(SALIDA_DIR)
                logs_arduino = logs_cli
                if not ok_cli:
                    self._responder_json({
                        "ok": False,
                        "error": "Fallo al verificar el código con arduino-cli.",
                        "logs_arduino": logs_cli,
                        "cpp_codigo": cpp_generado
                    }, status=422)
                    return

            self._responder_json({
                "ok": True,
                "cpp_codigo": cpp_generado,
                "ast": ast,
                "logs_arduino": logs_arduino
            })
            return

        # 2. API: Flasheo Inalámbrico por WiFi (OTA)
        if self.path == "/api/flashear-wifi":
            codigo_sl = req_data.get("codigo", "")
            ip_esp32 = req_data.get("ip", "192.168.4.1").strip()
            wifi_ssid = req_data.get("wifi_ssid", "")
            wifi_pass = req_data.get("wifi_pass", "")

            if not codigo_sl.strip():
                self._responder_error("El código fuente está vacío.")
                return

            try:
                cpp_generado, _ = compilar_sensorlang_a_cpp(codigo_sl, wifi_ssid=wifi_ssid, wifi_pass=wifi_pass)
            except Exception as e:
                self._responder_error(f"Error de sintaxis: {e}")
                return

            os.makedirs(SALIDA_DIR, exist_ok=True)
            ruta_ino = os.path.join(SALIDA_DIR, "salida_compilador.ino")
            with open(ruta_ino, "w", encoding="utf-8") as f:
                f.write(cpp_generado)

            ok_cli, logs_cli = compilar_con_arduino_cli(SALIDA_DIR)
            if not ok_cli:
                self._responder_json({
                    "ok": False,
                    "error": "Error al compilar el binario ESP32.",
                    "logs": logs_cli
                }, status=422)
                return

            # Localizar el archivo binario generado
            ruta_bin = os.path.join(SALIDA_DIR, "build", "esp32.esp32.esp32", "salida_compilador.ino.bin")
            if not os.path.exists(ruta_bin):
                ruta_bin = os.path.join(SALIDA_DIR, "build", "salida_compilador.ino.bin")
            if not os.path.exists(ruta_bin):
                for root_dir, _, files in os.walk(SALIDA_DIR):
                    for file in files:
                        if file.endswith(".bin") and not file.endswith(".partitions.bin") and not file.endswith(".bootloader.bin"):
                            ruta_bin = os.path.join(root_dir, file)
                            break

            if not os.path.exists(ruta_bin):
                self._responder_error("No se encontró el archivo binario .bin tras la compilación.")
                return

            ok_ota, logs_ota = subir_firmware_wifi(ip_esp32, ruta_bin)
            if ok_ota:
                self._responder_json({"ok": True, "logs": logs_ota})
            else:
                self._responder_json({"ok": False, "error": logs_ota}, status=502)
            return

        # 3. API: Flasheo por Cable USB Serie
        if self.path == "/api/flashear-usb":
            codigo_sl = req_data.get("codigo", "")
            puerto = req_data.get("puerto", "").strip()
            wifi_ssid = req_data.get("wifi_ssid", "")
            wifi_pass = req_data.get("wifi_pass", "")

            if not codigo_sl.strip():
                self._responder_error("El código fuente está vacío.")
                return

            if not puerto:
                puerto = detectar_puerto_esp32_automatico()
                if not puerto:
                    self._responder_error("No se detectó automáticamente ningún puerto USB con ESP32.")
                    return

            try:
                cpp_generado, _ = compilar_sensorlang_a_cpp(codigo_sl, wifi_ssid=wifi_ssid, wifi_pass=wifi_pass)
            except Exception as e:
                self._responder_error(f"Error de sintaxis: {e}")
                return

            os.makedirs(SALIDA_DIR, exist_ok=True)
            ruta_ino = os.path.join(SALIDA_DIR, "salida_compilador.ino")
            with open(ruta_ino, "w", encoding="utf-8") as f:
                f.write(cpp_generado)

            ok_usb, logs_usb = subir_firmware_usb(puerto, SALIDA_DIR)
            if ok_usb:
                self._responder_json({"ok": True, "logs": logs_usb, "puerto": puerto})
            else:
                self._responder_json({"ok": False, "error": logs_usb, "puerto": puerto}, status=502)
            return

        self.send_error(404, "Endpoint de API no encontrado")


def encontrar_puerto_libre(puerto_inicial: int = 5000) -> int:
    """Busca el primer puerto TCP disponible a partir de puerto_inicial."""
    puerto = puerto_inicial
    while puerto < 65535:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(('127.0.0.1', puerto))
            s.close()
            return puerto
        except OSError:
            s.close()
            puerto += 1
    return puerto_inicial


def iniciar_servidor_web(puerto: int = 5000, abrir_navegador: bool = True):
    """Inicializa el servidor HTTP local y opcionalmente abre el navegador."""
    puerto_real = encontrar_puerto_libre(puerto)
    servidor = ThreadingHTTPServer(('127.0.0.1', puerto_real), SensorLangWebHandler)
    url = f"http://localhost:{puerto_real}"

    print("\n" + "═" * 72)
    print("  ⚡ SensorLang Studio — Compilador & IDE ESP32")
    print(f"  🌐 Servidor local activo en: {url}")
    print("  📡 Conexión inalámbrica OTA: http://192.168.4.1/update")
    print("  🧊 Modelo 3D y Guía de Protoboard integrados")
    print("═" * 72 + "\n")

    if abrir_navegador:
        try:
            import webbrowser
            threading.Timer(0.6, lambda: webbrowser.open(url)).start()
        except Exception:
            pass

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor web de SensorLang...")
        servidor.server_close()

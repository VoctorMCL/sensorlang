"""
SensorLang CLI y Lanzador Principal para ESP32.

Punto de entrada de línea de comandos (CLI) y servidor web local.
Soporta:
- Modo por defecto: Web Studio en localhost con Three.js, editor interactivo y flasheo.
- Modo terminal: Compilación directa a C++, arduino-cli, subida USB y subida WiFi OTA.
- Modo escritorio clásico: Interfaz gráfica Tkinter (--tk).
"""

import os
import sys
import time
import argparse
import threading
import urllib.request
from typing import Optional, List, Tuple, Dict, Any

from .lexer import LexerError
from .parser import ParserError
from .esp32_tools import (
    FQBN_ESP32,
    ESP32_VIDS,
    SERIAL_DISPONIBLE,
    detectar_info_puertos_usb,
    detectar_puerto_esp32_automatico,
    listar_puertos_usb,
    compilar_sensorlang_a_cpp,
    compilar_con_arduino_cli,
    subir_firmware_wifi,
    subir_firmware_usb,
)

try:
    import serial
except ImportError:
    serial = None


# =========================================================================
# Interfaz Gráfica Tkinter (Modo Escritorio Clásico Legacy)
# =========================================================================
class SensorLangIDE:
    """Entorno de escritorio clásico en Tkinter para SensorLang."""

    def __init__(self, root):
        self.root = root
        self.root.title("SensorLang IDE — ESP32 Desktop Edition")
        self.root.geometry("1000x780")
        self.root.minsize(820, 620)

        self.wifi_monitor_activo = False
        self.wifi_thread = None
        self.serial_activo = False
        self.serial_thread = None
        self.conexion_serial = None
        self.puertos_map: Dict[str, str] = {}

        self.crear_widgets()
        self.cargar_ejemplo("prender_led.sl")
        self._iniciar_hilo_deteccion_automatica()

    def crear_widgets(self):
        import tkinter as tk
        from tkinter import ttk, scrolledtext

        top_frame = tk.LabelFrame(self.root, text=" Configuración de Conexión ESP32 ", font=("Arial", 9, "bold"), padx=10, pady=8)
        top_frame.pack(fill=tk.X, padx=10, pady=6)

        row1 = tk.Frame(top_frame)
        row1.pack(fill=tk.X, pady=2)

        tk.Label(row1, text="IP ESP32:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        self.entry_ip = tk.Entry(row1, width=16, font=("Arial", 9))
        self.entry_ip.insert(0, "192.168.4.1")
        self.entry_ip.pack(side=tk.LEFT, padx=5)

        tk.Label(row1, text="WiFi SSID:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(15, 2))
        self.entry_ssid = tk.Entry(row1, width=14, font=("Arial", 9))
        self.entry_ssid.pack(side=tk.LEFT, padx=3)

        tk.Label(row1, text="Clave:", font=("Arial", 9)).pack(side=tk.LEFT, padx=(6, 2))
        self.entry_pass = tk.Entry(row1, width=12, show="*", font=("Arial", 9))
        self.entry_pass.pack(side=tk.LEFT, padx=3)

        row2 = tk.Frame(top_frame)
        row2.pack(fill=tk.X, pady=(6, 2))

        tk.Label(row2, text="Puerto USB:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=3)
        self.combo_puertos = ttk.Combobox(row2, width=34, font=("Arial", 9))
        self.combo_puertos.pack(side=tk.LEFT, padx=5)

        btn_refrescar = tk.Button(row2, text="Actualizar", font=("Arial", 8), command=lambda: self.actualizar_lista_puertos(silencioso=False))
        btn_refrescar.pack(side=tk.LEFT, padx=4)

        self.lbl_estado_puerto = tk.Label(row2, text="", font=("Arial", 9, "bold"))
        self.lbl_estado_puerto.pack(side=tk.LEFT, padx=8)
        self.actualizar_lista_puertos(silencioso=True)

        editor_frame = tk.Frame(self.root)
        editor_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=4)

        header_editor = tk.Frame(editor_frame)
        header_editor.pack(fill=tk.X, pady=2)
        tk.Label(header_editor, text="Código SensorLang (.sl):", font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        btn_3d = tk.Button(header_editor, text="Modelo 3D Protoboard", font=("Arial", 8, "bold"), bg="#0284c7", fg="white", padx=8, pady=2, command=self.abrir_modelo_3d)
        btn_3d.pack(side=tk.RIGHT, padx=4)

        self.txt_codigo = scrolledtext.ScrolledText(editor_frame, wrap=tk.NONE, font=("Consolas", 11), undo=True)
        self.txt_codigo.pack(fill=tk.BOTH, expand=True, pady=4)

        bottom_actions = tk.Frame(self.root, padx=10, pady=6)
        bottom_actions.pack(fill=tk.X)

        btn_compilar = tk.Button(bottom_actions, text="Compilar C++", font=("Arial", 9, "bold"), bg="#2563eb", fg="white", padx=10, pady=4, command=self.compilar)
        btn_compilar.pack(side=tk.LEFT, padx=4)

        btn_flash_wifi = tk.Button(bottom_actions, text="Flash WiFi (OTA)", font=("Arial", 9, "bold"), bg="#059669", fg="white", padx=10, pady=4, command=self.flashear_wifi)
        btn_flash_wifi.pack(side=tk.LEFT, padx=4)

        btn_flash_usb = tk.Button(bottom_actions, text="Flash USB", font=("Arial", 9, "bold"), bg="#475569", fg="white", padx=10, pady=4, command=self.flashear_usb)
        btn_flash_usb.pack(side=tk.LEFT, padx=4)

        console_frame = tk.LabelFrame(self.root, text=" Consola ", font=("Arial", 9, "bold"), padx=8, pady=6)
        console_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=6)

        self.txt_consola = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=7, font=("Consolas", 9), bg="#090a0f", fg="#38bdf8")
        self.txt_consola.pack(fill=tk.BOTH, expand=True)

    def log(self, mensaje: str):
        self.txt_consola.insert(tk.END, mensaje + "\n")
        self.txt_consola.see(tk.END)

    def cargar_ejemplo(self, nombre_archivo: str):
        ruta_ejemplos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ejemplos", nombre_archivo)
        if os.path.exists(ruta_ejemplos):
            with open(ruta_ejemplos, "r", encoding="utf-8") as f:
                self.txt_codigo.delete("1.0", tk.END)
                self.txt_codigo.insert("1.0", f.read())

    def actualizar_lista_puertos(self, silencioso: bool = False):
        puertos = detectar_info_puertos_usb()
        self.puertos_map.clear()
        valores = []
        seleccionado = None

        for dev, es_esp, desc in puertos:
            etiqueta = f"{dev} — {desc}"
            valores.append(etiqueta)
            self.puertos_map[etiqueta] = dev
            if es_esp and not seleccionado:
                seleccionado = etiqueta

        self.combo_puertos['values'] = valores
        if seleccionado:
            self.combo_puertos.set(seleccionado)
            self.lbl_estado_puerto.config(text=f"ESP32 en {self.puertos_map[seleccionado]}", fg="#10b981")
        elif valores:
            self.combo_puertos.set(valores[0])
            self.lbl_estado_puerto.config(text="Puerto serie detectado", fg="#f59e0b")
        else:
            self.combo_puertos.set("Ninguno detectado")
            self.lbl_estado_puerto.config(text="Sin conexión USB", fg="#ef4444")

    def _iniciar_hilo_deteccion_automatica(self):
        def bucle_deteccion():
            puertos_previos = None
            while True:
                time.sleep(3.5)
                try:
                    puertos_actuales = [p[0] for p in detectar_info_puertos_usb()]
                    if puertos_previos is not None and set(puertos_actuales) != set(puertos_previos):
                        self.root.after(0, lambda: self.actualizar_lista_puertos(silencioso=False))
                    puertos_previos = puertos_actuales
                except Exception:
                    pass
        threading.Thread(target=bucle_deteccion, daemon=True).start()

    def obtener_puerto_seleccionado(self) -> Optional[str]:
        val = self.combo_puertos.get().strip()
        if not val or val == "Ninguno detectado":
            return detectar_puerto_esp32_automatico()
        return self.puertos_map.get(val, val)

    def abrir_modelo_3d(self):
        try:
            from .visualizador_3d import VentanaProtoboard3D
            VentanaProtoboard3D(self.root)
            self.log("[3D] Visor de protoboard abierto.")
        except Exception as e:
            self.log(f"[Error 3D] {e}")

    def compilar(self):
        codigo = self.txt_codigo.get("1.0", tk.END).strip()
        if not codigo:
            self.log("Error: El editor está vacío.")
            return

        self.log("Compilando SensorLang a C++ ESP32...")
        try:
            cpp, _ = compilar_sensorlang_a_cpp(codigo, wifi_ssid=self.entry_ssid.get(), wifi_pass=self.entry_pass.get())
            salida_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "salida_compilador")
            os.makedirs(salida_dir, exist_ok=True)
            with open(os.path.join(salida_dir, "salida_compilador.ino"), "w", encoding="utf-8") as f:
                f.write(cpp)
            self.log("Compilación exitosa. Sketch C++ generado.")
        except Exception as e:
            self.log(f"Error de compilación: {e}")

    def flashear_wifi(self):
        self.compilar()
        ip = self.entry_ip.get().strip()
        salida_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "salida_compilador")
        self.log(f"Compilando y subiendo por WiFi a http://{ip}/update...")

        def _subir():
            ok_cli, logs_cli = compilar_con_arduino_cli(salida_dir)
            if not ok_cli:
                self.root.after(0, lambda: self.log(f"Error arduino-cli:\n{logs_cli}"))
                return
            binario = os.path.join(salida_dir, "build", "esp32.esp32.esp32", "salida_compilador.ino.bin")
            if not os.path.exists(binario):
                binario = os.path.join(salida_dir, "build", "salida_compilador.ino.bin")
            ok_ota, logs_ota = subir_firmware_wifi(ip, binario)
            if ok_ota:
                self.root.after(0, lambda: self.log(f"Firmware OTA subido exitosamente a {ip}."))
            else:
                self.root.after(0, lambda: self.log(f"Fallo OTA: {logs_ota}"))

        threading.Thread(target=_subir, daemon=True).start()

    def flashear_usb(self):
        self.compilar()
        puerto = self.obtener_puerto_seleccionado()
        if not puerto:
            self.log("Error: Selecciona un puerto USB conectado.")
            return

        salida_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "salida_compilador")
        self.log(f"Subiendo por cable USB en {puerto}...")

        def _subir():
            ok, msg = subir_firmware_usb(puerto, salida_dir)
            if ok:
                self.root.after(0, lambda: self.log(f"Flasheo USB completado en {puerto}."))
            else:
                self.root.after(0, lambda: self.log(f"Error en flasheo USB:\n{msg}"))

        threading.Thread(target=_subir, daemon=True).start()


# =========================================================================
# Modo Línea de Comandos (CLI)
# =========================================================================
def ejecutar_cli(args):
    """Ejecuta SensorLang en modo terminal según los argumentos provistos."""
    if not os.path.exists(args.archivo):
        print(f"Error: El archivo '{args.archivo}' no existe.")
        sys.exit(1)

    with open(args.archivo, 'r', encoding='utf-8') as f:
        codigo_sl = f.read()

    print(f"\n[SensorLang] Compilando '{args.archivo}' para ESP32...")
    try:
        cpp, ast = compilar_sensorlang_a_cpp(codigo_sl, wifi_ssid=args.ssid or "", wifi_pass=args.password or "")
    except (LexerError, ParserError) as e:
        print(f"Error de sintaxis: {e}")
        sys.exit(1)

    ruta_salida_dir = args.output or os.path.join(os.getcwd(), 'salida_compilador')
    os.makedirs(ruta_salida_dir, exist_ok=True)
    ruta_salida_ino = os.path.join(ruta_salida_dir, 'salida_compilador.ino')

    with open(ruta_salida_ino, 'w', encoding='utf-8') as f:
        f.write(cpp)

    print(f"Sketch C++ generado en: {ruta_salida_ino}")

    if args.compile or args.upload_wifi or args.upload_usb:
        ruta_build = os.path.join(ruta_salida_dir, 'build')
        os.makedirs(ruta_build, exist_ok=True)
        print("Compilando con arduino-cli para ESP32...")
        ok, salida = compilar_con_arduino_cli(ruta_salida_dir, ruta_output_bin=ruta_build)
        if not ok:
            print(f"Fallo en compilación arduino-cli:\n{salida}")
            sys.exit(1)
        print("Compilación arduino-cli exitosa.")

        if args.upload_wifi:
            binario = os.path.join(ruta_build, 'salida_compilador.ino.bin')
            print(f"Subiendo por WiFi OTA a {args.upload_wifi}...")
            ok_subida, msg = subir_firmware_wifi(args.upload_wifi, binario)
            if ok_subida:
                print(f"Firmware OTA subido con éxito: {msg}")
            else:
                print(f"Fallo en subida WiFi: {msg}")
                sys.exit(1)

        elif args.upload_usb:
            puerto = args.upload_usb
            if puerto == "auto":
                puerto = detectar_puerto_esp32_automatico()
                if not puerto:
                    print("No se detectó automáticamente ningún ESP32 conectado por USB.")
                    sys.exit(1)
                print(f"ESP32 detectado en: {puerto}")
            print(f"Subiendo por USB en {puerto}...")
            ok_subida, msg = subir_firmware_usb(puerto, ruta_salida_dir)
            if ok_subida:
                print(f"Firmware subido por USB exitosamente:\n{msg}")
            else:
                print(f"Fallo al subir por USB:\n{msg}")
                sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Compilador SensorLang para ESP32 (Web Studio en Localhost, WiFi y USB)")
    parser.add_argument("archivo", nargs="?", help="Ruta al archivo .sl de SensorLang (modo terminal)")
    parser.add_argument("-o", "--output", help="Directorio de destino para el sketch C++ generado")
    parser.add_argument("-c", "--compile", action="store_true", help="Compilar binario ejecutable con arduino-cli")
    parser.add_argument("--upload-wifi", metavar="IP", help="Subir firmware inalámbrico vía WiFi (OTA) a la IP indicada")
    parser.add_argument("--upload-usb", nargs="?", const="auto", metavar="PUERTO", help="Subir firmware por cable USB (autodetecta si se omite)")
    parser.add_argument("--ssid", help="SSID de la red WiFi a la que conectará el ESP32")
    parser.add_argument("--password", help="Contraseña de la red WiFi")
    parser.add_argument("--port", type=int, default=5000, help="Puerto del servidor web local (por defecto: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="No abrir automáticamente el navegador web")
    parser.add_argument("--tk", action="store_true", help="Iniciar interfaz gráfica clásica en Tkinter")
    parser.add_argument("--view-3d", action="store_true", help="Abrir la ventana interactiva del modelo 3D de la protoboard")

    args = parser.parse_args()

    if args.view_3d:
        from .visualizador_3d import VentanaProtoboard3D
        app = VentanaProtoboard3D()
        app.root.mainloop()
        return

    if args.archivo:
        ejecutar_cli(args)
        return

    if args.tk:
        import tkinter as tk
        root = tk.Tk()
        app = SensorLangIDE(root)
        root.mainloop()
        return

    # Modo por defecto: Web Studio en localhost
    from .web_server import iniciar_servidor_web
    iniciar_servidor_web(puerto=args.port, abrir_navegador=not args.no_browser)


if __name__ == '__main__':
    main()

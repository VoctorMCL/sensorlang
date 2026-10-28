"""
Visualizador 3D de Alta Fidelidad para Protoboard y Conexiones ESP32.
Incorpora renderizado tridimensional con sombreado, perspectiva, componentes
con volumen real (LED abombado con reflejos y collarín, resistencia dumbbell con bandas axiales,
sensor DHT/MQ detallado con rejilla o cúpula metálica, ESP32 DevKit con pines header, botones
EN/BOOT, puerto USB y antena meandro, y cables Dupont con conectores negros).

Orientación de la Protoboard (400 puntos / 30 filas):
- Fila 30a: ARRIBA A LA DERECHA (Top-Right)
- Fila 1a: ARRIBA A LA IZQUIERDA (Top-Left)
- Fila 30j: ABAJO A LA DERECHA (Bottom-Right)
- Fila 1j: ABAJO A LA IZQUIERDA (Bottom-Left)
"""

import math
import os
import webbrowser
from typing import List, Tuple, Dict, Any, Optional

try:
    import tkinter as tk
    from tkinter import ttk
except ImportError:
    tk = None

class VentanaProtoboard3D:
    def __init__(self, parent=None):
        if tk is None:
            raise RuntimeError("Tkinter no está disponible.")

        if parent is None:
            self.root = tk.Tk()
            self.es_toplevel = False
        else:
            self.root = tk.Toplevel(parent)
            self.es_toplevel = True

        self.root.title("🧊 Modelo 3D Protoboard y Conexiones - SensorLang")
        self.root.geometry("1160x780")
        self.root.minsize(940, 620)

        # Parámetros de Cámara 3D (30a arriba-izquierda, 1j abajo-derecha)
        self.yaw = math.radians(-14)    # Ángulo horizontal
        self.pitch = math.radians(52)   # Inclinación vertical
        self.zoom = 22.0                # Escala
        self.pan_x = 0.0
        self.pan_y = 10.0

        # Estado del ratón
        self.mouse_last_x = 0
        self.mouse_last_y = 0

        # Opciones de visualización
        self.tipo_sensor = "DHT"         # "DHT" o "MQ"
        self.orientacion_invertida = False
        self.paso_resaltado = None

        self.crear_interfaz()
        self.dibujar_escena()

    def crear_interfaz(self):
        # Barra superior con controles
        top_bar = tk.Frame(self.root, bg="#111827", padx=12, pady=10)
        top_bar.pack(fill=tk.X)

        tk.Label(top_bar, text="Sensor:", fg="#e2e8f0", bg="#111827", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        
        self.var_sensor = tk.StringVar(value=self.tipo_sensor)
        btn_dht = tk.Radiobutton(top_bar, text="🌡️ Temp/Humedad (VCC, DATA, NC, GND)", variable=self.var_sensor, value="DHT",
                                 bg="#111827", fg="#38bdf8", selectcolor="#1f2937", activebackground="#111827",
                                 font=("Arial", 9, "bold"), command=self._cambiar_sensor)
        btn_dht.pack(side=tk.LEFT, padx=6)

        btn_mq = tk.Radiobutton(top_bar, text="💨 Aire/Gas (AO, DO, GND, VCC)", variable=self.var_sensor, value="MQ",
                                bg="#111827", fg="#fbbf24", selectcolor="#1f2937", activebackground="#111827",
                                font=("Arial", 9, "bold"), command=self._cambiar_sensor)
        btn_mq.pack(side=tk.LEFT, padx=6)

        # Botones de orientación de la placa
        btn_flip = tk.Button(top_bar, text="🔄 Girar 180°", font=("Arial", 9, "bold"), bg="#374151", fg="white",
                             activebackground="#4b5563", relief=tk.FLAT, padx=8, pady=3, command=self.girar_180)
        btn_flip.pack(side=tk.LEFT, padx=8)

        btn_iso = tk.Button(top_bar, text="📐 Vista 3D", font=("Arial", 9), bg="#374151", fg="white",
                            activebackground="#4b5563", relief=tk.FLAT, padx=6, pady=3, command=self.vista_isometrica)
        btn_iso.pack(side=tk.LEFT, padx=4)

        btn_top = tk.Button(top_bar, text="🔼 Vista Plana (2D)", font=("Arial", 9), bg="#374151", fg="white",
                            activebackground="#4b5563", relief=tk.FLAT, padx=6, pady=3, command=self.vista_superior)
        btn_top.pack(side=tk.LEFT, padx=4)

        btn_reset = tk.Button(top_bar, text="🎯 Centrar", font=("Arial", 9), bg="#374151", fg="white",
                              activebackground="#4b5563", relief=tk.FLAT, padx=6, pady=3, command=self.centrar_camara)
        btn_reset.pack(side=tk.LEFT, padx=4)

        btn_web = tk.Button(top_bar, text="🌐 Abrir 3D en Navegador", font=("Arial", 9, "bold"), bg="#059669", fg="white",
                            activebackground="#10b981", relief=tk.FLAT, padx=10, pady=3, command=self.abrir_en_navegador)
        btn_web.pack(side=tk.RIGHT, padx=4)

        # Contenedor central
        body_frame = tk.Frame(self.root, bg="#030712")
        body_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas de dibujo 3D
        self.canvas = tk.Canvas(body_frame, bg="#090d16", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag_left)
        self.canvas.bind("<ButtonPress-3>", self._on_mouse_down)
        self.canvas.bind("<B3-Motion>", self._on_mouse_drag_right)
        self.canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom(1.15))
        self.canvas.bind("<Button-5>", lambda e: self._zoom(0.85))
        self.canvas.bind("<Configure>", lambda e: self.dibujar_escena())

        # Panel lateral con instrucciones
        side_panel = tk.Frame(body_frame, bg="#111827", width=350, padx=16, pady=14)
        side_panel.pack(side=tk.RIGHT, fill=tk.Y)
        side_panel.pack_propagate(False)

        tk.Label(side_panel, text="🧭 Orientación Exacta de la Proto:", font=("Arial", 11, "bold"), fg="#38bdf8", bg="#111827").pack(anchor="w", pady=(0, 3))
        lbl_or = (
            "• Arriba a la izquierda: Fila 30a\n"
            "• Arriba a la derecha: Fila 1a\n"
            "• Abajo a la izquierda: Fila 30j\n"
            "• Abajo a la derecha: Fila 1j"
        )
        tk.Label(side_panel, text=lbl_or, font=("Consolas", 8, "bold"), fg="#93c5fd", bg="#111827", justify=tk.LEFT).pack(anchor="w", pady=(0, 10))

        tk.Label(side_panel, text="📋 Pasos de Armado (Clic para resaltar):", font=("Arial", 10, "bold"), fg="#f8fafc", bg="#111827").pack(anchor="w", pady=(0, 6))

        self.items_guia = [
            ("led", "1. LED (Filas 5 y 6)", "Ánodo (+) en 5c | Cátodo (-) en 6c", "#ef4444"),
            ("resistencia", "2. Resistencia 220Ω (Filas 6 y 8)", "Pata 1 en 6d | Pata 2 en 8d", "#f59e0b"),
            ("sensor", "3. Sensor 4 Pines (Filas 20 a 23)", "Pines 20c, 21c, 22c, 23c en Columna c", "#10b981"),
            ("esp32", "4. ESP32 (Al lado de la proto)", "Pines 3V3, GND, VN, D2 rotulados", "#06b6d4"),
            ("cables", "5. Cables Jumper", "D2 -> 5b | GND -> 8b | 3V3 -> 20b | VN -> 21b", "#eab308"),
        ]

        for tag, titulo, subtitulo, color in self.items_guia:
            f = tk.Frame(side_panel, bg="#1f2937", bd=1, relief=tk.SOLID, padx=9, pady=7, cursor="hand2")
            f.pack(fill=tk.X, pady=3)
            lbl_tit = tk.Label(f, text=titulo, font=("Arial", 9, "bold"), fg=color, bg="#1f2937", cursor="hand2")
            lbl_tit.pack(anchor="w")
            lbl_sub = tk.Label(f, text=subtitulo, font=("Arial", 8), fg="#cbd5e1", bg="#1f2937", cursor="hand2")
            lbl_sub.pack(anchor="w")
            
            f.bind("<Button-1>", lambda e, t=tag: self._resaltar_paso(t))
            lbl_tit.bind("<Button-1>", lambda e, t=tag: self._resaltar_paso(t))
            lbl_sub.bind("<Button-1>", lambda e, t=tag: self._resaltar_paso(t))

        # Aviso crítico
        f_aviso = tk.Frame(side_panel, bg="#450a0a", padx=10, pady=10, bd=1, relief=tk.RIDGE)
        f_aviso.pack(fill=tk.X, pady=(14, 0))
        tk.Label(f_aviso, text="🔥 ¿POR QUÉ OLIÓ A QUEMADO?", font=("Arial", 8, "bold"), fg="#f87171", bg="#450a0a").pack(anchor="w")
        tk.Label(f_aviso, text="1. Parpadeo rápido: El ESP32 entró en Brownout Reset loop (~10 reinicios/seg) por sobrecorriente.\n"
                               "2. Causa: Si metes la pata 1 de la resistencia en 6c y la pata 2 en 6d (misma fila), la resistencia queda en CORTO y el LED quema el regulador de 3.3V.\n"
                               "3. Solución: La pata 2 DEBE ir en la fila 8d para forzar el paso de corriente por el resistor.",
                 font=("Arial", 8), fg="#fecaca", bg="#450a0a", wraplength=310, justify=tk.LEFT).pack(anchor="w", pady=(3, 0))

    def _cambiar_sensor(self):
        self.tipo_sensor = self.var_sensor.get()
        self.dibujar_escena()

    def girar_180(self):
        self.orientacion_invertida = not self.orientacion_invertida
        self.dibujar_escena()

    def vista_isometrica(self):
        self.yaw = math.radians(-14)
        self.pitch = math.radians(52)
        self.dibujar_escena()

    def vista_superior(self):
        self.yaw = 0.0
        self.pitch = math.radians(88)
        self.dibujar_escena()

    def centrar_camara(self):
        self.vista_isometrica()
        self.zoom = 22.0
        self.pan_x = 0.0
        self.pan_y = 10.0
        self.paso_resaltado = None
        self.dibujar_escena()

    def _zoom(self, factor):
        self.zoom = max(8.0, min(75.0, self.zoom * factor))
        self.dibujar_escena()

    def _on_mouse_down(self, event):
        self.mouse_last_x = event.x
        self.mouse_last_y = event.y

    def _on_mouse_drag_left(self, event):
        dx = event.x - self.mouse_last_x
        dy = event.y - self.mouse_last_y
        self.mouse_last_x = event.x
        self.mouse_last_y = event.y

        self.yaw += dx * 0.01
        self.pitch = max(-math.pi/2 + 0.05, min(math.pi/2 - 0.05, self.pitch + dy * 0.01))
        self.dibujar_escena()

    def _on_mouse_drag_right(self, event):
        dx = event.x - self.mouse_last_x
        dy = event.y - self.mouse_last_y
        self.mouse_last_x = event.x
        self.mouse_last_y = event.y

        self.pan_x += dx
        self.pan_y += dy
        self.dibujar_escena()

    def _on_mouse_wheel(self, event):
        if event.delta > 0:
            self._zoom(1.15)
        else:
            self._zoom(0.85)

    def _resaltar_paso(self, tag):
        self.paso_resaltado = None if self.paso_resaltado == tag else tag
        self.dibujar_escena()

    # --- PROYECCIÓN 3D CON PERSPECTIVA ---
    def proyectar(self, x: float, y: float, z: float, w_canvas: int, h_canvas: int) -> Tuple[float, float, float]:
        if self.orientacion_invertida:
            x = -x
            y = -y

        cos_y = math.cos(self.yaw)
        sin_y = math.sin(self.yaw)
        x1 = x * cos_y - y * sin_y
        y1 = x * sin_y + y * cos_y

        sin_p = math.sin(self.pitch)
        cos_p = math.cos(self.pitch)

        cx = w_canvas / 2 + self.pan_x
        cy = h_canvas / 2 + self.pan_y

        px = cx + x1 * self.zoom
        py = cy - (y1 * sin_p + z * cos_p) * self.zoom
        depth = y1 * cos_p - z * sin_p
        return px, py, depth

    def coord_hueco(self, fila: int, letra: str) -> Tuple[float, float]:
        """
        Retorna las coordenadas 3D en el plano de la protoboard:
        Espejo horizontal: Fila 30 a la izquierda (-14.5), Fila 1 a la derecha (+14.5).
        Columna 'a' arriba (+4.8), Columna 'j' abajo (-4.8).
        -> 30a queda ARRIBA A LA IZQUIERDA y 1j ABAJO A LA DERECHA.
        """
        x = +15.0 - (fila - 0.5)
        cols = {
            'a': +4.8, 'b': +3.8, 'c': +2.8, 'd': +1.8, 'e': +0.8,
            'f': -0.8, 'g': -1.8, 'h': -2.8, 'i': -3.8, 'j': -4.8
        }
        y = cols.get(letra.lower(), 0.0)
        return x, y

    # --- DIBUJADO DE LA ESCENA ---
    def dibujar_escena(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        # 1. Base Protoboard sólida con biselado
        # X: -15.8 a +15.8 (31.6 largo), Y: -6.2 a +6.2 (12.4 ancho), Z: -1.4 a 0
        self._dibujar_prisma(-15.8, -6.0, -1.4, 31.6, 12.0, 1.4,
                             color_top="#f8fafc", color_front="#94a3b8", color_side="#cbd5e1", w=w, h=h)

        # Canal central divisor en Y = 0 (grabado oscuro)
        pC1 = self.proyectar(-15.5, 0.0, 0.02, w, h)
        pC2 = self.proyectar(+15.5, 0.0, 0.02, w, h)
        self.canvas.create_line(pC1[0], pC1[1], pC2[0], pC2[1], fill="#64748b", width=3)

        # Rieles de alimentación serigrafiados (+ rojo, - azul)
        pPos1 = self.proyectar(-15.2, +5.5, 0.02, w, h)
        pPos2 = self.proyectar(+15.2, +5.5, 0.02, w, h)
        self.canvas.create_line(pPos1[0], pPos1[1], pPos2[0], pPos2[1], fill="#ef4444", width=2)

        pNeg1 = self.proyectar(-15.2, -5.5, 0.02, w, h)
        pNeg2 = self.proyectar(+15.2, -5.5, 0.02, w, h)
        self.canvas.create_line(pNeg1[0], pNeg1[1], pNeg2[0], pNeg2[1], fill="#3b82f6", width=2)

        # 2. Orificios de la protoboard (Filas 1 a 30)
        for f in range(1, 31):
            if f in (1, 5, 10, 15, 20, 25, 30):
                hx_f = 15.0 - (f - 0.5)
                p_num_top = self.proyectar(hx_f, +5.8, 0.03, w, h)
                self.canvas.create_text(p_num_top[0], p_num_top[1], text=str(f), fill="#475569", font=("Consolas", 8, "bold"))
                p_num_bot = self.proyectar(hx_f, -5.8, 0.03, w, h)
                self.canvas.create_text(p_num_bot[0], p_num_bot[1], text=str(f), fill="#475569", font=("Consolas", 8, "bold"))

            for letra in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']:
                hx, hy = self.coord_hueco(f, letra)
                p = self.proyectar(hx, hy, 0.01, w, h)
                rad = max(1.5, self.zoom * 0.11)

                # Colorear según asignación
                color_h = "#334155"
                if (f, letra) in [(5, 'c'), (6, 'c')]:
                    color_h = "#ef4444" if (self.paso_resaltado in (None, "led")) else "#7f1d1d"
                elif (f, letra) in [(6, 'd'), (8, 'd')]:
                    color_h = "#f59e0b" if (self.paso_resaltado in (None, "resistencia")) else "#78350f"
                elif (f, letra) in [(20, 'c'), (21, 'c'), (22, 'c'), (23, 'c')]:
                    color_h = "#10b981" if (self.paso_resaltado in (None, "sensor")) else "#064e3b"
                elif (f, letra) in [(5, 'b'), (8, 'b'), (20, 'b'), (21, 'b'), (23, 'b')]:
                    color_h = "#eab308" if (self.paso_resaltado in (None, "cables")) else "#713f12"

                self.canvas.create_oval(p[0] - rad, p[1] - rad, p[0] + rad, p[1] + rad, fill=color_h, outline="#0f172a")

        # Letras de columnas en los extremos
        for col_l in ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']:
            hx_30, hy_30 = self.coord_hueco(30, col_l)
            p_letra_l = self.proyectar(hx_30 - 0.8, hy_30, 0.03, w, h)
            self.canvas.create_text(p_letra_l[0], p_letra_l[1], text=col_l, fill="#334155", font=("Consolas", 8, "bold"))

            hx_1, hy_1 = self.coord_hueco(1, col_l)
            p_letra_r = self.proyectar(hx_1 + 0.8, hy_1, 0.03, w, h)
            self.canvas.create_text(p_letra_r[0], p_letra_r[1], text=col_l, fill="#334155", font=("Consolas", 8, "bold"))

        # Marcas de esquina solicitadas (30a arriba a la izquierda, 1j abajo a la derecha)
        p_c30a = self.proyectar(self.coord_hueco(30, 'a')[0] - 1.2, self.coord_hueco(30, 'a')[1] + 1.8, 0.05, w, h)
        self.canvas.create_text(p_c30a[0], p_c30a[1], text="📍 30a (Arriba-Izq)", fill="#0284c7", font=("Arial", 9, "bold"))

        p_c1j = self.proyectar(self.coord_hueco(1, 'j')[0] + 1.2, self.coord_hueco(1, 'j')[1] - 1.8, 0.05, w, h)
        self.canvas.create_text(p_c1j[0], p_c1j[1], text="📍 1j (Abajo-Der)", fill="#0284c7", font=("Arial", 9, "bold"))

        # 3. LED 5mm MODELADO CON CÚPULA REDONDEADA Y BRILLO RADIAL (Filas 5c y 6c)
        hx_led5, hy_led5 = self.coord_hueco(5, 'c')
        hx_led6, hy_led6 = self.coord_hueco(6, 'c')

        p_anodo = self.proyectar(hx_led5, hy_led5, 0.0, w, h)
        p_catodo = self.proyectar(hx_led6, hy_led6, 0.0, w, h)
        p_led_base = self.proyectar((hx_led5 + hx_led6)/2, hy_led5, 2.5, w, h)
        p_led_top = self.proyectar((hx_led5 + hx_led6)/2, hy_led5, 3.8, w, h)

        # Patas metálicas dobladas
        self.canvas.create_line(p_anodo[0], p_anodo[1], p_led_base[0] - 2, p_led_base[1], fill="#94a3b8", width=2.5)
        self.canvas.create_line(p_catodo[0], p_catodo[1], p_led_base[0] + 2, p_led_base[1], fill="#94a3b8", width=2.5)

        # Collarín inferior del LED
        rad_base = max(5, self.zoom * 0.42)
        self.canvas.create_oval(p_led_base[0] - rad_base, p_led_base[1] - rad_base*0.4,
                                p_led_base[0] + rad_base, p_led_base[1] + rad_base*0.4,
                                fill="#991b1b", outline="#7f1d1d")

        # Cúpula esférica translúcida
        rad_cupula = max(6, self.zoom * 0.48)
        self.canvas.create_oval(p_led_top[0] - rad_cupula, p_led_top[1] - rad_cupula,
                                p_led_top[0] + rad_cupula, p_led_top[1] + rad_cupula,
                                fill="#dc2626", outline="#991b1b", width=2)
        # Brillo especular
        self.canvas.create_oval(p_led_top[0] - rad_cupula*0.45, p_led_top[1] - rad_cupula*0.5,
                                p_led_top[0] - rad_cupula*0.05, p_led_top[1] - rad_cupula*0.15,
                                fill="#fca5a5", outline="")

        self.canvas.create_text(p_led_top[0], p_led_top[1] - rad_cupula - 8,
                                text="🔴 LED (5c: +, 6c: -)", fill="#f87171", font=("Arial", 8, "bold"))

        # 4. RESISTENCIA 220 Ω AXIAL CON CUERPO Y BANDAS (Filas 6d y 8d)
        hx_r6, hy_r6 = self.coord_hueco(6, 'd')
        hx_r8, hy_r8 = self.coord_hueco(8, 'd')

        p_r1 = self.proyectar(hx_r6, hy_r6, 0.0, w, h)
        p_r2 = self.proyectar(hx_r8, hy_r8, 0.0, w, h)
        p_rc = self.proyectar((hx_r6 + hx_r8)/2, hy_r6, 1.5, w, h)

        # Alambres conductores doblados
        self.canvas.create_line(p_r1[0], p_r1[1], p_rc[0] - 10, p_rc[1], fill="#94a3b8", width=2)
        self.canvas.create_line(p_r2[0], p_r2[1], p_rc[0] + 10, p_rc[1], fill="#94a3b8", width=2)

        # Cuerpo cerámico beige de la resistencia
        rx = max(8, self.zoom * 0.6)
        ry = max(3, self.zoom * 0.26)
        self.canvas.create_oval(p_rc[0] - rx, p_rc[1] - ry, p_rc[0] + rx, p_rc[1] + ry,
                                fill="#d2b48c", outline="#8c6d46", width=1.5)

        # Bandas de 220 Ω (Rojo, Rojo, Marrón, Dorado)
        b_x = [-rx * 0.5, -rx * 0.15, rx * 0.2, rx * 0.6]
        b_col = ["#dc2626", "#dc2626", "#78350f", "#eab308"]
        for bx, col in zip(b_x, b_col):
            self.canvas.create_line(p_rc[0] + bx, p_rc[1] - ry + 1, p_rc[0] + bx, p_rc[1] + ry - 1, fill=col, width=2.5)

        self.canvas.create_text(p_rc[0], p_rc[1] - ry - 9,
                                text="Resistencia 220Ω (6d -> 8d)", fill="#fbbf24", font=("Arial", 8, "bold"))

        # 5. SENSOR DE 4 PINES ULTRA DETALLADO (Filas 20 a 23 en Columna c)
        hx_s20, hy_s = self.coord_hueco(20, 'c')
        hx_s23, _ = self.coord_hueco(23, 'c')

        # Pines metálicos dorados que bajan verticalmente
        for f in range(20, 24):
            hxf, hyf = self.coord_hueco(f, 'c')
            pb = self.proyectar(hxf, hyf, 0.0, w, h)
            pt = self.proyectar(hxf, hyf, 1.8, w, h)
            self.canvas.create_line(pb[0], pb[1], pt[0], pt[1], fill="#eab308", width=2.5)

        cx_sensor = (hx_s20 + hx_s23) / 2
        cy_sensor = hy_s

        if self.tipo_sensor == "DHT":
            # Breakout PCB azul
            self._dibujar_prisma(cx_sensor - 2.4, cy_sensor - 1.8, 1.6, 4.8, 3.6, 0.4,
                                 color_top="#0369a1", color_front="#082f49", color_side="#075985", w=w, h=h)
            # Carcasa celeste del DHT11
            self._dibujar_prisma(cx_sensor - 2.0, cy_sensor - 1.5, 2.0, 4.0, 3.0, 2.2,
                                 color_top="#38bdf8", color_front="#0284c7", color_side="#0369a1", w=w, h=h)
            # Rejillas de ventilación
            for slot_z in [2.5, 3.0, 3.5]:
                ps1 = self.proyectar(cx_sensor - 1.4, cy_sensor + 1.51, slot_z, w, h)
                ps2 = self.proyectar(cx_sensor + 1.4, cy_sensor + 1.51, slot_z, w, h)
                self.canvas.create_line(ps1[0], ps1[1], ps2[0], ps2[1], fill="#0369a1", width=2)
            lbl_sen = "🌡️ DHT11 (Temp/Hum)"
        else:
            # Módulo MQ: PCB verde con cúpula cilíndrica de malla
            self._dibujar_prisma(cx_sensor - 2.4, cy_sensor - 1.8, 1.6, 4.8, 3.6, 0.5,
                                 color_top="#15803d", color_front="#052e16", color_side="#166534", w=w, h=h)
            # Cúpula de malla metálica redonda
            p_malla_b = self.proyectar(cx_sensor, cy_sensor, 2.1, w, h)
            p_malla_t = self.proyectar(cx_sensor, cy_sensor, 3.5, w, h)
            rad_m = max(8, self.zoom * 0.52)
            self.canvas.create_oval(p_malla_t[0] - rad_m, p_malla_t[1] - rad_m,
                                    p_malla_t[0] + rad_m, p_malla_t[1] + rad_m,
                                    fill="#cbd5e1", outline="#64748b", width=2)
            # Rejilla circular en el centro
            self.canvas.create_oval(p_malla_t[0] - rad_m*0.6, p_malla_t[1] - rad_m*0.6,
                                    p_malla_t[0] + rad_m*0.6, p_malla_t[1] + rad_m*0.6,
                                    fill="#94a3b8", outline="#475569")
            lbl_sen = "💨 Sensor MQ (Aire/Gas)"

        p_txt_sen = self.proyectar(cx_sensor, cy_sensor, 4.5, w, h)
        self.canvas.create_text(p_txt_sen[0], p_txt_sen[1], text=lbl_sen, fill="#38bdf8", font=("Arial", 9, "bold"))

        # Llamador de pines del sensor (Limpieza visual sin solapamiento)
        p_card_anchor = self.proyectar(cx_sensor + 3.2, cy_sensor + 1.2, 2.5, w, h)
        pines_info = [
            ("20c", "VCC (3.3V)" if self.tipo_sensor == "DHT" else "AO (Señal a VN)", "#38bdf8"),
            ("21c", "DATA (A Pin VN)" if self.tipo_sensor == "DHT" else "DO (Sin Conectar)", "#38bdf8" if self.tipo_sensor == "DHT" else "#94a3b8"),
            ("22c", "NC (¡DEJAR VACÍO!)" if self.tipo_sensor == "DHT" else "GND (Tierra)", "#ef4444" if self.tipo_sensor == "DHT" else "#cbd5e1"),
            ("23c", "GND (Tierra)" if self.tipo_sensor == "DHT" else "VCC (Alimentación)", "#cbd5e1" if self.tipo_sensor == "DHT" else "#ef4444")
        ]
        
        # Fondo translúcido para el cartel de pines
        card_x = p_card_anchor[0] + 10
        card_y = p_card_anchor[1] - 40
        self.canvas.create_rectangle(card_x - 6, card_y - 6, card_x + 160, card_y + 70,
                                     fill="#0f172a", outline="#334155", width=1.5)
        self.canvas.create_text(card_x, card_y, anchor="nw", text=f"Pines {lbl_sen}:", fill="#f8fafc", font=("Arial", 8, "bold"))
        
        for idx, (p_pin, p_nom, c_cor) in enumerate(pines_info):
            txt_line = f"• {p_pin}: {p_nom}"
            self.canvas.create_text(card_x + 4, card_y + 16 + idx * 13, anchor="nw",
                                    text=txt_line, fill=c_cor, font=("Consolas", 8, "bold"))

        # 6. ESP32 DEVKIT DE ALTA CALIDAD CON PINES, BOTONES Y BLINDAJE
        x_esp = 0.0
        y_esp = -12.5

        # PCB negro mate con bisel
        self._dibujar_prisma(x_esp - 8.0, y_esp - 3.2, 0.0, 16.0, 6.4, 0.9,
                             color_top="#18181b", color_front="#09090b", color_side="#111827", w=w, h=h)

        # Tiras de pines Header negras con pines dorados (Superior e Inferior)
        for px_off in range(-7, 8):
            # Pin header superior
            p_pin_top = self.proyectar(x_esp + px_off * 0.95, y_esp + 2.7, 0.9, w, h)
            self.canvas.create_rectangle(p_pin_top[0]-2, p_pin_top[1]-2, p_pin_top[0]+2, p_pin_top[1]+2, fill="#09090b", outline="#eab308")
            # Pin header inferior
            p_pin_bot = self.proyectar(x_esp + px_off * 0.95, y_esp - 2.7, 0.9, w, h)
            self.canvas.create_rectangle(p_pin_bot[0]-2, p_pin_bot[1]-2, p_pin_bot[0]+2, p_pin_bot[1]+2, fill="#09090b", outline="#eab308")

        # Blindaje metálico plateado ESP-WROOM-32
        self._dibujar_prisma(x_esp - 5.8, y_esp - 2.1, 0.9, 7.5, 4.2, 0.6,
                             color_top="#e2e8f0", color_front="#94a3b8", color_side="#cbd5e1", w=w, h=h)
        
        # Grabado de antena meandro en PCB
        p_ant = self.proyectar(x_esp - 7.0, y_esp, 1.5, w, h)
        self.canvas.create_text(p_ant[0], p_ant[1], text="📡 ESP32", fill="#e2e8f0", font=("Arial", 8, "bold"))

        # Conector micro-USB metálico a la derecha
        self._dibujar_prisma(x_esp + 7.0, y_esp - 1.2, 0.9, 1.8, 2.4, 0.8,
                             color_top="#cbd5e1", color_front="#64748b", color_side="#94a3b8", w=w, h=h)

        # Botones táctiles EN y BOOT
        p_btn_en = self.proyectar(x_esp - 5.5, y_esp + 1.8, 1.0, w, h)
        self.canvas.create_oval(p_btn_en[0]-2.5, p_btn_en[1]-2.5, p_btn_en[0]+2.5, p_btn_en[1]+2.5, fill="#cbd5e1", outline="#475569")
        self.canvas.create_text(p_btn_en[0], p_btn_en[1] - 8, text="EN", fill="#94a3b8", font=("Consolas", 6, "bold"))

        p_btn_boot = self.proyectar(x_esp + 5.0, y_esp + 1.8, 1.0, w, h)
        self.canvas.create_oval(p_btn_boot[0]-2.5, p_btn_boot[1]-2.5, p_btn_boot[0]+2.5, p_btn_boot[1]+2.5, fill="#cbd5e1", outline="#475569")
        self.canvas.create_text(p_btn_boot[0], p_btn_boot[1] - 8, text="BOOT", fill="#94a3b8", font=("Consolas", 6, "bold"))

        # LED Onboard (Rojo encendido y Azul D2)
        p_led_pwr = self.proyectar(x_esp + 3.2, y_esp + 1.8, 1.0, w, h)
        self.canvas.create_oval(p_led_pwr[0]-2, p_led_pwr[1]-2, p_led_pwr[0]+2, p_led_pwr[1]+2, fill="#ef4444", outline="")

        # Pines clave rotulados con llamadores
        p_esp_d2 = self.proyectar(x_esp + 3.5, y_esp + 2.8, 0.5, w, h)
        p_esp_vn = self.proyectar(x_esp - 3.5, y_esp - 2.8, 0.5, w, h)
        p_esp_3v3 = self.proyectar(x_esp - 5.5, y_esp - 2.8, 0.5, w, h)
        p_esp_gnd = self.proyectar(x_esp + 4.5, y_esp - 2.8, 0.5, w, h)

        self.canvas.create_oval(p_esp_d2[0]-4, p_esp_d2[1]-4, p_esp_d2[0]+4, p_esp_d2[1]+4, fill="#22c55e", outline="#15803d")
        self.canvas.create_text(p_esp_d2[0], p_esp_d2[1] + 13, text="Pin D2 (GPIO 2)", fill="#86efac", font=("Arial", 8, "bold"))

        self.canvas.create_oval(p_esp_vn[0]-4, p_esp_vn[1]-4, p_esp_vn[0]+4, p_esp_vn[1]+4, fill="#38bdf8", outline="#0284c7")
        self.canvas.create_text(p_esp_vn[0], p_esp_vn[1] - 13, text="Pin VN (A1)", fill="#7dd3fc", font=("Arial", 8, "bold"))

        self.canvas.create_oval(p_esp_3v3[0]-4, p_esp_3v3[1]-4, p_esp_3v3[0]+4, p_esp_3v3[1]+4, fill="#ef4444", outline="#b91c1c")
        self.canvas.create_text(p_esp_3v3[0] - 14, p_esp_3v3[1] - 13, text="Pin 3V3", fill="#fca5a5", font=("Arial", 8, "bold"))

        self.canvas.create_oval(p_esp_gnd[0]-4, p_esp_gnd[1]-4, p_esp_gnd[0]+4, p_esp_gnd[1]+4, fill="#ffffff", outline="#94a3b8")
        self.canvas.create_text(p_esp_gnd[0] + 14, p_esp_gnd[1] - 13, text="Pin GND", fill="#ffffff", font=("Arial", 8, "bold"))

        # Pin GND del sensor en el lado izquierdo del ESP32
        p_esp_gnd_s = self.proyectar(x_esp - 4.5, y_esp - 2.8, 0.5, w, h)
        self.canvas.create_oval(p_esp_gnd_s[0]-4, p_esp_gnd_s[1]-4, p_esp_gnd_s[0]+4, p_esp_gnd_s[1]+4, fill="#ffffff", outline="#94a3b8")
        self.canvas.create_text(p_esp_gnd_s[0], p_esp_gnd_s[1] + 14, text="Pin GND", fill="#ffffff", font=("Arial", 7, "bold"))

        # 7. CABLES JUMPERS CON ARCOS REALISTAS Y CONECTORES DUPONT
        # Cable 1: LED señal -> ESP32 D2 (Verde) hacia Fila 5b
        hx_5b, hy_5b = self.coord_hueco(5, 'b')
        self._dibujar_cable_dupont_3d(x_esp + 3.5, y_esp + 2.8, 0.5,
                                      hx_5b, hy_5b, 0.0,
                                      altura_arco=4.8, color="#22c55e", ancho=3.5, w=w, h=h)

        # Cable 2: LED tierra -> Resistencia en Fila 8b hacia ESP32 GND (Gris)
        hx_8b, hy_8b = self.coord_hueco(8, 'b')
        self._dibujar_cable_dupont_3d(x_esp + 4.5, y_esp - 2.8, 0.5,
                                      hx_8b, hy_8b, 0.0,
                                      altura_arco=4.0, color="#64748b", ancho=3.5, w=w, h=h)

        # Cable 3: Sensor VCC -> ESP32 3V3 (Rojo) hacia 20b (DHT) o 23b (MQ)
        fila_vcc = 20 if self.tipo_sensor == "DHT" else 23
        hx_vcc, hy_vcc = self.coord_hueco(fila_vcc, 'b')
        self._dibujar_cable_dupont_3d(x_esp - 5.5, y_esp - 2.8, 0.5,
                                      hx_vcc, hy_vcc, 0.0,
                                      altura_arco=5.5, color="#ef4444", ancho=3.5, w=w, h=h)

        # Cable 4: Sensor DATA -> ESP32 VN (Azul) hacia 21b (DHT) o 20b (MQ)
        fila_sig = 21 if self.tipo_sensor == "DHT" else 20
        hx_sig, hy_sig = self.coord_hueco(fila_sig, 'b')
        self._dibujar_cable_dupont_3d(x_esp - 3.5, y_esp - 2.8, 0.5,
                                      hx_sig, hy_sig, 0.0,
                                      altura_arco=4.6, color="#0284c7", ancho=3.5, w=w, h=h)

        # Cable 5: Sensor GND -> ESP32 GND (Blanco/Gris) hacia 23b (DHT) o 22b (MQ)
        fila_gnd = 23 if self.tipo_sensor == "DHT" else 22
        hx_gnd, hy_gnd = self.coord_hueco(fila_gnd, 'b')
        self._dibujar_cable_dupont_3d(x_esp - 4.5, y_esp - 2.8, 0.5,
                                      hx_gnd, hy_gnd, 0.0,
                                      altura_arco=3.6, color="#e2e8f0", ancho=3.0, w=w, h=h)

    def _dibujar_prisma(self, x, y, z, dx, dy, dz, color_top, color_front, color_side, w, h):
        """Dibuja un prisma 3D sólido respetando sombreado en sus 3 caras visibles."""
        v = [
            (x, y, z), (x + dx, y, z), (x + dx, y + dy, z), (x, y + dy, z),
            (x, y, z + dz), (x + dx, y, z + dz), (x + dx, y + dy, z + dz), (x, y + dy, z + dz)
        ]
        vp = [self.proyectar(vx, vy, vz, w, h) for vx, vy, vz in v]

        # Cara frontal
        self.canvas.create_polygon(vp[3][0], vp[3][1], vp[2][0], vp[2][1], vp[6][0], vp[6][1], vp[7][0], vp[7][1],
                                   fill=color_front, outline="#0f172a", width=1)
        # Cara lateral
        self.canvas.create_polygon(vp[1][0], vp[1][1], vp[2][0], vp[2][1], vp[6][0], vp[6][1], vp[5][0], vp[5][1],
                                   fill=color_side, outline="#0f172a", width=1)
        # Cara superior
        self.canvas.create_polygon(vp[4][0], vp[4][1], vp[5][0], vp[5][1], vp[6][0], vp[6][1], vp[7][0], vp[7][1],
                                   fill=color_top, outline="#334155", width=1)

    def _dibujar_cable_dupont_3d(self, x1, y1, z1, x2, y2, z2, altura_arco, color, ancho, w, h):
        """Dibuja un cable jumper con conectores negros Dupont en ambos extremos."""
        # Conector negro Dupont en el orificio de la protoboard
        p_boot_b = self.proyectar(x2, y2, 0.0, w, h)
        p_boot_t = self.proyectar(x2, y2, 0.9, w, h)
        self.canvas.create_line(p_boot_b[0], p_boot_b[1], p_boot_t[0], p_boot_t[1], fill="#020617", width=5, capstyle=tk.PROJECTING)

        # Arco parabólico suave para el cable
        pasos = 24
        puntos = []
        for i in range(pasos + 1):
            t = i / pasos
            xt = x1 + (x2 - x1) * t
            yt = y1 + (y2 - y1) * t
            zt = z1 + (z2 - z1) * t + math.sin(t * math.pi) * altura_arco
            puntos.append(self.proyectar(xt, yt, zt, w, h))

        for i in range(len(puntos) - 1):
            p_ini = puntos[i]
            p_fin = puntos[i+1]
            self.canvas.create_line(p_ini[0], p_ini[1], p_fin[0], p_fin[1], fill=color, width=ancho, capstyle=tk.ROUND)

    def abrir_en_navegador(self):
        """Abre el Web Studio en el navegador local."""
        webbrowser.open("http://localhost:5000")

def main():
    app = VentanaProtoboard3D()
    app.root.mainloop()

if __name__ == '__main__':
    main()

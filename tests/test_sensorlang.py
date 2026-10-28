import unittest
import os
import subprocess
from sensorlang.lexer import lexer, Token, LexerError
from sensorlang.parser import parsear, ParserError
from sensorlang.generador import generar_cpp

class TestLexer(unittest.TestCase):
    def test_tokens_basicos(self):
        codigo = "pin led = 2; // pin led\nencender(led);"
        tokens = list(lexer(codigo))
        tipos = [t.type for t in tokens]
        self.assertEqual(tipos, ['PIN_DECL', 'ID', 'ASIGNAR', 'NUMERO', 'PUNTOCOMA', 'ENCENDER', 'LPAREN', 'ID', 'RPAREN', 'PUNTOCOMA'])

    def test_palabras_reservadas(self):
        codigo = "leer leer_analogo leer_digital mostrar alerta esperar si sino apagar"
        tokens = list(lexer(codigo))
        tipos = [t.type for t in tokens]
        self.assertEqual(tipos, ['LEER', 'LEER_ANALOGO', 'LEER_DIGITAL', 'MOSTRAR', 'ALERTA', 'ESPERAR', 'SI', 'SINO', 'APAGAR'])

    def test_cadenas_y_comentarios(self):
        codigo = '/* Bloque */ alerta("Alerta!"); # Comentario linea\n alerta(\'Otra alerta\');'
        tokens = list(lexer(codigo))
        self.assertEqual(tokens[0].type, 'ALERTA')
        self.assertEqual(tokens[1].type, 'LPAREN')
        self.assertEqual(tokens[2].type, 'CADENA')
        self.assertEqual(tokens[2].value, '"Alerta!"')
        self.assertEqual(tokens[7].type, 'CADENA')
        self.assertEqual(tokens[7].value, "'Otra alerta'")

    def test_error_lexico(self):
        with self.assertRaises(LexerError):
            list(lexer("pin x = @123;"))

class TestParser(unittest.TestCase):
    def test_parsear_declaracion_y_accion(self):
        codigo = "pin led = 2;\nencender(led);"
        ast = parsear(lexer(codigo))
        self.assertEqual(len(ast), 2)
        self.assertEqual(ast[0]['tipo'], 'declaracion_pin')
        self.assertEqual(ast[0]['var'], 'led')
        self.assertEqual(ast[0]['pin'], '2')
        self.assertEqual(ast[1]['tipo'], 'accion')
        self.assertEqual(ast[1]['comando'], 'encender')
        self.assertEqual(ast[1]['pin'], 'led')

    def test_parsear_lectura_y_mostrar(self):
        codigo = "val = leer_analogo(sensor);\nmostrar(val);"
        ast = parsear(lexer(codigo))
        self.assertEqual(len(ast), 2)
        self.assertEqual(ast[0]['tipo'], 'lectura')
        self.assertEqual(ast[0]['modo'], 'analogo')
        self.assertEqual(ast[1]['tipo'], 'mostrar')

    def test_parsear_condicional(self):
        codigo = """
        si (val > 500) {
            encender(led);
        } sino {
            apagar(led);
        }
        """
        ast = parsear(lexer(codigo))
        self.assertEqual(len(ast), 1)
        self.assertEqual(ast[0]['tipo'], 'si')
        self.assertEqual(len(ast[0]['bloque_si']), 1)
        self.assertEqual(len(ast[0]['bloque_sino']), 1)

    def test_error_sintactico(self):
        with self.assertRaises(ParserError):
            parsear(lexer("si val > 500 { encender(led); }"))

class TestGenerador(unittest.TestCase):
    def test_generar_cpp_elementos_clave(self):
        codigo = """
        pin led = 2;
        pin sensor = A1;
        val = leer_analogo(sensor);
        mostrar(val);
        si (val > 400) {
            encender(led);
            alerta("Peligro");
        }
        """
        ast = parsear(lexer(codigo))
        cpp = generar_cpp(ast, wifi_ssid="MiRed", wifi_pass="12345678")
        
        # Verificar macros de pines
        self.assertIn("#define A1 39", cpp)
        # Verificar setup de WiFi y WebServer
        self.assertIn("WebServer server(80);", cpp)
        self.assertIn("WiFi.softAP(\"SensorLang-ESP32\", \"12345678\");", cpp)
        self.assertIn("server.on(\"/telemetria\"", cpp)
        self.assertIn("server.on(\"/update\"", cpp)
        self.assertIn("registrarLog(\"Lectura Sensor\"", cpp)
        self.assertIn("registrarLog(\"Alerta\"", cpp)
        self.assertIn("digitalWrite(led, HIGH);", cpp)

if __name__ == '__main__':
    unittest.main()

class TestIntegracionArduinoCLI(unittest.TestCase):
    def test_compilar_ejemplos_arduino_cli(self):
        ejemplos_dir = os.path.join(os.path.dirname(__file__), '..', 'ejemplos')
        salida_dir = os.path.join(os.path.dirname(__file__), '..', 'salida_compilador')
        os.makedirs(salida_dir, exist_ok=True)
        ino_path = os.path.join(salida_dir, 'salida_compilador.ino')

        for archivo in ['prender_led.sl', 'alerta_temperatura.sl', 'parpadeo_wifi.sl']:
            ruta = os.path.join(ejemplos_dir, archivo)
            with open(ruta, 'r', encoding='utf-8') as f:
                codigo = f.read()

            ast = parsear(lexer(codigo))
            cpp = generar_cpp(ast)
            with open(ino_path, 'w', encoding='utf-8') as f:
                f.write(cpp)

            cmd = ["arduino-cli", "compile", "--fqbn", "esp32:esp32:esp32", salida_dir]
            res = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, f"Fallo al compilar {archivo}:\n{res.stderr}\n{res.stdout}")

class TestDeteccionPuertos(unittest.TestCase):
    def test_deteccion_puertos_lista(self):
        from sensorlang.esp32_tools import detectar_info_puertos_usb, detectar_puerto_esp32_automatico
        puertos = detectar_info_puertos_usb()
        self.assertIsInstance(puertos, list)
        for p in puertos:
            self.assertEqual(len(p), 3)
            # Asegurar que no se devuelvan puertos virtuales ttyS
            self.assertFalse(p[0].startswith('/dev/ttyS') and p[0][9:].isdigit())

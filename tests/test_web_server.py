import unittest
import threading
import time
import urllib.request
import json
import os

from sensorlang.web_server import SensorLangWebHandler, ThreadingHTTPServer, encontrar_puerto_libre

class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puerto = encontrar_puerto_libre(5890)
        cls.server = ThreadingHTTPServer(('127.0.0.1', cls.puerto), SensorLangWebHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)
        cls.base_url = f"http://127.0.0.1:{cls.puerto}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_status_endpoint(self):
        url = f"{self.base_url}/api/status"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertEqual(data.get("fqbn"), "esp32:esp32:esp32")

    def test_puertos_endpoint(self):
        url = f"{self.base_url}/api/puertos"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertIn("puertos", data)

    def test_ejemplos_endpoint(self):
        url = f"{self.base_url}/api/ejemplos"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertTrue(len(data.get("ejemplos", [])) >= 3)

    def test_compilar_endpoint(self):
        url = f"{self.base_url}/api/compilar"
        payload = json.dumps({
            "codigo": "pin led = 2;\nencender(led);",
            "wifi_ssid": "TestNet",
            "wifi_pass": "12345678",
            "verificar_arduino": False
        }).encode()

        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode())
            self.assertTrue(data.get("ok"))
            self.assertIn("digitalWrite(led, HIGH)", data.get("cpp_codigo", ""))

    def test_servir_index_html(self):
        url = f"{self.base_url}/"
        with urllib.request.urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode()
            self.assertIn("SensorLang", content)
            self.assertIn("three-container", content)

    def test_servir_vendor_threejs(self):
        with urllib.request.urlopen(f"{self.base_url}/vendor/three.min.js") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.headers.get("Content-Type", ""))
            self.assertGreater(len(resp.read()), 100000)

        with urllib.request.urlopen(f"{self.base_url}/vendor/OrbitControls.js") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.headers.get("Content-Type", ""))
            self.assertGreater(len(resp.read()), 10000)

    def test_servir_static_css_and_js(self):
        with urllib.request.urlopen(f"{self.base_url}/style.css") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("text/css", resp.headers.get("Content-Type", ""))

        with urllib.request.urlopen(f"{self.base_url}/app.js") as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("javascript", resp.headers.get("Content-Type", ""))

if __name__ == '__main__':
    unittest.main()

// Código C++ generado automáticamente por SensorLang para ESP32
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Update.h>

// ==========================================
// Mapeo de compatibilidad de pines analógicos ESP32
// ==========================================
#ifndef A0
#define A0 36 // SENSOR_VP
#endif
#ifndef A1
#define A1 39 // SENSOR_VN
#endif
#ifndef A2
#define A2 34
#endif
#ifndef A3
#define A3 35
#endif
#ifndef A4
#define A4 32
#endif
#ifndef A5
#define A5 33
#endif
#ifndef A6
#define A6 25
#endif
#ifndef A7
#define A7 26
#endif

// Variables globales del sketch
int led = 2;


// Servidor Web para telemetría y actualización OTA
WebServer server(80);

// Buffer circular en memoria para lecturas de sensores y alertas
#define LOG_BUFFER_SIZE 30
String logBuffer[LOG_BUFFER_SIZE];
int logHead = 0;
int logCount = 0;

void registrarLog(const String& tipo, const String& mensaje) {
  String linea = "[" + tipo + "]: " + mensaje;
  Serial.println(linea);
  logBuffer[logHead] = linea;
  logHead = (logHead + 1) % LOG_BUFFER_SIZE;
  if (logCount < LOG_BUFFER_SIZE) logCount++;
}

const char INDEX_HTML[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SensorLang ESP32 Dashboard</title>
  <style>
    body { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; background: #08090d; color: #e2e8f0; margin: 0; padding: 20px; font-size: 13px; }
    .container { max-width: 720px; margin: 0 auto; }
    .header { padding: 14px 18px; background: #0d1017; border-radius: 6px; margin-bottom: 16px; border: 1px solid #1e293b; border-left: 4px solid #2563eb; }
    h1 { margin: 0; color: #ffffff; font-size: 16px; }
    .status { color: #10b981; font-size: 12px; margin-top: 4px; }
    .card { background: #0d1017; padding: 16px; border-radius: 6px; margin-bottom: 16px; border: 1px solid #191e2b; }
    .card h2 { margin-top: 0; color: #60a5fa; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }
    #console { background: #050608; color: #38bdf8; font-family: inherit; padding: 12px; border-radius: 4px; height: 240px; overflow-y: auto; white-space: pre-wrap; font-size: 12px; border: 1px solid #191e2b; }
    .btn { background: #2563eb; color: #ffffff; border: 1px solid #3b82f6; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 600; font-size: 12px; }
    .btn:hover { background: #1d4ed8; }
    input[type=file] { margin: 10px 0; font-size: 12px; color: #94a3b8; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>SensorLang — ESP32 Node Controller</h1>
      <div class="status">● Firmware Activo | Conexión WiFi & Servidor Web OTA</div>
    </div>
    <div class="card">
      <h2>Telemetría en Vivo (mostrar / alerta)</h2>
      <div id="console">Estableciendo flujo de datos...</div>
    </div>
    <div class="card">
      <h2>Actualización Inalámbrica de Firmware (OTA)</h2>
      <p style="font-size: 11px; color: #64748b;">Selecciona el archivo binario compilado <b>.bin</b> para flashear la memoria flash vía WiFi sin cables.</p>
      <form method="POST" action="/update" enctype="multipart/form-data">
        <input type="file" name="update" accept=".bin" required><br>
        <button type="submit" class="btn">Subir Firmware OTA</button>
      </form>
    </div>
  </div>
  <script>
    async function actualizarTelemetria() {
      try {
        const res = await fetch('/telemetria');
        if (res.ok) {
          const texto = await res.text();
          const cons = document.getElementById('console');
          if (texto.trim().length > 0) {
            cons.textContent = texto;
            cons.scrollTop = cons.scrollHeight;
          }
        }
      } catch (e) {}
    }
    setInterval(actualizarTelemetria, 800);
    actualizarTelemetria();
  </script>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", INDEX_HTML);
}

void handleTelemetria() {
  String salida = "";
  int inicio = (logCount == LOG_BUFFER_SIZE) ? logHead : 0;
  for (int i = 0; i < logCount; i++) {
    int idx = (inicio + i) % LOG_BUFFER_SIZE;
    salida += logBuffer[idx] + "\n";
  }
  server.send(200, "text/plain", salida);
}

void handleUpdate() {
  server.sendHeader("Connection", "close");
  server.send(200, "text/plain", (Update.hasError()) ? "FAIL" : "OK");
  ESP.restart();
}

void handleUpdateUpload() {
  HTTPUpload& upload = server.upload();
  if (upload.status == UPLOAD_FILE_START) {
    Serial.printf("Inicio OTA: %s\n", upload.filename.c_str());
    if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
      Update.printError(Serial);
    }
  } else if (upload.status == UPLOAD_FILE_WRITE) {
    if (Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
      Update.printError(Serial);
    }
  } else if (upload.status == UPLOAD_FILE_END) {
    if (Update.end(true)) {
      Serial.printf("OTA Exitoso: %u bytes escritos\n", upload.totalSize);
    } else {
      Update.printError(Serial);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.println("\n--- Iniciando Firmware SensorLang ESP32 ---");

  pinMode(led, OUTPUT);


  // Configuración de Conectividad WiFi
  const char* ssidConfig = "TestNet";
  const char* passConfig = "12345678";

  if (strlen(ssidConfig) > 0) {
    Serial.printf("Conectando a red WiFi: %s ...\n", ssidConfig);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssidConfig, passConfig);

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 20) {
      delay(500);
      Serial.print(".");
      intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi Conectado!");
      Serial.print("Dirección IP asignada: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("\nFallo al conectar como cliente WiFi. Levantando Punto de Acceso (AP)...");
      WiFi.mode(WIFI_AP);
      WiFi.softAP("SensorLang-ESP32", "12345678");
      Serial.print("Punto de Acceso iniciado. IP: ");
      Serial.println(WiFi.softAPIP());
    }
  } else {
    // Modo Punto de Acceso Autónomo (AP) por defecto
    WiFi.mode(WIFI_AP);
    WiFi.softAP("SensorLang-ESP32", "12345678");
    Serial.println("Punto de Acceso 'SensorLang-ESP32' activo (Clave: 12345678)");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.softAPIP());
  }

  // Configurar rutas del Servidor Web
  server.on("/", HTTP_GET, handleRoot);
  server.on("/telemetria", HTTP_GET, handleTelemetria);
  server.on("/update", HTTP_POST, handleUpdate, handleUpdateUpload);
  server.begin();
  Serial.println("Servidor Web HTTP activo en el puerto 80.");
}

void loop() {
  server.handleClient();

  digitalWrite(led, HIGH);

}

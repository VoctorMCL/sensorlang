// Prueba de actuadores digitales (LED) en ESP32
pin led = 2;

encender(led);
alerta("LED encendido");
esperar(1000);

apagar(led);
alerta("LED apagado");
esperar(1000);

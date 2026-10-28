// Control de temperatura con sensor analógico y alerta
pin led_alerta = 2;
pin sensor_temp = A1;

temperatura = leer_analogo(sensor_temp);
mostrar(temperatura);

si (temperatura > 650) {
    encender(led_alerta);
    alerta("¡Alerta de calor! Temperatura superior a 650");
} sino {
    apagar(led_alerta);
}

esperar(400);

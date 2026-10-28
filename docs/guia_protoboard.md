# Guía de Armado en Protoboard Compacta (400 / 430 Puntos, 30 Filas)
## Conexión de Sensores de 4 Pines (AO-DO-GND-VCC y VCC-DATA-NC-GND) con ESP32

Esta guía técnica describe el conexionado físico orificio por orificio para armar circuitos con el microcontrolador ESP32 y sensores de 4 pines en una protoboard compacta de 30 filas.

---

## 1. Sistema de Coordenadas de la Protoboard (Orientación Espejo)

Con la protoboard orientada horizontalmente frente a ti:

```text
[Arriba-Izquierda: 30a]   =========================   [Arriba-Derecha: 1a]
       Columna a-e        (Canal Central Divisor)          Columna a-e
-------------------------------------------------------------------------
       Columna f-j        (Canal Central Divisor)          Columna f-j
[Abajo-Izquierda: 30j]    =========================   [Abajo-Derecha: 1j]
```

* **Fila 30:** Extremo izquierdo de la protoboard.
* **Fila 1:** Extremo derecho de la protoboard.
* **Columnas `a`, `b`, `c`, `d`, `e`:** Banco superior (conectadas eléctricamente entre sí a lo largo de cada fila numérica).
* **Canal central:** Aislamiento físico que divide los bancos superior e inferior.
* **Columnas `f`, `g`, `h`, `i`, `j`:** Banco inferior (conectadas eléctricamente entre sí a lo largo de cada fila numérica).

### Distribución de Componentes:
* **Mitad Izquierda (Filas 20 a 23):** Sensor de 4 pines en columna `c`.
* **Mitad Derecha (Filas 5, 6 y 8):** LED de 5mm y resistencia de 220 Ω en columnas `c` y `d`.
* **Superficie de Trabajo (Frente a la Proto):** Módulo ESP32 DevKit, facilitando el ruteo directo de cables jumpers sin cruces desordenados.

---

## 2. Regla Crítica de Seguridad: Prevención de Sobrecorriente y Bucle Brownout

> [!CAUTION]
> **Prevención de cortocircuito en la resistencia limitadora:**
> Si ambas patas de la resistencia de 220 Ω se insertan en la **misma fila** (por ejemplo, pata 1 en `6c` y pata 2 en `6d`), la resistencia queda puenteada internamente en corto circuito:
> 1. El LED recibe corriente directa sin limitación desde el pin de 3.3V.
> 2. El regulador de voltaje AMS1117 del ESP32 se sobrecalienta inmediatamente y huele a quemado.
> 3. La caída de tensión induce un **Brownout Reset continuo** (~10 reinicios por segundo), produciendo un parpadeo acelerado y anómalo en los LEDs de la placa.
>
> **Regla de montaje:**
> * Pata 1 de la resistencia en **`6d`** (conectada al cátodo del LED).
> * Pata 2 de la resistencia en **`8d`** (conectada a GND en la fila 8).

---

## 3. Configuración A: Sensor de Aire / Gas (4 Pines: AO, DO, GND, VCC)

Aplica a sensores analógicos de gas y calidad de aire (serie MQ-2, MQ-135, MQ-7, etc.):
* **`AO` (Analog Output):** Salida de voltaje variable proporcional a la concentración leída por `leer_analogo(...)`.
* **`DO` (Digital Output):** Salida del comparador integrado con potenciómetro. **Se deja sin conectar**.
* **`GND`:** Referencia de tierra (0 V).
* **`VCC`:** Alimentación eléctrica (**`VIN` a 5 V** para el filamento calefactor de sensores MQ; o **`3V3`** para sensores de temperatura LM35).

### Mapa de Inserción:

```text
              LADO SUPERIOR (a - e)               CANAL              LADO INFERIOR (f - j)
------------------------------------------------------------------------------------------
Fila 5:   [5b: Jumper a D2]      [5c: Ánodo LED (+)]     |
Fila 6:                          [6c: Cátodo LED (-)]    |  (Unión interna: cátodo + pata 1 R220)
                                 [6d: Pata 1 Resistencia]|
Fila 7:   (Fila vacía de aislamiento)                    |
Fila 8:   [8b: Jumper a GND]     [8d: Pata 2 Resistencia]|  (Salida del resistor hacia tierra)
...
Fila 20:  [20b: Jumper a VN]     [20c: Pin AO (Señal)]   |
Fila 21:                         [21c: Pin DO (Libre)]   |  <-- Fila 21 vacía (sin cable)
Fila 22:  [22b: Jumper a GND]    [22c: Pin GND (Tierra)] |
Fila 23:  [23b: Jumper a VIN]    [23c: Pin VCC (5V/3V3)] |
------------------------------------------------------------------------------------------
```

### Cableado Paso a Paso:
1. **Actuador LED 5mm:**
   * Ánodo (+) [pata larga] $\rightarrow$ **`5c`**.
   * Cátodo (-) [pata corta con chaflán plano] $\rightarrow$ **`6c`**.
   * Resistencia 220 Ω Pata 1 $\rightarrow$ **`6d`**.
   * Resistencia 220 Ω Pata 2 $\rightarrow$ **`8d`**.
   * Cable Jumper desde pin **`D2` (GPIO 2)** del ESP32 $\rightarrow$ **`5b`**.
   * Cable Jumper desde pin **`GND`** del ESP32 $\rightarrow$ **`8b`**.
2. **Sensor MQ:**
   * Pin **`AO`** en **`20c`** $\rightarrow$ Cable desde **`20b`** al pin **`VN` (GPIO 39 / Pin A1)** del ESP32.
   * Pin **`DO`** en **`21c`** $\rightarrow$ **Dejar sin conectar**.
   * Pin **`GND`** en **`22c`** $\rightarrow$ Cable desde **`22b`** a un pin **`GND`** del ESP32.
   * Pin **`VCC`** en **`23c`** $\rightarrow$ Cable desde **`23b`** al pin **`VIN` (5 V)** o **`3V3`** del ESP32.

---

## 4. Configuración B: Sensor de Humedad y Temperatura (4 Pines: VCC, DATA, NC, GND)

Aplica a sensores ambientales de 4 pines (serie DHT11 / DHT22):
* **`VCC`:** Alimentación a **`3V3`** (3.3 V).
* **`DATA`:** Línea de datos digitales bidireccional.
* **`NC` (No Connect):** Pin pasivo sin conexión interna. **Se deja sin conectar**.
* **`GND`:** Referencia de tierra (0 V).

### Mapa de Inserción:

```text
              LADO SUPERIOR (a - e)               CANAL              LADO INFERIOR (f - j)
------------------------------------------------------------------------------------------
Fila 5:   [5b: Jumper a D2]      [5c: Ánodo LED (+)]     |
Fila 6:                          [6c: Cátodo LED (-)]    |
                                 [6d: Pata 1 Resistencia]|
Fila 7:   (Fila vacía de aislamiento)                    |
Fila 8:   [8b: Jumper a GND]     [8d: Pata 2 Resistencia]|
...
Fila 20:  [20b: Jumper a 3V3]    [20c: Pin VCC (3.3V)]   |
Fila 21:  [21b: Jumper a VN]     [21c: Pin DATA (Datos)] |
Fila 22:                         [22c: Pin NC (Libre)]   |  <-- Fila 22 vacía (sin cable)
Fila 23:  [23b: Jumper a GND]    [23c: Pin GND (Tierra)] |
------------------------------------------------------------------------------------------
```

### Cableado Paso a Paso:
1. **Actuador LED 5mm:**
   * Exactamente igual que en la Configuración A (filas `5c`, `6c`, `6d`, `8d`).
2. **Sensor DHT11/22:**
   * Pin **`VCC`** en **`20c`** $\rightarrow$ Cable desde **`20b`** al pin **`3V3`** del ESP32.
   * Pin **`DATA`** en **`21c`** $\rightarrow$ Cable desde **`21b`** al pin **`VN` (GPIO 39 / Pin A1)** del ESP32.
   * Pin **`NC`** en **`22c`** $\rightarrow$ **Dejar sin conectar**.
   * Pin **`GND`** en **`23c`** $\rightarrow$ Cable desde **`23b`** al pin **`GND`** del ESP32.

---

## 5. Tabla de Resumen de Conexiones

| Fila Protoboard | Orificios Usados | Componente Físico | Destino en ESP32 | Función |
| :--- | :--- | :--- | :--- | :--- |
| **Fila 5** | `5b` / `5c` | Ánodo LED (+) | Pin `D2` (GPIO 2) | Control digital de encendido |
| **Fila 6** | `6c` / `6d` | Cátodo LED (-) y Pata 1 R220 | Unión interna fila 6 | Retorno de corriente del LED |
| **Fila 8** | `8b` / `8d` | Pata 2 R220 | Pin `GND` | Conexión de tierra protegida |
| **Fila 20** | `20b` / `20c` | VCC (DHT) / AO (MQ) | Pin `3V3` o Pin `VN` | Alimentación / Señal analógica |
| **Fila 21** | `21b` / `21c` | DATA (DHT) / DO (MQ) | Pin `VN` o *Libre* | Señal de datos / *Sin conectar* |
| **Fila 22** | `22b` / `22c` | NC (DHT) / GND (MQ) | *Libre* o Pin `GND` | *Sin conectar* / Tierra |
| **Fila 23** | `23b` / `23c` | GND (DHT) / VCC (MQ) | Pin `GND` o Pin `VIN` | Tierra / Alimentación 5V |

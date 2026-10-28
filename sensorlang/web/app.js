/**
 * SensorLang Studio — Frontend Engine
 *
 * Módulos integrados:
 * 1. Splitters arrastrables (Left, Right, Bottom) con persistencia en localStorage.
 * 2. Motor 3D Three.js con Protoboard 100% SÓLIDA por debajo (cero huecos),
 *    orientación espejo horizontal (30a Arriba-Izquierda, 1j Abajo-Derecha).
 * 3. Componentes físicos realistas: LED 5mm, Resistencia 220Ω con código de colores,
 *    Sensor intercambiable (DHT11 / MQ gas), ESP32 DevKit y cables jumpers DuPont 3D.
 * 4. Editor de código con numeración de líneas, atajos y compilación SensorLang -> C++.
 * 5. Flasheo inalámbrico WiFi (OTA) y puerto USB serie con detección automática.
 * 6. Telemetría en vivo con gráfico analógico y selector de fuente.
 */

document.addEventListener('DOMContentLoaded', () => {
  initSplitters();
  initEditor();
  initExamples();
  initPorts();
  initTabs();
  initActions();
  initTelemetry();
  init3DViewer();
});

// =========================================================================
// 1. CONSOLA Y LOGS
// =========================================================================
function log(msg, type = 'info') {
  const consoleOutput = document.getElementById('console-output');
  if (!consoleOutput) return;

  const line = document.createElement('div');
  line.className = `term-line term-${type}`;

  const now = new Date();
  const timeStr = [
    String(now.getHours()).padStart(2, '0'),
    String(now.getMinutes()).padStart(2, '0'),
    String(now.getSeconds()).padStart(2, '0')
  ].join(':');

  line.textContent = `[${timeStr}] ${msg}`;
  consoleOutput.appendChild(line);
  consoleOutput.scrollTop = consoleOutput.scrollHeight;
}

function clearConsole() {
  const consoleOutput = document.getElementById('console-output');
  if (consoleOutput) {
    consoleOutput.innerHTML = '';
    log('Consola restablecida.', 'info');
  }
}

// =========================================================================
// 2. SPLITTERS REDIMENSIONABLES (PAREDES ARRASTRABLES)
// =========================================================================
function initSplitters() {
  const workspace = document.getElementById('app-workspace');
  const sidebarLeft = document.getElementById('sidebar-left');
  const resizerLeft = document.getElementById('resizer-left');
  const rightPanel = document.getElementById('right-panel');
  const resizerRight = document.getElementById('resizer-right');
  const bottomConsole = document.getElementById('bottom-console');
  const resizerBottom = document.getElementById('resizer-bottom');

  // Restaurar anchos guardados
  const savedLeft = localStorage.getItem('sl_sidebar_w');
  if (savedLeft && sidebarLeft) sidebarLeft.style.width = `${savedLeft}px`;

  const savedRight = localStorage.getItem('sl_right_w');
  if (savedRight && rightPanel) rightPanel.style.width = `${savedRight}px`;

  const savedBottom = localStorage.getItem('sl_bottom_h');
  if (savedBottom && bottomConsole) bottomConsole.style.height = `${savedBottom}px`;

  const trigger3DResize = () => {
    if (window.onThreeResize) window.onThreeResize();
  };

  // 1. Resizer Izquierdo (Sidebar)
  if (resizerLeft && sidebarLeft && workspace) {
    let isDraggingLeft = false;

    resizerLeft.addEventListener('mousedown', (e) => {
      e.preventDefault();
      isDraggingLeft = true;
      resizerLeft.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDraggingLeft) return;
      const rect = workspace.getBoundingClientRect();
      const newWidth = Math.max(180, Math.min(460, e.clientX - rect.left));
      sidebarLeft.style.width = `${newWidth}px`;
      localStorage.setItem('sl_sidebar_w', newWidth);
      trigger3DResize();
    });

    window.addEventListener('mouseup', () => {
      if (isDraggingLeft) {
        isDraggingLeft = false;
        resizerLeft.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        trigger3DResize();
      }
    });
  }

  // 2. Resizer Derecho (Panel 3D / Pestañas)
  if (resizerRight && rightPanel && workspace) {
    let isDraggingRight = false;

    resizerRight.addEventListener('mousedown', (e) => {
      e.preventDefault();
      isDraggingRight = true;
      resizerRight.classList.add('dragging');
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDraggingRight) return;
      const rect = workspace.getBoundingClientRect();
      const maxWidth = Math.floor(window.innerWidth * 0.68);
      const newWidth = Math.max(300, Math.min(maxWidth, rect.right - e.clientX));
      rightPanel.style.width = `${newWidth}px`;
      localStorage.setItem('sl_right_w', newWidth);
      trigger3DResize();
    });

    window.addEventListener('mouseup', () => {
      if (isDraggingRight) {
        isDraggingRight = false;
        resizerRight.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        trigger3DResize();
      }
    });
  }

  // 3. Resizer Inferior (Consola de Salida)
  if (resizerBottom && bottomConsole) {
    let isDraggingBottom = false;

    resizerBottom.addEventListener('mousedown', (e) => {
      e.preventDefault();
      isDraggingBottom = true;
      resizerBottom.classList.add('dragging');
      document.body.style.cursor = 'row-resize';
      document.body.style.userSelect = 'none';
    });

    window.addEventListener('mousemove', (e) => {
      if (!isDraggingBottom) return;
      const newHeight = Math.max(32, Math.min(500, window.innerHeight - e.clientY));
      bottomConsole.style.height = `${newHeight}px`;
      localStorage.setItem('sl_bottom_h', newHeight);
      trigger3DResize();
    });

    window.addEventListener('mouseup', () => {
      if (isDraggingBottom) {
        isDraggingBottom = false;
        resizerBottom.classList.remove('dragging');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        trigger3DResize();
      }
    });
  }

  window.addEventListener('resize', trigger3DResize);
}

// =========================================================================
// 3. EDITOR DE CÓDIGO
// =========================================================================
function initEditor() {
  const editor = document.getElementById('code-editor');
  const lineNumbers = document.getElementById('line-numbers');
  const cursorPos = document.getElementById('editor-cursor-pos');
  const editorLength = document.getElementById('editor-length');
  const btnLimpiar = document.getElementById('btn-limpiar-codigo');
  const btnLimpiarConsola = document.getElementById('btn-limpiar-consola');

  if (!editor) return;

  function updateLines() {
    const lines = editor.value.split('\n').length;
    let numbers = '';
    for (let i = 1; i <= lines; i++) {
      numbers += i + '\n';
    }
    if (lineNumbers) lineNumbers.textContent = numbers;
    if (editorLength) editorLength.textContent = `${editor.value.length} caracteres`;
  }

  function updateCursor() {
    if (!cursorPos) return;
    const text = editor.value.substring(0, editor.selectionStart);
    const lines = text.split('\n');
    const row = lines.length;
    const col = lines[lines.length - 1].length + 1;
    cursorPos.textContent = `Ln ${row}, Col ${col}`;
  }

  editor.addEventListener('input', updateLines);
  editor.addEventListener('scroll', () => {
    if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
  });
  editor.addEventListener('keyup', updateCursor);
  editor.addEventListener('click', updateCursor);

  // Atajos: Tab (4 espacios), Ctrl+Enter (compilar), Ctrl+S (guardar)
  editor.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      editor.value = editor.value.substring(0, start) + '    ' + editor.value.substring(end);
      editor.selectionStart = editor.selectionEnd = start + 4;
      updateLines();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      const btnCompilar = document.getElementById('btn-compilar');
      if (btnCompilar) btnCompilar.click();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      localStorage.setItem('sl_saved_sketch', editor.value);
      log('Sketch guardado en caché del navegador.', 'ok');
    }
  });

  if (btnLimpiar) {
    btnLimpiar.addEventListener('click', () => {
      if (editor.value.trim() && confirm('¿Deseas vaciar el editor?')) {
        editor.value = '';
        updateLines();
        updateCursor();
        log('Editor vaciado.', 'info');
      }
    });
  }

  if (btnLimpiarConsola) {
    btnLimpiarConsola.addEventListener('click', clearConsole);
  }

  // Cargar sketch guardado o mantener default
  const savedSketch = localStorage.getItem('sl_saved_sketch');
  if (savedSketch && !editor.value.trim()) {
    editor.value = savedSketch;
  }
  updateLines();
  updateCursor();
}

// =========================================================================
// 4. EJEMPLOS Y GESTIÓN DE PUERTOS
// =========================================================================
async function initExamples() {
  const select = document.getElementById('select-ejemplos');
  if (!select) return;

  try {
    const res = await fetch('/api/ejemplos');
    const data = await res.json();
    if (data.ok && Array.isArray(data.ejemplos)) {
      data.ejemplos.forEach((ex) => {
        const opt = document.createElement('option');
        opt.value = ex.archivo;
        opt.textContent = `⚡ ${ex.titulo}`;
        opt.dataset.codigo = ex.codigo;
        select.appendChild(opt);
      });
    }
  } catch (err) {
    log(`Aviso al cargar ejemplos: ${err.message}`, 'warn');
  }

  select.addEventListener('change', () => {
    const opt = select.options[select.selectedIndex];
    if (opt && opt.dataset.codigo) {
      const editor = document.getElementById('code-editor');
      if (editor) {
        editor.value = opt.dataset.codigo;
        editor.dispatchEvent(new Event('input'));
        log(`Ejemplo cargado: ${opt.textContent}`, 'cmd');
      }
    }
  });
}

async function initPorts() {
  const select = document.getElementById('select-puerto');
  const details = document.getElementById('puerto-details');
  const btnRefresh = document.getElementById('btn-refresh-puertos');
  const pillDot = document.getElementById('pill-dot');
  const pillText = document.getElementById('pill-text');

  async function checkPorts() {
    try {
      const res = await fetch('/api/puertos');
      const data = await res.json();

      if (!select) return;
      select.innerHTML = '';

      if (data.ok && Array.isArray(data.puertos) && data.puertos.length > 0) {
        let esp32Found = null;

        data.puertos.forEach((p) => {
          const opt = document.createElement('option');
          opt.value = p.device;
          opt.textContent = `${p.device} — ${p.descripcion}`;
          if (p.es_esp32 && !esp32Found) {
            opt.selected = true;
            esp32Found = p;
          }
          select.appendChild(opt);
        });

        if (esp32Found) {
          if (pillDot) pillDot.className = 'pill-dot connected';
          if (pillText) pillText.textContent = `ESP32 en ${esp32Found.device}`;
          if (details) details.textContent = `Detectado: ${esp32Found.descripcion}`;
        } else {
          if (pillDot) pillDot.className = 'pill-dot';
          if (pillText) pillText.textContent = `${data.puertos.length} puerto(s) USB`;
          if (details) details.textContent = 'Selecciona el puerto de tu ESP32.';
        }
      } else {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = 'Sin puertos serie detectados';
        select.appendChild(opt);

        if (pillDot) pillDot.className = 'pill-dot';
        if (pillText) pillText.textContent = 'Conectar ESP32 (USB)';
        if (details) details.textContent = 'Verifica el cable de datos Micro-USB.';
      }
    } catch (err) {
      if (details) details.textContent = 'Servidor local no responde.';
    }
  }

  if (btnRefresh) {
    btnRefresh.addEventListener('click', checkPorts);
  }
  checkPorts();
  setInterval(checkPorts, 4000);
}

// =========================================================================
// 5. PESTAÑAS (SUB-TABS)
// =========================================================================
function initTabs() {
  const buttons = document.querySelectorAll('.sub-tab-btn');
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      buttons.forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.sub-tab-content').forEach((c) => c.classList.remove('active'));

      btn.classList.add('active');
      const targetId = btn.dataset.tab;
      const targetEl = document.getElementById(targetId);
      if (targetEl) {
        targetEl.classList.add('active');
        if (targetId === 'tab-3d' && window.onThreeResize) {
          setTimeout(window.onThreeResize, 20);
        }
      }
    });
  });
}

// =========================================================================
// 6. ACCIONES: COMPILAR, FLASH OTA, FLASH USB, COPIAR C++
// =========================================================================
function initActions() {
  const btnCompilar = document.getElementById('btn-compilar');
  const btnFlashearWifi = document.getElementById('btn-flashear-wifi');
  const btnFlashearUsb = document.getElementById('btn-flashear-usb');
  const btnCopyCpp = document.getElementById('btn-copy-cpp');

  if (btnCompilar) {
    btnCompilar.addEventListener('click', async () => {
      const codigo = document.getElementById('code-editor').value;
      const ssid = document.getElementById('input-ssid').value;
      const pass = document.getElementById('input-pass').value;

      if (!codigo.trim()) {
        log('Error: El editor está vacío.', 'error');
        return;
      }

      log('Compilando SensorLang a binario C++ ESP32...', 'cmd');
      const statusPill = document.getElementById('console-status');
      if (statusPill) statusPill.textContent = 'Compilando...';

      try {
        const res = await fetch('/api/compilar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            codigo,
            wifi_ssid: ssid,
            wifi_pass: pass,
            verificar_arduino: true
          })
        });
        const data = await res.json();

        if (data.ok) {
          log('Compilación SensorLang completada con éxito.', 'ok');
          const cppView = document.getElementById('cpp-code-view');
          if (cppView) cppView.textContent = data.cpp_codigo;
          if (statusPill) statusPill.textContent = 'Compilado OK';

          if (data.logs_arduino) {
            log(`[Arduino-CLI] ${data.logs_arduino}`, 'info');
          }
        } else {
          log(`Error en compilación: ${data.error || 'Error sintáctico'}`, 'error');
          if (data.logs_arduino) log(data.logs_arduino, 'error');
          if (statusPill) statusPill.textContent = 'Error Compilación';
        }
      } catch (err) {
        log(`Error de comunicación: ${err.message}`, 'error');
        if (statusPill) statusPill.textContent = 'Error de Red';
      }
    });
  }

  if (btnFlashearWifi) {
    btnFlashearWifi.addEventListener('click', async () => {
      const codigo = document.getElementById('code-editor').value;
      const ip = document.getElementById('input-ip').value;
      const ssid = document.getElementById('input-ssid').value;
      const pass = document.getElementById('input-pass').value;

      if (!codigo.trim()) {
        log('Error: Editor vacío.', 'error');
        return;
      }
      if (!ip.trim()) {
        log('Error: Ingresa la dirección IP del ESP32.', 'error');
        return;
      }

      log(`Subiendo firmware OTA vía WiFi a http://${ip}/update...`, 'cmd');
      const statusPill = document.getElementById('console-status');
      if (statusPill) statusPill.textContent = 'OTA Flashing...';

      try {
        const res = await fetch('/api/flashear-wifi', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo, ip, wifi_ssid: ssid, wifi_pass: pass })
        });
        const data = await res.json();

        if (data.ok) {
          log(`Firmware OTA instalado exitosamente en ${ip}. ESP32 reiniciado.`, 'ok');
          if (statusPill) statusPill.textContent = 'OTA OK';
        } else {
          log(`Fallo en flasheo WiFi OTA: ${data.logs || data.error}`, 'error');
          if (statusPill) statusPill.textContent = 'Error OTA';
        }
      } catch (err) {
        log(`Fallo de red en OTA: ${err.message}`, 'error');
        if (statusPill) statusPill.textContent = 'Error Red';
      }
    });
  }

  if (btnFlashearUsb) {
    btnFlashearUsb.addEventListener('click', async () => {
      const codigo = document.getElementById('code-editor').value;
      const puerto = document.getElementById('select-puerto').value;
      const ssid = document.getElementById('input-ssid').value;
      const pass = document.getElementById('input-pass').value;

      if (!codigo.trim()) {
        log('Error: Editor vacío.', 'error');
        return;
      }
      if (!puerto) {
        log('Error: Selecciona un puerto USB conectado.', 'error');
        return;
      }

      log(`Flasheando firmware por USB en puerto ${puerto}...`, 'cmd');
      const statusPill = document.getElementById('console-status');
      if (statusPill) statusPill.textContent = 'USB Flashing...';

      try {
        const res = await fetch('/api/flashear-usb', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo, puerto, wifi_ssid: ssid, wifi_pass: pass })
        });
        const data = await res.json();

        if (data.ok) {
          log(`Flasheo USB completado exitosamente en ${puerto}.`, 'ok');
          if (statusPill) statusPill.textContent = 'USB OK';
        } else {
          log(`Error en flasheo USB: ${data.logs || data.error}`, 'error');
          if (statusPill) statusPill.textContent = 'Error USB';
        }
      } catch (err) {
        log(`Fallo de red en flasheo USB: ${err.message}`, 'error');
        if (statusPill) statusPill.textContent = 'Error Red';
      }
    });
  }

  if (btnCopyCpp) {
    btnCopyCpp.addEventListener('click', () => {
      const cppText = document.getElementById('cpp-code-view').textContent;
      navigator.clipboard.writeText(cppText).then(() => {
        log('Código C++ copiado al portapapeles.', 'info');
      });
    });
  }
}

// =========================================================================
// 7. TELEMETRÍA EN VIVO Y GRÁFICO ANALÓGICO
// =========================================================================
function initTelemetry() {
  const btnToggle = document.getElementById('btn-toggle-telemetria');
  const btnClearChart = document.getElementById('btn-clear-chart');
  const canvas = document.getElementById('chart-canvas');
  const telemVal = document.getElementById('telem-val');
  const telemSub = document.getElementById('telem-sub');
  const telemState = document.getElementById('telem-state');
  const telemUptime = document.getElementById('telem-uptime');

  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let isRunning = false;
  let pollInterval = null;
  const history = [];
  const maxSamples = 80;
  let startTime = Date.now();

  function drawChart() {
    const w = canvas.width;
    const h = canvas.height;

    // Fondo oscuro técnico
    ctx.fillStyle = '#06070a';
    ctx.fillRect(0, 0, w, h);

    // Rejilla de fondo
    ctx.strokeStyle = '#151922';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x < w; x += 40) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = 0; y < h; y += 30) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    if (history.length < 2) return;

    // Escalar datos entre 0 y 1023 (o 4095 de ADC de ESP32)
    const maxVal = Math.max(1000, ...history.map((d) => d.val));
    const minVal = Math.min(0, ...history.map((d) => d.val));
    const range = (maxVal - minVal) || 1;

    // Trazar línea de señal
    ctx.strokeStyle = '#2563eb';
    ctx.lineWidth = 2;
    ctx.beginPath();

    history.forEach((pt, i) => {
      const x = (i / (maxSamples - 1)) * w;
      const normalized = (pt.val - minVal) / range;
      const y = h - (normalized * (h - 20) + 10);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Relleno gradiente bajo la curva
    ctx.lineTo((history.length - 1) / (maxSamples - 1) * w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(37, 99, 235, 0.25)');
    grad.addColorStop(1, 'rgba(37, 99, 235, 0.0)');
    ctx.fillStyle = grad;
    ctx.fill();

    // Punto actual
    const lastPt = history[history.length - 1];
    const lastX = ((history.length - 1) / (maxSamples - 1)) * w;
    const lastNorm = (lastPt.val - minVal) / range;
    const lastY = h - (lastNorm * (h - 20) + 10);

    ctx.fillStyle = '#60a5fa';
    ctx.beginPath();
    ctx.arc(lastX, lastY, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  async function pollData() {
    const src = document.querySelector('input[name="telem-src"]:checked')?.value || 'wifi';
    const ip = document.getElementById('input-ip')?.value || '192.168.4.1';
    const puerto = document.getElementById('select-puerto')?.value || '';

    try {
      const res = await fetch(`/api/telemetria?origen=${src}&ip=${encodeURIComponent(ip)}&puerto=${encodeURIComponent(puerto)}`);
      const data = await res.json();

      let val = null;
      let estado = 'NORMAL';

      if (data.ok && data.datos) {
        val = data.datos.valor ?? data.datos.adc ?? Math.floor(Math.random() * 400 + 350);
        estado = data.datos.estado || (val > 600 ? 'ALERTA' : 'NORMAL');
      } else {
        // Modo simulación suave si el dispositivo está desconectado
        const last = history.length > 0 ? history[history.length - 1].val : 420;
        val = Math.max(100, Math.min(900, Math.round(last + (Math.random() * 30 - 15))));
        estado = val > 650 ? 'ALERTA' : 'NORMAL';
      }

      history.push({ t: Date.now(), val });
      if (history.length > maxSamples) history.shift();

      if (telemVal) telemVal.textContent = val;
      if (telemSub) telemSub.textContent = `Vcc ~ 3.3V | ADC: ${val}`;
      if (telemState) {
        telemState.textContent = estado;
        telemState.className = estado === 'ALERTA' ? 'metric-state state-alert' : 'metric-state state-normal';
      }

      const elapsedSec = Math.floor((Date.now() - startTime) / 1000);
      if (telemUptime) telemUptime.textContent = `Uptime: ${elapsedSec}s`;

      drawChart();
    } catch (err) {
      // Ignorar fallas silenciosas en polling
    }
  }

  if (btnToggle) {
    btnToggle.addEventListener('click', () => {
      isRunning = !isRunning;
      if (isRunning) {
        startTime = Date.now();
        btnToggle.textContent = '⏹ Detener Monitoreo';
        btnToggle.style.borderColor = '#ef4444';
        btnToggle.style.color = '#f87171';
        log('Flujo de telemetría iniciado.', 'info');
        pollInterval = setInterval(pollData, 350);
      } else {
        clearInterval(pollInterval);
        btnToggle.textContent = '▶ Iniciar Monitoreo';
        btnToggle.style.borderColor = '';
        btnToggle.style.color = '';
        log('Flujo de telemetría detenido.', 'info');
      }
    });
  }

  if (btnClearChart) {
    btnClearChart.addEventListener('click', () => {
      history.length = 0;
      drawChart();
    });
  }

  drawChart();
}

// =========================================================================
// 8. MOTOR 3D THREE.JS — PROTOBOARD SÓLIDA POR DEBAJO (NO HUECA)
//    Y COORDENADAS CON ESPEJO HORIZONTAL: 30a ARRIBA-IZQ, 1j ABAJO-DER
// =========================================================================
function init3DViewer() {
  const container = document.getElementById('three-container');
  if (!container || typeof THREE === 'undefined') {
    console.warn('Three.js o contenedor 3D no encontrado.');
    return;
  }

  // Dimensiones físicas de la protoboard (en unidades de Three.js)
  // 30 filas x 10 orificios + 2 pares de rieles de alimentación
  const PITCH = 0.8;
  const BOARD_W = 30 * PITCH + 2.4; // ~26.4
  const BOARD_D = 13.6;             // Profundidad Z
  const BOARD_H = 1.4;              // Espesor Y

  // 1. ESCENA, CÁMARA Y RENDERER
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x090a0f);

  const camera = new THREE.PerspectiveCamera(
    42,
    container.clientWidth / (container.clientHeight || 1),
    0.1,
    1000
  );
  camera.position.set(0, 22, 24);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(container.clientWidth, container.clientHeight);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);

  // 2. ORBIT CONTROLS
  let controls = null;
  if (THREE.OrbitControls) {
    controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.minDistance = 6;
    controls.maxDistance = 75;
    controls.target.set(0, 0, 1.5);
  }

  // 3. ILUMINACIÓN MULTI-ÁNGULO (INCLUYE REBOTE INFERIOR PARA BASE SÓLIDA)
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xffffff, 0.85);
  mainLight.position.set(16, 26, 18);
  mainLight.castShadow = true;
  mainLight.shadow.mapSize.width = 1024;
  mainLight.shadow.mapSize.height = 1024;
  scene.add(mainLight);

  const fillLight = new THREE.DirectionalLight(0x93c5fd, 0.35);
  fillLight.position.set(-18, 14, -14);
  scene.add(fillLight);

  // Luz inferior para iluminar la cinta adhesiva cuando el usuario mira por debajo
  const bottomBounceLight = new THREE.DirectionalLight(0xf5ede0, 0.45);
  bottomBounceLight.position.set(0, -22, 0);
  scene.add(bottomBounceLight);

  // 4. MESA DE TRABAJO TÉCNICA (GROUND PLANE)
  const groundGeo = new THREE.PlaneGeometry(65, 50);
  const groundMat = new THREE.MeshStandardMaterial({
    color: 0x0c0e14,
    roughness: 0.92,
    metalness: 0.08
  });
  const ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -BOARD_H / 2 - 0.02;
  ground.receiveShadow = true;
  scene.add(ground);

  // Rejilla métrica sobre la mesa
  const gridHelper = new THREE.GridHelper(60, 60, 0x1d283a, 0x131924);
  gridHelper.position.y = -BOARD_H / 2 - 0.01;
  scene.add(gridHelper);

  // 5. MAPEO DE COORDENADAS: 30a ARRIBA-IZQ, 1j ABAJO-DER
  // row: 1 a 30 (30 está a la izquierda X < 0, 1 a la derecha X > 0)
  // col: 'a' a 'e' (arriba Z < 0), canal Z=0, 'f' a 'j' (abajo Z > 0)
  function getHolePos(row, col) {
    const x = (15.5 - row) * PITCH; // row 30 -> -11.6 (Izq), row 1 -> +11.6 (Der)
    let z = 0;
    const colMap = {
      'a': -3.3,
      'b': -2.5,
      'c': -1.7,
      'd': -0.9,
      'e': -0.22,
      'f': 0.22,
      'g': 0.9,
      'h': 1.7,
      'i': 2.5,
      'j': 3.3,
      '+t': -4.6,
      '-t': -5.4,
      '+b': 4.6,
      '-b': 5.4
    };
    if (colMap[col] !== undefined) {
      z = colMap[col];
    }
    const y = BOARD_H / 2;
    return new THREE.Vector3(x, y, z);
  }

  // 6. GENERACIÓN PROCEDURAL DE TEXTURAS PARA LA PROTOBOARD SÓLIDA

  // A) Textura Superior (Plástico ABS, serigrafía 30a -> 1j, orificios)
  function createTopTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 2048;
    canvas.height = 1024;
    const ctx = canvas.getContext('2d');

    // Fondo plástico ABS marfil
    ctx.fillStyle = '#f5f2e9';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Borde exterior
    ctx.strokeStyle = '#dedad0';
    ctx.lineWidth = 12;
    ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);

    // Canal central (hendidura oscura)
    ctx.fillStyle = '#dbd6c7';
    ctx.fillRect(80, canvas.height / 2 - 22, canvas.width - 160, 44);
    ctx.fillStyle = '#9c9582';
    ctx.fillRect(90, canvas.height / 2 - 6, canvas.width - 180, 12);

    // Líneas de rieles de alimentación
    // Superior: Azul (-) y Roja (+)
    ctx.fillStyle = '#dc2626'; // Roja (+)
    ctx.fillRect(100, 75, canvas.width - 200, 10);
    ctx.fillStyle = '#2563eb'; // Azul (-)
    ctx.fillRect(100, 155, canvas.width - 200, 10);

    // Inferior: Roja (+) y Azul (-)
    ctx.fillStyle = '#dc2626'; // Roja (+)
    ctx.fillRect(100, canvas.height - 165, canvas.width - 200, 10);
    ctx.fillStyle = '#2563eb'; // Azul (-)
    ctx.fillRect(100, canvas.height - 85, canvas.width - 200, 10);

    // Símbolos + y -
    ctx.font = 'bold 36px monospace';
    ctx.fillStyle = '#dc2626';
    ctx.fillText('+', 50, 86);
    ctx.fillText('+', canvas.width - 70, 86);
    ctx.fillText('+', 50, canvas.height - 154);
    ctx.fillText('+', canvas.width - 70, canvas.height - 154);

    ctx.fillStyle = '#2563eb';
    ctx.fillText('−', 50, 166);
    ctx.fillText('−', canvas.width - 70, 166);
    ctx.fillText('−', 50, canvas.height - 74);
    ctx.fillText('−', canvas.width - 70, canvas.height - 74);

    // Letras de columnas (a, b, c, d, e / f, g, h, i, j)
    ctx.font = 'bold 22px monospace';
    ctx.fillStyle = '#64748b';
    const colsTop = ['a', 'b', 'c', 'd', 'e'];
    const colsBot = ['f', 'g', 'h', 'i', 'j'];

    colsTop.forEach((l, idx) => {
      const y = 235 + idx * 52;
      ctx.fillText(l, 55, y + 8);
      ctx.fillText(l, canvas.width - 75, y + 8);
    });

    colsBot.forEach((l, idx) => {
      const y = canvas.height / 2 + 58 + idx * 52;
      ctx.fillText(l, 55, y + 8);
      ctx.fillText(l, canvas.width - 75, y + 8);
    });

    // Números de fila: 30 a la Izquierda, 1 a la Derecha (Espejo Horizontal)
    ctx.font = 'bold 20px monospace';
    ctx.textAlign = 'center';
    for (let r = 1; r <= 30; r++) {
      // Posición X en canvas: row 30 está cerca de X=120, row 1 cerca de canvas.width - 120
      const normX = (30 - r) / 29;
      const x = 125 + normX * (canvas.width - 250);

      if (r % 5 === 0 || r === 1) {
        ctx.fillStyle = '#475569';
        ctx.fillText(String(r), x, 205);
        ctx.fillText(String(r), x, canvas.height - 185);
      }

      // Dibujar orificios (cuadritos con contacto metálico interno)
      // Filas a-e
      for (let c = 0; c < 5; c++) {
        const y = 235 + c * 52;
        drawHole(ctx, x, y);
      }
      // Filas f-j
      for (let c = 0; c < 5; c++) {
        const y = canvas.height / 2 + 58 + c * 52;
        drawHole(ctx, x, y);
      }

      // Orificios rieles
      drawHole(ctx, x, 75);
      drawHole(ctx, x, 155);
      drawHole(ctx, x, canvas.height - 165);
      drawHole(ctx, x, canvas.height - 85);
    }

    function drawHole(c, x, y) {
      c.fillStyle = '#1c1f26';
      c.fillRect(x - 9, y - 9, 18, 18);
      c.fillStyle = '#b45309'; // Lámina de bronce interna
      c.fillRect(x - 4, y - 4, 8, 8);
      c.strokeStyle = '#cbd5e1';
      c.lineWidth = 2;
      c.strokeRect(x - 9, y - 9, 18, 18);
    }

    const tex = new THREE.CanvasTexture(canvas);
    tex.anisotropy = 4;
    return tex;
  }

  // B) Textura Inferior: CINTA ADHESIVA DE DOBLE CONTACTO SÓLIDA
  // Soluciona completamente el detalle de que "estaba hueco por debajo"
  function createBottomTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 1024;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    // Espuma de montaje autoadhesiva color arena / marfil tostado
    ctx.fillStyle = '#dfd6c0';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Tira central de protección desprendible (liner rojo de cinta 3M)
    ctx.fillStyle = '#b91c1c';
    ctx.fillRect(40, canvas.height / 2 - 40, canvas.width - 80, 80);

    // Texto técnico impreso sobre la cinta protectora
    ctx.font = 'bold 24px monospace';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText('PEEL OFF ADHESIVE FOAM TAPE — SENSORLANG ESP32 LAB', canvas.width / 2, canvas.height / 2 - 8);
    ctx.font = '16px monospace';
    ctx.fillStyle = '#fee2e2';
    ctx.fillText('DOUBLE COATED TISSUE TAPE • 430/480 POINTS COMPACT', canvas.width / 2, canvas.height / 2 + 20);

    // Cuadrícula sutil de corte en la espuma
    ctx.strokeStyle = '#c8bc9f';
    ctx.lineWidth = 1;
    for (let x = 0; x < canvas.width; x += 32) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y < canvas.height; y += 32) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }

    // 4 Patitas de goma antideslizante en las esquinas
    const pads = [
      [45, 45],
      [canvas.width - 45, 45],
      [45, canvas.height - 45],
      [canvas.width - 45, canvas.height - 45]
    ];
    pads.forEach(([px, py]) => {
      ctx.fillStyle = '#111827';
      ctx.beginPath();
      ctx.arc(px, py, 26, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = '#374151';
      ctx.lineWidth = 3;
      ctx.stroke();
    });

    const tex = new THREE.CanvasTexture(canvas);
    return tex;
  }

  // C) Textura Lateral (Plástico ABS con pestañas de ensamble)
  function createSideTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = '#e8e4d8';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#d0cbc0';
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, canvas.width - 4, canvas.height - 4);
    return new THREE.CanvasTexture(canvas);
  }

  // 7. CONSTRUCCIÓN DEL BLOQUE SÓLIDO DE LA PROTOBOARD (6 CARAS SELLADAS)
  const topTexture = createTopTexture();
  const bottomTexture = createBottomTexture();
  const sideTexture = createSideTexture();

  const boardMaterials = [
    new THREE.MeshStandardMaterial({ map: sideTexture, roughness: 0.6 }),   // Derecha (+X)
    new THREE.MeshStandardMaterial({ map: sideTexture, roughness: 0.6 }),   // Izquierda (-X)
    new THREE.MeshStandardMaterial({ map: topTexture, roughness: 0.35, metalness: 0.05 }), // Superior (+Y)
    new THREE.MeshStandardMaterial({ map: bottomTexture, roughness: 0.85, metalness: 0.02 }), // INFERIOR (-Y) SÓLIDA
    new THREE.MeshStandardMaterial({ map: sideTexture, roughness: 0.6 }),   // Frontal (+Z)
    new THREE.MeshStandardMaterial({ map: sideTexture, roughness: 0.6 })    // Trasera (-Z)
  ];

  const boardGeometry = new THREE.BoxGeometry(BOARD_W, BOARD_H, BOARD_D, 1, 1, 1);
  const breadboardMesh = new THREE.Mesh(boardGeometry, boardMaterials);
  breadboardMesh.castShadow = true;
  breadboardMesh.receiveShadow = true;
  scene.add(breadboardMesh);

  // 8. GRUPO DE COMPONENTES INTERACTIVOS
  const componentsGroup = new THREE.Group();
  scene.add(componentsGroup);

  // Material metálico para patas de componentes y soldaduras
  const wireMat = new THREE.MeshStandardMaterial({
    color: 0x94a3b8,
    metalness: 0.95,
    roughness: 0.25
  });

  // A) LED 5mm en Filas 5c (Ánodo +) y 6c (Cátodo -)
  const ledGroup = new THREE.Group();
  ledGroup.name = 'step_led';

  const pos5c = getHolePos(5, 'c');
  const pos6c = getHolePos(6, 'c');
  const ledCenter = new THREE.Vector3().addVectors(pos5c, pos6c).multiplyScalar(0.5);

  // Cuello del LED con reborde plano en el cátodo (fila 6)
  const ledCollarGeo = new THREE.CylinderGeometry(0.48, 0.48, 0.16, 24);
  const ledEpoxyMat = new THREE.MeshPhysicalMaterial({
    color: 0xd92626,
    emissive: 0x991b1b,
    emissiveIntensity: 0.45,
    roughness: 0.15,
    metalness: 0.1,
    transmission: 0.6,
    opacity: 0.92,
    transparent: true
  });
  const ledCollar = new THREE.Mesh(ledCollarGeo, ledEpoxyMat);
  ledCollar.position.set(ledCenter.x, pos5c.y + 0.8, ledCenter.z);
  ledGroup.add(ledCollar);

  // Cuerpo cilíndrico del domo
  const ledBodyGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.55, 24);
  const ledBody = new THREE.Mesh(ledBodyGeo, ledEpoxyMat);
  ledBody.position.set(ledCenter.x, pos5c.y + 1.15, ledCenter.z);
  ledGroup.add(ledBody);

  // Cúpula esférica del LED
  const ledDomeGeo = new THREE.SphereGeometry(0.42, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2);
  const ledDome = new THREE.Mesh(ledDomeGeo, ledEpoxyMat);
  ledDome.position.set(ledCenter.x, pos5c.y + 1.42, ledCenter.z);
  ledGroup.add(ledDome);

  // Filamento / Yunque interno plateado
  const ledAnvilGeo = new THREE.BoxGeometry(0.12, 0.22, 0.12);
  const anvilMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9 });
  const ledAnvil = new THREE.Mesh(ledAnvilGeo, anvilMat);
  ledAnvil.position.set(ledCenter.x, pos5c.y + 1.15, ledCenter.z);
  ledGroup.add(ledAnvil);

  // Patas de alambre del LED insertándose en 5c y 6c
  function createLedLeg(fromHole) {
    const legGeo = new THREE.CylinderGeometry(0.04, 0.04, 0.85, 12);
    const leg = new THREE.Mesh(legGeo, wireMat);
    leg.position.set(fromHole.x, fromHole.y + 0.42, fromHole.z);
    return leg;
  }
  ledGroup.add(createLedLeg(pos5c));
  ledGroup.add(createLedLeg(pos6c));
  componentsGroup.add(ledGroup);

  // B) Resistencia 220 Ω (1/4 Watt) entre Filas 6d y 8d
  // REGLA CRÍTICA: Pata 1 en 6d (unida al cátodo del LED), Pata 2 en 8d (GND)
  const resGroup = new THREE.Group();
  resGroup.name = 'step_resistor';

  const pos6d = getHolePos(6, 'd');
  const pos8d = getHolePos(8, 'd');
  const resCenter = new THREE.Vector3().addVectors(pos6d, pos8d).multiplyScalar(0.5);

  // Cuerpo cerámico beige
  const resBodyGeo = new THREE.CylinderGeometry(0.24, 0.24, 1.15, 20);
  const resBodyMat = new THREE.MeshStandardMaterial({ color: 0xd8c89d, roughness: 0.5 });
  const resBody = new THREE.Mesh(resBodyGeo, resBodyMat);
  resBody.rotation.z = Math.PI / 2;
  resBody.position.set(resCenter.x, pos6d.y + 0.65, resCenter.z);
  resGroup.add(resBody);

  // 4 Bandas de color (220 Ω ±5% -> Rojo, Rojo, Marrón, Dorado)
  const bandColors = [0xdc2626, 0xdc2626, 0x78350f, 0xeab308];
  const bandOffsets = [-0.34, -0.12, 0.1, 0.35];
  bandColors.forEach((col, idx) => {
    const bandGeo = new THREE.CylinderGeometry(0.25, 0.25, 0.1, 20);
    const bandMat = new THREE.MeshStandardMaterial({ color: col, roughness: 0.35 });
    const band = new THREE.Mesh(bandGeo, bandMat);
    band.rotation.z = Math.PI / 2;
    band.position.set(resCenter.x + bandOffsets[idx], pos6d.y + 0.65, resCenter.z);
    resGroup.add(band);
  });

  // Patas de alambre dobladas a 90 grados
  function createBentLeg(holePos, sign) {
    const legCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(holePos.x, holePos.y, holePos.z),
      new THREE.Vector3(holePos.x, holePos.y + 0.65, holePos.z),
      new THREE.Vector3(resCenter.x + sign * 0.58, pos6d.y + 0.65, resCenter.z)
    ]);
    const legGeo = new THREE.TubeGeometry(legCurve, 16, 0.04, 8, false);
    return new THREE.Mesh(legGeo, wireMat);
  }
  resGroup.add(createBentLeg(pos6d, 1));
  resGroup.add(createBentLeg(pos8d, -1));
  componentsGroup.add(resGroup);

  // C) Sensor Intercambiable (DHT11 vs MQ) en Filas 20c, 21c, 22c, 23c
  const sensorGroup = new THREE.Group();
  sensorGroup.name = 'step_sensor';

  let dhtMeshGroup = new THREE.Group();
  let mqMeshGroup = new THREE.Group();

  function buildSensors() {
    // Orificios del sensor: 20c a 23c
    const p20c = getHolePos(20, 'c');
    const p21c = getHolePos(21, 'c');
    const p22c = getHolePos(22, 'c');
    const p23c = getHolePos(23, 'c');

    const sensorCenterX = (p20c.x + p23c.x) / 2;
    const sensorCenterZ = p20c.z;

    // --- 1. SENSOR DHT11 ---
    dhtMeshGroup = new THREE.Group();

    // PCB de soporte azul
    const pcbGeo = new THREE.BoxGeometry(3.6, 0.16, 2.0);
    const pcbMat = new THREE.MeshStandardMaterial({ color: 0x1e3a8a, roughness: 0.4 });
    const pcb = new THREE.Mesh(pcbGeo, pcbMat);
    pcb.position.set(sensorCenterX, p20c.y + 0.8, sensorCenterZ);
    dhtMeshGroup.add(pcb);

    // Carcasa plástica azul con rejillas de ventilación
    const dhtCaseGeo = new THREE.BoxGeometry(2.4, 2.2, 1.4);
    const dhtCaseMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.3 });
    const dhtCase = new THREE.Mesh(dhtCaseGeo, dhtCaseMat);
    dhtCase.position.set(sensorCenterX, p20c.y + 1.95, sensorCenterZ);
    dhtMeshGroup.add(dhtCase);

    // Ranuras de ventilación
    for (let s = -0.6; s <= 0.6; s += 0.3) {
      const slotGeo = new THREE.BoxGeometry(1.6, 0.08, 0.1);
      const slotMat = new THREE.MeshStandardMaterial({ color: 0x0369a1 });
      const slot = new THREE.Mesh(slotGeo, slotMat);
      slot.position.set(sensorCenterX, p20c.y + 2.0 + s, sensorCenterZ + 0.71);
      dhtMeshGroup.add(slot);
    }

    // 4 Pines dorados hacia abajo
    [p20c, p21c, p22c, p23c].forEach((pt) => {
      const pinGeo = new THREE.BoxGeometry(0.08, 0.8, 0.08);
      const pinMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.9 });
      const pin = new THREE.Mesh(pinGeo, pinMat);
      pin.position.set(pt.x, pt.y + 0.4, pt.z);
      dhtMeshGroup.add(pin);
    });

    // --- 2. SENSOR MQ (GAS / CALIDAD DE AIRE) ---
    mqMeshGroup = new THREE.Group();

    // PCB rectangular azul
    const mqPcb = new THREE.Mesh(pcbGeo, pcbMat);
    mqPcb.position.set(sensorCenterX, p20c.y + 0.8, sensorCenterZ);
    mqMeshGroup.add(mqPcb);

    // Cilindro de malla metálica de acero
    const mqCylGeo = new THREE.CylinderGeometry(0.75, 0.75, 1.6, 24);
    const mqMeshMat = new THREE.MeshStandardMaterial({
      color: 0xcfd6df,
      metalness: 0.95,
      roughness: 0.3
    });
    const mqCyl = new THREE.Mesh(mqCylGeo, mqMeshMat);
    mqCyl.position.set(sensorCenterX, p20c.y + 1.65, sensorCenterZ);
    mqMeshGroup.add(mqCyl);

    // Tapa superior plateada
    const mqCapGeo = new THREE.CylinderGeometry(0.78, 0.78, 0.18, 24);
    const mqCap = new THREE.Mesh(mqCapGeo, mqMeshMat);
    mqCap.position.set(sensorCenterX, p20c.y + 2.45, sensorCenterZ);
    mqMeshGroup.add(mqCap);

    // Trimmer potenciómetro azul en la base
    const potGeo = new THREE.BoxGeometry(0.6, 0.45, 0.6);
    const potMat = new THREE.MeshStandardMaterial({ color: 0x3b82f6 });
    const pot = new THREE.Mesh(potGeo, potMat);
    pot.position.set(sensorCenterX + 1.1, p20c.y + 1.05, sensorCenterZ);
    mqMeshGroup.add(pot);

    // 4 Pines dorados
    [p20c, p21c, p22c, p23c].forEach((pt) => {
      const pinGeo = new THREE.BoxGeometry(0.08, 0.8, 0.08);
      const pinMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.9 });
      const pin = new THREE.Mesh(pinGeo, pinMat);
      pin.position.set(pt.x, pt.y + 0.4, pt.z);
      mqMeshGroup.add(pin);
    });

    sensorGroup.add(dhtMeshGroup);
    sensorGroup.add(mqMeshGroup);
    mqMeshGroup.visible = false; // Por defecto DHT11 activo
  }
  buildSensors();
  componentsGroup.add(sensorGroup);

  // D) ESP32 DevKit en la mesa (frente a la protoboard)
  const espGroup = new THREE.Group();
  espGroup.name = 'step_esp32';

  const espPosX = 0;
  const espPosY = -BOARD_H / 2 + 0.14;
  const espPosZ = 10.2;

  // PCB negro mate del ESP32
  const espPcbGeo = new THREE.BoxGeometry(6.6, 0.2, 3.2);
  const espPcbMat = new THREE.MeshStandardMaterial({ color: 0x111217, roughness: 0.4 });
  const espPcb = new THREE.Mesh(espPcbGeo, espPcbMat);
  espPcb.position.set(espPosX, espPosY, espPosZ);
  espGroup.add(espPcb);

  // Blindaje metálico RF plateado ESP-WROOM-32
  const shieldGeo = new THREE.BoxGeometry(2.4, 0.35, 2.2);
  const shieldMat = new THREE.MeshStandardMaterial({ color: 0xd1d5db, metalness: 0.88, roughness: 0.25 });
  const shield = new THREE.Mesh(shieldGeo, shieldMat);
  shield.position.set(espPosX - 1.2, espPosY + 0.22, espPosZ);
  espGroup.add(shield);

  // Conector Micro-USB metálico
  const usbGeo = new THREE.BoxGeometry(0.85, 0.35, 0.75);
  const usb = new THREE.Mesh(usbGeo, shieldMat);
  usb.position.set(espPosX + 3.1, espPosY + 0.2, espPosZ);
  espGroup.add(usb);

  // Tiras de pines macho a ambos lados
  const headerMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.6 });
  const hTop = new THREE.Mesh(new THREE.BoxGeometry(5.8, 0.4, 0.35), headerMat);
  hTop.position.set(espPosX, espPosY + 0.25, espPosZ - 1.3);
  espGroup.add(hTop);

  const hBot = new THREE.Mesh(new THREE.BoxGeometry(5.8, 0.4, 0.35), headerMat);
  hBot.position.set(espPosX, espPosY + 0.25, espPosZ + 1.3);
  espGroup.add(hBot);

  // Botones táctiles micro EN y BOOT
  [-0.3, 0.3].forEach((off) => {
    const btnMesh = new THREE.Mesh(
      new THREE.BoxGeometry(0.3, 0.3, 0.3),
      new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.9 })
    );
    btnMesh.position.set(espPosX + 2.2, espPosY + 0.25, espPosZ + off);
    espGroup.add(btnMesh);
  });
  componentsGroup.add(espGroup);

  // E) Cables Jumpers DuPont 3D (Curvas naturales de alambre)
  const cablesGroup = new THREE.Group();
  cablesGroup.name = 'step_cables';

  // Coordenadas clave de pines en ESP32
  const espPinD2 = new THREE.Vector3(espPosX + 1.4, espPosY + 0.5, espPosZ - 1.3);
  const espPinGnd = new THREE.Vector3(espPosX + 0.6, espPosY + 0.5, espPosZ - 1.3);
  const espPin3V3 = new THREE.Vector3(espPosX - 0.2, espPosY + 0.5, espPosZ - 1.3);
  const espPinVN = new THREE.Vector3(espPosX - 1.0, espPosY + 0.5, espPosZ - 1.3);

  // Jumpers dinámicos según sensor activo
  let activeJumpers = [];

  function buildJumpers(sensorType) {
    // Limpiar cables anteriores
    while (cablesGroup.children.length > 0) {
      cablesGroup.remove(cablesGroup.children[0]);
    }
    activeJumpers = [];

    // Lista de conexiones:
    // [Origen ESP32, Destino Proto (row, col), Color hex, Altura arco]
    let wireDefs = [];
    if (sensorType === 'DHT') {
      wireDefs = [
        { from: espPinD2, row: 5, col: 'b', color: 0x8b5cf6, h: 4.8 },  // D2 -> 5b (Ánodo LED)
        { from: espPinGnd, row: 8, col: 'b', color: 0x1e293b, h: 4.2 }, // GND -> 8b (Resistencia)
        { from: espPin3V3, row: 20, col: 'b', color: 0xef4444, h: 5.5 },// 3V3 -> 20b (VCC DHT)
        { from: espPinVN, row: 21, col: 'b', color: 0xeab308, h: 5.0 }, // VN -> 21b (DATA DHT)
        { from: espPinGnd, row: 23, col: 'b', color: 0x0f172a, h: 5.8 } // GND -> 23b (GND DHT)
      ];
    } else {
      wireDefs = [
        { from: espPinD2, row: 5, col: 'b', color: 0x8b5cf6, h: 4.8 },  // D2 -> 5b
        { from: espPinGnd, row: 8, col: 'b', color: 0x1e293b, h: 4.2 }, // GND -> 8b
        { from: espPinVN, row: 20, col: 'b', color: 0xeab308, h: 5.5 }, // VN -> 20b (AO MQ)
        { from: espPinGnd, row: 22, col: 'b', color: 0x1e293b, h: 5.0 },// GND -> 22b (GND MQ)
        { from: espPin3V3, row: 23, col: 'b', color: 0xef4444, h: 5.8 } // 3V3 -> 23b (VCC MQ)
      ];
    }

    wireDefs.forEach((def) => {
      const toPos = getHolePos(def.row, def.col);

      // Puntos de control para el arco del cable en el aire
      const midPoint = new THREE.Vector3().addVectors(def.from, toPos).multiplyScalar(0.5);
      midPoint.y += def.h;

      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(def.from.x, def.from.y, def.from.z),
        new THREE.Vector3(def.from.x, def.from.y + 0.8, def.from.z),
        midPoint,
        new THREE.Vector3(toPos.x, toPos.y + 0.9, toPos.z),
        new THREE.Vector3(toPos.x, toPos.y, toPos.z)
      ]);

      const tubeGeo = new THREE.TubeGeometry(curve, 28, 0.08, 8, false);
      const tubeMat = new THREE.MeshStandardMaterial({
        color: def.color,
        roughness: 0.35,
        metalness: 0.1
      });
      const wireMesh = new THREE.Mesh(tubeGeo, tubeMat);
      cablesGroup.add(wireMesh);

      // Capuchón terminal DuPont negro en la protoboard
      const bootGeo = new THREE.BoxGeometry(0.24, 0.65, 0.24);
      const bootMat = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.6 });
      const boot = new THREE.Mesh(bootGeo, bootMat);
      boot.position.set(toPos.x, toPos.y + 0.32, toPos.z);
      cablesGroup.add(boot);

      activeJumpers.push(wireMesh);
    });
  }
  buildJumpers('DHT');
  componentsGroup.add(cablesGroup);

  // 9. CONTROLES DE USUARIO (TOGGLES, CÁMARA, HIGHLIGHTS)

  // Selector DHT / MQ
  const btnToggleDht = document.getElementById('btn-toggle-dht');
  const btnToggleMq = document.getElementById('btn-toggle-mq');
  const descSensorStep = document.getElementById('desc-sensor-step');
  const descCablesStep = document.getElementById('desc-cables-step');

  function setSensor(type) {
    if (type === 'DHT') {
      dhtMeshGroup.visible = true;
      mqMeshGroup.visible = false;
      if (btnToggleDht) btnToggleDht.classList.add('active');
      if (btnToggleMq) btnToggleMq.classList.remove('active');
      if (descSensorStep) descSensorStep.textContent = '20c: VCC | 21c: DATA | 22c: NC vacío | 23c: GND';
      if (descCablesStep) descCablesStep.textContent = 'D2 → 5b | GND → 8b | 3V3 → 20b | VN → 21b | GND → 23b';
      buildJumpers('DHT');
    } else {
      dhtMeshGroup.visible = false;
      mqMeshGroup.visible = true;
      if (btnToggleMq) btnToggleMq.classList.add('active');
      if (btnToggleDht) btnToggleDht.classList.remove('active');
      if (descSensorStep) descSensorStep.textContent = '20c: AO Analógico | 21c: DO Digital | 22c: GND | 23c: VCC';
      if (descCablesStep) descCablesStep.textContent = 'D2 → 5b | GND → 8b | VN → 20b | GND → 22b | 3V3 → 23b';
      buildJumpers('MQ');
    }
  }

  if (btnToggleDht) btnToggleDht.addEventListener('click', () => setSensor('DHT'));
  if (btnToggleMq) btnToggleMq.addEventListener('click', () => setSensor('MQ'));

  // Botones de Cámara: Girar 180° (mira el fondo sólido), Centrar, 2D Plana
  const btnFlip = document.getElementById('btn-3d-flip');
  const btnReset = document.getElementById('btn-3d-reset');
  const btnTop = document.getElementById('btn-3d-top');

  let isFlipped = false;
  if (btnFlip) {
    btnFlip.addEventListener('click', () => {
      isFlipped = !isFlipped;
      if (isFlipped) {
        // Mirar desde ABAJO para inspeccionar la base sólida sin huecos
        camera.position.set(0, -18, 16);
        if (controls) controls.target.set(0, 0, 0);
        btnFlip.textContent = 'Vista Frontal';
      } else {
        camera.position.set(0, 22, 24);
        if (controls) controls.target.set(0, 0, 1.5);
        btnFlip.textContent = 'Girar 180°';
      }
    });
  }

  if (btnReset) {
    btnReset.addEventListener('click', () => {
      isFlipped = false;
      camera.position.set(0, 22, 24);
      if (controls) controls.target.set(0, 0, 1.5);
      if (btnFlip) btnFlip.textContent = 'Girar 180°';
      document.querySelectorAll('.step-card').forEach((c) => c.classList.remove('active'));
      resetComponentHighlights();
    });
  }

  if (btnTop) {
    btnTop.addEventListener('click', () => {
      camera.position.set(0, 36, 0.01);
      if (controls) controls.target.set(0, 0, 0);
    });
  }

  // Resaltado de pasos del checklist interactivo
  const stepCards = document.querySelectorAll('.step-card');
  function resetComponentHighlights() {
    componentsGroup.traverse((obj) => {
      if (obj.isMesh && obj.material) {
        if (obj.material._origEmissive !== undefined) {
          obj.material.emissive.setHex(obj.material._origEmissive);
        }
      }
    });
  }

  stepCards.forEach((card) => {
    card.addEventListener('click', () => {
      const stepName = card.dataset.step;
      const wasActive = card.classList.contains('active');

      stepCards.forEach((c) => c.classList.remove('active'));
      resetComponentHighlights();

      if (!wasActive) {
        card.classList.add('active');
        highlightStep(stepName);
      }
    });
  });

  function highlightStep(stepName) {
    let targetObj = null;
    if (stepName === 'led') targetObj = ledGroup;
    else if (stepName === 'resistor') targetObj = resGroup;
    else if (stepName === 'sensor') targetObj = sensorGroup;
    else if (stepName === 'esp32') targetObj = espGroup;
    else if (stepName === 'cables') targetObj = cablesGroup;

    if (targetObj) {
      targetObj.traverse((obj) => {
        if (obj.isMesh && obj.material && obj.material.emissive) {
          if (obj.material._origEmissive === undefined) {
            obj.material._origEmissive = obj.material.emissive.getHex();
          }
          obj.material.emissive.setHex(0x3b82f6);
        }
      });
      // Mover suavemente la cámara hacia el componente
      const box = new THREE.Box3().setFromObject(targetObj);
      const center = box.getCenter(new THREE.Vector3());
      if (controls) {
        controls.target.lerp(center, 0.8);
      }
    }
  }

  // 10. RESIZE DEL RENDERER THREE.JS (VINCULADO AL SPLITTER)
  window.onThreeResize = function () {
    if (!container || !renderer || !camera) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (w <= 0 || h <= 0) return;

    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h, false);
  };

  // Observador de cambios de tamaño en el contenedor WebGL
  if (window.ResizeObserver) {
    const ro = new ResizeObserver(() => {
      window.onThreeResize();
    });
    ro.observe(container);
  }

  // 11. BUCLE DE ANIMACIÓN CONTINUO
  let frameId = null;
  function animate() {
    frameId = requestAnimationFrame(animate);

    if (controls) controls.update();

    // Efecto sutil de respiración en el LED cuando está activo
    if (ledEpoxyMat && !isFlipped) {
      const pulse = 0.35 + Math.sin(Date.now() * 0.004) * 0.15;
      ledEpoxyMat.emissiveIntensity = pulse;
    }

    renderer.render(scene, camera);
  }
  animate();
}

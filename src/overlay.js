(() => {
  "use strict";
  const API = "http://127.0.0.1:8000";
  const state = document.getElementById("state");
  const label = document.getElementById("state-label");
  const target = document.getElementById("target");
  const targetLabel = document.getElementById("target-label");
  const cursor = document.getElementById("cursor");
  const trail = document.getElementById("trail");
  const points = [];
  let hideTargetTimer = null;
  let lastState = "idle";

  const finite = (n) => Number.isFinite(Number(n)) ? Number(n) : null;
  const coordsFrom = (data) => {
    const t = data && (data.target || data.alvo || data.overlay || data);
    if (!t || typeof t !== "object") return null;
    const rawX = finite(t.target_x ?? t.x ?? t.screen_x);
    const rawY = finite(t.target_y ?? t.y ?? t.screen_y);
    if (rawX === null || rawY === null) return null;
    // OCR/mss coordinates are physical pixels; the WebView uses logical CSS pixels.
    const scale = window.devicePixelRatio || 1;
    return { x: rawX / scale, y: rawY / scale, label: String(t.target_label || t.label || t.descricao || "Alvo").slice(0, 100) };
  };
  function setState(data) {
    const raw = String(data.state || data.estado || data.status || "").toLowerCase();
    let next = "idle";
    if (["running", "executing", "executando", "acao"].includes(raw)) next = "executing";
    else if (["thinking", "observing", "observando", "pensando", "planning"].includes(raw)) next = "thinking";
    else if (["done", "ok", "concluido", "concluído", "success"].includes(raw)) next = "done";
    else if (["error", "erro", "failed", "falha"].includes(raw)) next = "error";
    const tool = String(data.passo_atual || data.tool || data.ferramenta || "").trim();
    label.textContent = next === "executing" ? (tool ? "Executando · " + tool : "MYRA executando")
      : next === "thinking" ? "MYRA observando / pensando"
      : next === "done" ? "Tarefa concluída"
      : next === "error" ? "Tarefa com erro"
      : "MYRA pronta";
    state.dataset.state = next;
    state.classList.toggle("visible", next !== "idle");
    if (next !== lastState) {
      lastState = next;
      if (next === "idle") clearTarget();
    }
    const coords = coordsFrom(data);
    if (coords) showTarget(coords.x, coords.y, coords.label);
    const cursorCoords = data.cursor || data.mouse;
    if (cursorCoords && finite(cursorCoords.x) !== null && finite(cursorCoords.y) !== null) {
      const scale = window.devicePixelRatio || 1;
      moveCursor(Number(cursorCoords.x) / scale, Number(cursorCoords.y) / scale);
    }
  }
  function showTarget(x, y, text) {
    const maxX = window.innerWidth, maxY = window.innerHeight;
    if (x < 0 || y < 0 || x > maxX || y > maxY) return;
    target.style.left = x + "px"; target.style.top = y + "px";
    targetLabel.textContent = text;
    target.hidden = false;
    if (hideTargetTimer) clearTimeout(hideTargetTimer);
    hideTargetTimer = setTimeout(() => { target.hidden = true; }, 2600);
    moveCursor(x, y);
  }
  function moveCursor(x, y) {
    cursor.style.left = x + "px"; cursor.style.top = y + "px";
    cursor.hidden = false;
    points.push([x, y]);
    if (points.length > 24) points.shift();
    const d = points.map((p, i) => (i ? "L" : "M") + p[0] + " " + p[1]).join(" ");
    trail.innerHTML = d ? '<path d="' + d + '"></path>' : "";
  }
  function clearTarget() {
    target.hidden = true; cursor.hidden = true; points.length = 0; trail.replaceChildren();
    if (hideTargetTimer) clearTimeout(hideTargetTimer);
  }
  function connect() {
    const stream = new EventSource(API + "/task_events");
    stream.onmessage = (event) => {
      try { setState(JSON.parse(event.data)); } catch (e) { console.warn("[MYRA overlay] evento invalido", e); }
    };
    stream.onerror = () => { state.dataset.state = "idle"; label.textContent = "Reconectando ao MYRA…"; };
  }
  connect();
  window.addEventListener("resize", () => { trail.setAttribute("viewBox", "0 0 " + innerWidth + " " + innerHeight); });
  console.info("[MYRA overlay] SSE conectado");
})();
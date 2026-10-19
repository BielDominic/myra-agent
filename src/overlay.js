(() => {
  "use strict";
  const API = "http://127.0.0.1:8000";
  const state = document.getElementById("state");
  const label = document.getElementById("state-label");
  const target = document.getElementById("target");
  const targetLabel = document.getElementById("target-label");
  const cursor = document.getElementById("cursor");
  const trail = document.getElementById("trail");
  const activityBorder = document.getElementById("activity-border");
  const activityBanner = document.getElementById("activity-banner");
  const activityText = document.getElementById("activity-text");
  const points = [];
  let hideTargetTimer = null;
  let lastTargetSignature = "";
  let lastState = "idle";

  async function setOverlayVisible(visible) {
    try {
      if (window.__TAURI__ && window.__TAURI__.core) {
        await window.__TAURI__.core.invoke(
          "set_overlay_visible",
          { visible }
        );
      } else {
        console.warn("[MYRA overlay] API Tauri indisponivel");
      }
    } catch (e) {
      console.warn("[MYRA overlay] falha ao alterar visibilidade", e);
    }
  }

  const finite = (n) => Number.isFinite(Number(n)) ? Number(n) : null;
  const coordsFrom = (data) => {
    const t = data && (data.target || data.alvo || data.overlay || data);
    if (!t || typeof t !== "object") return null;
    const rawX = finite(t.target_x ?? t.x ?? t.screen_x);
    const rawY = finite(t.target_y ?? t.y ?? t.screen_y);
    if (rawX === null || rawY === null) return null;
    const scale = window.devicePixelRatio || 1;
    return { x: rawX / scale, y: rawY / scale, label: String(t.target_label || t.label || t.descricao || "Alvo").slice(0, 100) };
  };
  function setState(data) {
    const tool = String(data.passo_atual || data.tool || data.ferramenta || "").trim();
    const active = data.computer_activity === true;
    const next = active
      ? (/observ|pens|planej|verific|analis/i.test(tool) ? "thinking" : "executing")
      : "idle";
    label.textContent = active
      ? (tool ? "MYRA · " + tool.replace(/_/g, " ") : "MYRA interagindo com o computador")
      : "MYRA pronta";
    state.dataset.state = next;
    state.classList.toggle("visible", active);
    if (!active) {
      lastState = "idle";
      clearTarget();
      syncActivityUI("idle", "");
      void setOverlayVisible(false);
      return;
    }
    lastState = next;
    const coords = coordsFrom(data);
    if (coords) {
      const signature = Math.round(coords.x) + "|" + Math.round(coords.y) + "|" + coords.label;
      if (signature !== lastTargetSignature) {
        lastTargetSignature = signature;
        showTarget(coords.x, coords.y, coords.label);
      }
    }
    syncActivityUI(next, tool);
    const cursorCoords = data.cursor || data.mouse;
    if (cursorCoords && finite(cursorCoords.x) !== null && finite(cursorCoords.y) !== null) {
      const scale = window.devicePixelRatio || 1;
      moveCursor(Number(cursorCoords.x) / scale, Number(cursorCoords.y) / scale);
    }
    void setOverlayVisible(true);
  }
  function syncActivityUI(next, tool) {
    const active = next !== "idle";
    if (activityBorder) activityBorder.classList.toggle("active", active);
    if (activityBanner) activityBanner.classList.toggle("active", active);
    if (activityText) {
      activityText.textContent = next === "executing" ? (tool ? "MYRA executando · " + tool : "MYRA executando…")
        : next === "thinking" ? "MYRA observando / pensando…"
        : next === "done" ? "Tarefa concluída ✓"
        : next === "error" ? "Tarefa com erro"
        : "MYRA pronta";
    }
  }

  function showTarget(x, y, text) {
    const maxX = window.innerWidth, maxY = window.innerHeight;
    if (x < 0 || y < 0 || x > maxX || y > maxY) return;
    target.style.left = x + "px"; target.style.top = y + "px";
    targetLabel.textContent = text;
    target.hidden = false;
    void setOverlayVisible(true);
    if (hideTargetTimer) clearTimeout(hideTargetTimer);
    hideTargetTimer = setTimeout(() => {
      target.hidden = true;
      hideTargetTimer = null;
      if (lastState !== "idle") void setOverlayVisible(true);
      else void setOverlayVisible(false);
    }, 2600);
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
    lastTargetSignature = "";
    target.hidden = true; cursor.hidden = true; points.length = 0; trail.replaceChildren();
    if (hideTargetTimer) clearTimeout(hideTargetTimer);
    hideTargetTimer = null;
  }
  function connect() {
    const stream = new EventSource(API + "/task_events");
    stream.onmessage = (event) => {
      try { setState(JSON.parse(event.data)); } catch (e) { console.warn("[MYRA overlay] evento invalido", e); }
    };
    stream.onerror = () => { state.dataset.state = "idle"; state.classList.remove("visible"); label.textContent = "Reconectando ao MYRA..."; lastState = "idle"; clearTarget(); void setOverlayVisible(false); };
  }
  connect();
  window.addEventListener("resize", () => { trail.setAttribute("viewBox", "0 0 " + innerWidth + " " + innerHeight); });
  console.info("[MYRA overlay] SSE conectado");
})();
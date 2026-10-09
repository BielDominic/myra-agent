// ============================================================
// MYRA Widget — Tauri (limpo)
// ============================================================

const invoke = window.__TAURI__.core.invoke;

const IDLE_W = 200, IDLE_H = 44;
const CARD_W = 440, CARD_H = 340;

let lastState = null;
let resetting = false;

async function setWindowSize(state) {
    const w = state === "idle" ? IDLE_W : CARD_W;
    const h = state === "idle" ? IDLE_H : CARD_H;
    try {
        await invoke('resize_window', { width: w, height: h });
    } catch (e) {
        console.error("[RESIZE]", e);
    }
}

function switchView(state) {
    const island = document.getElementById("island");
    if (!island) return;
    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);
    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    const view = document.querySelector(`.view-${state}`);
    if (view) view.classList.add("active");
    setWindowSize(state);
}

async function closeWidget() {
    resetting = true;
    try { await invoke('cancel_task'); } catch (e) { console.error(e); }
    switchView("idle");
    lastState = "idle";
    setTimeout(() => { resetting = false; }, 1200);
}

async function resetWidget() {
    resetting = true;
    try { await invoke('cancel_task'); } catch (e) { console.error(e); }
    switchView("idle");
    lastState = "idle";
    setTimeout(() => { resetting = false; }, 1200);
}

async function cancelTask() {
    resetting = true;
    try { await invoke('cancel_task'); } catch (e) { console.error(e); }
    switchView("idle");
    lastState = "idle";
    setTimeout(() => { resetting = false; }, 1200);
}

async function pollStatus() {
    if (resetting) return;
    try {
        const status = await invoke('get_task_status');
        if (!status) return;
        const state = status.state || "idle";

        if (state !== lastState) {
            console.log(`[POLL] ${lastState} -> ${state}`);
            lastState = state;

            if (state === "running") {
                const tool = document.getElementById("tool-name");
                if (tool && status.passo_atual) tool.textContent = status.passo_atual;
            }
            if (state === "done") {
                const result = document.getElementById("result-text");
                if (result) result.textContent = status.resultado || "(sem resultado)";
            }
            if (state === "error") {
                const err = document.getElementById("error-text");
                if (err) err.textContent = status.erro || "(sem mensagem)";
            }
            switchView(state);
        } else if (state === "running") {
            const tool = document.getElementById("tool-name");
            if (tool && status.passo_atual) tool.textContent = status.passo_atual;

            const tempo = document.getElementById("meta-tempo");
            if (tempo && status.iniciado_em) {
                const s = Math.floor(Date.now() / 1000 - status.iniciado_em);
                tempo.textContent = `⏱ ${s}s`;
            }
            const passos = document.getElementById("meta-passos");
            if (passos && status.passo_num !== undefined && status.passo_total) {
                passos.textContent = `⚙ ${status.passo_num}/${status.passo_total}`;
            }
        }
    } catch (e) {}
}

const appWin = window.__TAURI__.window.getCurrentWindow();
document.getElementById('btn-close')?.addEventListener('click', () => appWin.close());

const opacityEl = document.getElementById('opacity');
const islandEl = document.getElementById('island');
if (opacityEl && islandEl) {
    const saved = localStorage.getItem('myra-opacity') || '100';
    opacityEl.value = saved;
    islandEl.style.opacity = saved / 100;
    opacityEl.addEventListener('input', () => {
        const val = opacityEl.value;
        islandEl.style.opacity = val / 100;
        localStorage.setItem('myra-opacity', val);
    });
}

window.addEventListener("DOMContentLoaded", () => {
    switchView("idle");
    lastState = "idle";
    setInterval(pollStatus, 500);
});

window.cancelTask = cancelTask;
window.resetWidget = resetWidget;
window.closeWidget = closeWidget;
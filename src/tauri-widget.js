if (window.MYRA_RICH_WIDGET) {
    window.myraTauriWidget = {
        async syncOverlayVisibility(state) {
            try {
                if (state === "idle") await window.__TAURI__.core.invoke("set_overlay_visible", { visible: false });
            } catch (e) {
                console.debug("[OVERLAY] visibilidade indisponivel:", e);
            }
        },
        async setWindowSize(width, height) {
            return window.__TAURI__.core.invoke("resize_window", { width, height });
        }
    };
} else {
// ============================================================
// MYRA Widget — Script (versão Tauri)
// ============================================================

const AGENT_URL = "http://127.0.0.1:8000";

// Dimensões
const IDLE_WIDTH = 200;
const IDLE_HEIGHT = 44;
const CARD_WIDTH = 420;
const CARD_HEIGHT = 260;

let lastState = null;
let startTime = null;

// ============================================================
// IPC helper
// ============================================================

async function invoke(cmd, args = {}) {
    if (window.__TAURI__ && window.__TAURI__.core) {
        return await window.__TAURI__.core.invoke(cmd, args);
    }
    console.warn("[TAURI] API não disponível. Rodando em modo browser?");
    return null;
}

// ============================================================
// Resize da janela via Tauri
// ============================================================

async function setWindowSize(state) {
    let w, h;
    if (state === "idle") {
        w = IDLE_WIDTH;
        h = IDLE_HEIGHT;
    } else {
        w = CARD_WIDTH;
        h = CARD_HEIGHT;
    }
    try {
        await invoke("resize_window", { width: w, height: h });
        console.log(`[RESIZE] ${state} -> ${w}x${h}`);
    } catch (e) {
        console.error("[RESIZE] erro:", e);
    }
}

// ============================================================
// Troca de view
// ============================================================

async function syncOverlayVisibility(state) {
    try {
        await invoke("set_overlay_visible", { visible: state !== "idle" });
    } catch (e) {
        console.debug("[OVERLAY] visibilidade indisponivel:", e);
    }
}

function switchView(state) {
    syncOverlayVisibility(state);
    const island = document.getElementById("island");
    if (!island) return;

    // Remove classes antigas
    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);

    // Troca views ativas
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    const view = document.querySelector(`.view-${state}`);
    if (view) view.classList.add("active");

    // Resize da janela
    setWindowSize(state);
}

// ============================================================
// Ações
// ============================================================

function closeWidget() {
    console.log("[WIDGET] close");
    switchView("idle");
    lastState = "idle";
}

function resetWidget() {
    console.log("[WIDGET] reset");
    switchView("idle");
    lastState = "idle";
}

async function cancelTask() {
    console.log("[WIDGET] cancel");
    try {
        await invoke("cancel_task");
    } catch (e) {
        console.error("[CANCEL] erro:", e);
    }
}

// ============================================================
// Polling de status
// ============================================================

async function pollStatus() {
    try {
        const status = await invoke("get_task_status");
        if (!status) return;

        const state = status.state || "idle";

        if (state !== lastState) {
            console.log(`[POLL] state: ${lastState} -> ${state}`);
            lastState = state;

            // Atualiza campos
            if (state === "running") {
                const tool = document.getElementById("tool-name");
                if (tool && status.passo_atual) tool.textContent = status.passo_atual;

                const tempo = document.getElementById("meta-tempo");
                if (tempo && status.elapsed !== undefined) {
                    tempo.textContent = `⏱ ${Math.floor(status.elapsed)}s`;
                }

                const passos = document.getElementById("meta-passos");
                if (passos && status.passo_num !== undefined && status.passo_total !== undefined) {
                    passos.textContent = `⚙ ${status.passo_num}/${status.passo_total}`;
                }
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
            // Atualiza campos mesmo se o estado não mudou (tempo, passo)
            const tool = document.getElementById("tool-name");
            if (tool && status.passo_atual) tool.textContent = status.passo_atual;

            const tempo = document.getElementById("meta-tempo");
            if (tempo && status.elapsed !== undefined) {
                tempo.textContent = `⏱ ${Math.floor(status.elapsed)}s`;
            }

            const passos = document.getElementById("meta-passos");
            if (passos && status.passo_num !== undefined && status.passo_total !== undefined) {
                passos.textContent = `⚙ ${status.passo_num}/${status.passo_total}`;
            }
        }
    } catch (e) {
        // Agent offline — silêncio
    }
}

// ============================================================
// Init
// ============================================================

window.addEventListener("DOMContentLoaded", () => {
    console.log("[WIDGET] init");
    switchView("idle");
    lastState = "idle";

    // Polling a cada 500ms
    setInterval(pollStatus, 500);
});
// ============================================================
// ============================================================
// Hold-and-drag da janela main, sem interferir nos controles
// ============================================================
function initWidgetDrag() {
    const island = document.getElementById("island");
    const getCurrentWindow = window.__TAURI__?.window?.getCurrentWindow;

    if (!island || typeof getCurrentWindow !== "function") {
        console.warn("[DRAG] API de janela Tauri indisponível");
        return;
    }

    const currentWindow = getCurrentWindow();

    island.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;

        // Controles e texto selecionável nunca iniciam arraste.
        const noDrag = e.target.closest(
            "button, input, textarea, select, [contenteditable], " +
            ".no-drag, .result-text, .tool-name, .state-text, .meta"
        );
        if (noDrag) return;

        e.preventDefault();
        currentWindow.startDragging().catch((err) => {
            console.error("[DRAG] Falha ao mover a janela:", err);
        });
    });
}

window.addEventListener("DOMContentLoaded", initWidgetDrag);
// Click-through condicional (padrao CodeWalkers)
// Quando o cursor esta sobre a UI do widget, desliga ignore_cursor_events
// Quando esta sobre area vazia, liga ignore_cursor_events
// ============================================================

let clickThroughOn = false;
let lastIgnoreState = null;

async function updateClickThrough() {
    try {
        const pos = await invoke("get_mouse_pos");
        if (!pos) return;

        // Converte coordenadas globais (Windows) para locais do WebView
        const scale = window.devicePixelRatio || 1;
        const winX = Math.round(pos.x / scale) - Math.round(window.screenX / scale);
        const winY = Math.round(pos.y / scale) - Math.round(window.screenY / scale);

        const el = document.elementFromPoint(winX, winY);
        const interativo = !!(
            el && (
                el.closest("#island") ||
                el.closest(".mascot") ||
                el.closest(".set-btn") ||
                el.closest("button") ||
                el.closest("[data-tauri-drag-region]")
            )
        );

        // Se cursor sobre UI: ignore=false (permite interagir)
        // Senao: ignore=true (clique passa direto pra baixo)
        const deveIgnorar = !interativo;
        if (deveIgnorar !== lastIgnoreState) {
            await invoke("set_ignore_cursor_events", {
                label: "main",
                ignore: deveIgnorar,
            });
            lastIgnoreState = deveIgnorar;
            clickThroughOn = deveIgnorar;
        }
    } catch (e) {
        // silencio
    }
}

window.addEventListener("DOMContentLoaded", () => {
    // Polling rapido: 100ms responde bem ao movimento do mouse
    setInterval(updateClickThrough, 100);
});
}

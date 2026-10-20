// ============================================================
// MYRA Widget — Lógica da island
// ============================================================

// Dimensões (devem bater com o main.py)
const IDLE_WIDTH = 200;
const IDLE_HEIGHT = 44;
const RUNNING_WIDTH = 420;
const RUNNING_HEIGHT = 200;

// Estado atual
let currentState = "idle";
let lastStatus = null;
let idleTimeout = null;

// Referências aos elementos
const island = document.getElementById("island");
const views = {
    idle: document.querySelector(".view-idle"),
    running: document.querySelector(".view-running"),
    done: document.querySelector(".view-done"),
    error: document.querySelector(".view-error"),
};

// ============================================================
// API wrapper (pywebview expõe window.pywebview.api)
// ============================================================

const WidgetAPI = {
    async closeWidget() {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.close_widget();
        }
    },

    async cancelTask() {
        if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.cancel_task();
            // Volta pra idle
            switchToState("idle");
        }
    },

    async reset() {
        // Volta pra idle (usado depois de done/error)
        switchToState("idle");
    },

    async resize(width, height) {
        if (window.pywebview && window.pywebview.api) {
            await window.pywebview.api.resize_window(width, height);
        }
    },

    log(msg) {
        if (window.pywebview && window.pywebview.api) {
            window.pywebview.api.log(msg);
        } else {
            console.log("[WIDGET]", msg);
        }
    },
};

// ============================================================
// Trocar de estado (idle / running / done / error)
// ============================================================

function switchToState(state, status) {
    if (!views[state]) {
        console.warn("Estado desconhecido:", state);
        return;
    }

    // Cancela timeout anterior (se houver)
    if (idleTimeout) {
        clearTimeout(idleTimeout);
        idleTimeout = null;
    }

    currentState = state;

    // Atualiza classes do container
    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);

    // Esconde todas as views, mostra a certa
    Object.values(views).forEach((v) => v.classList.remove("active"));
    views[state].classList.add("active");

    // Redimensiona a janela
    if (state === "idle") {
        WidgetAPI.resize(IDLE_WIDTH, IDLE_HEIGHT);
    } else {
        WidgetAPI.resize(RUNNING_WIDTH, RUNNING_HEIGHT);
    }

    // Preenche dados específicos do estado
    if (status) {
        if (state === "running") {
            const toolName = status.passo_atual || "iniciando...";
            document.getElementById("tool-name").textContent = toolName;

            const tempo = status.iniciado_em
                ? Math.floor(Date.now() / 1000 - status.iniciado_em)
                : 0;
            document.getElementById("meta-tempo").textContent = `⏱ ${tempo}s`;

            const passos = status.historico ? status.historico.length : 0;
            document.getElementById("meta-passos").textContent = `⚙ ${passos} passo${passos === 1 ? "" : "s"}`;
        } else if (state === "done") {
            const resultado = status.resultado || "(sem resultado)";
            document.getElementById("result-text").textContent = resultado;
        } else if (state === "error") {
            const erro = status.erro || "(sem mensagem)";
            document.getElementById("error-text").textContent = erro;
        }
    }

    // Se done ou error, agenda volta automática pra idle (depois de 8s)
    if (state === "done" || state === "error") {
        idleTimeout = setTimeout(() => {
            switchToState("idle");
        }, 8000);
    }
}

// ============================================================
// Callback do Python (chamado pelo main.py via evaluate_js)
// ============================================================

window.onMyraStatus = function (status) {
    if (!status) return;
    lastStatus = status;

    const state = status.state || "idle";

    // Se mudou de estado ou é o mesmo mas com dados novos, atualiza
    if (state !== currentState || state === "running") {
        switchToState(state, status);
    } else {
        // Mesmo estado, só atualiza dados (ex: tempo passando no running)
        if (state === "running" && status.passo_atual) {
            document.getElementById("tool-name").textContent = status.passo_atual;
        }
        if (state === "running" && status.iniciado_em) {
            const tempo = Math.floor(Date.now() / 1000 - status.iniciado_em);
            document.getElementById("meta-tempo").textContent = `⏱ ${tempo}s`;
        }
        if (state === "running" && status.historico) {
            const passos = status.historico.length;
            document.getElementById("meta-passos").textContent = `⚙ ${passos} passo${passos === 1 ? "" : "s"}`;
        }
    }
};

// ============================================================
// Polling de fallback (se SSE falhar)
// ============================================================

async function pollStatus() {
    try {
        if (window.pywebview && window.pywebview.api) {
            const status = await window.pywebview.api.get_status();
            if (status && status.state) {
                window.onMyraStatus(status);
            }
        }
    } catch (e) {
        console.error("Erro no polling:", e);
    }
}

// Roda polling a cada 2s (fallback do SSE)
setInterval(pollStatus, 2000);

// ============================================================
// Clique na island (modo idle) → abre o chat
// ============================================================

island.addEventListener("click", (e) => {
    // Se clicou num botão, ignora
    if (e.target.tagName === "BUTTON") return;

    if (currentState === "idle") {
        // Abre o Open WebUI no navegador
        window.open("http://127.0.0.1:8080", "_blank");
    }
});

// ============================================================
// Inicialização
// ============================================================

console.log("[MYRA Widget] Iniciando...");

// Espera o pywebview ficar pronto
window.addEventListener("pywebviewready", () => {
    console.log("[MYRA Widget] pywebview pronto");
    WidgetAPI.log("Widget iniciado");

    // Carrega o status inicial
    pollStatus();

    // Mostra idle
    switchToState("idle");
});

// Fallback: se pywebviewready não disparar em 2s, mostra idle mesmo assim
setTimeout(() => {
    if (currentState !== "idle" && !island.classList.contains("idle")) {
        switchToState("idle");
    }
}, 2000);
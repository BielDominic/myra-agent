// MYRA Widget — Logica da island
const AGENT_URL = "http://127.0.0.1:8000";
const POLL_INTERVAL = 1000;

let currentState = "idle";

const island = document.getElementById("island");
const views = {
    idle: document.querySelector(".view-idle"),
    running: document.querySelector(".view-running"),
    done: document.querySelector(".view-done"),
    error: document.querySelector(".view-error"),
};

function switchToState(state, status) {
    if (!views[state]) return;
    currentState = state;

    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);

    Object.values(views).forEach((v) => v.classList.remove("active"));
    views[state].classList.add("active");

    if (status) {
        if (state === "running") {
            const toolName = status.passo_atual || "iniciando...";
            const el = document.getElementById("tool-name");
            if (el) el.textContent = toolName;

            const tempo = status.iniciado_em
                ? Math.floor(Date.now() / 1000 - status.iniciado_em)
                : 0;
            const elTempo = document.getElementById("meta-tempo");
            if (elTempo) elTempo.textContent = `⏱ ${tempo}s`;

            const passos = status.historico ? status.historico.length : 0;
            const elPassos = document.getElementById("meta-passos");
            if (elPassos) elPassos.textContent = `⚙ ${passos} passo${passos === 1 ? "" : "s"}`;
        } else if (state === "done") {
            const resultado = status.resultado || "(sem resultado)";
            const el = document.getElementById("result-text");
            if (el) el.textContent = resultado;
        } else if (state === "error") {
            const erro = status.erro || "(sem mensagem)";
            const el = document.getElementById("error-text");
            if (el) el.textContent = erro;
        }
    }
}

async function pollStatus() {
    try {
        const resp = await fetch(`${AGENT_URL}/task_status`, { method: "GET", cache: "no-store" });
        if (!resp.ok) return;
        const status = await resp.json();
        if (!status || !status.state) return;
        const state = status.state;
        if (state !== currentState || state === "running") {
            switchToState(state, status);
        }
    } catch (e) {}
}

setInterval(pollStatus, POLL_INTERVAL);
pollStatus();

async function cancelTask() {
    try {
        await fetch(`${AGENT_URL}/task_cancel`, { method: "POST" });
        switchToState("idle");
    } catch (e) {
        console.error("Erro ao cancelar:", e);
    }
}

function closeWidget() {
    window.close();
}

function resetWidget() {
    switchToState("idle");
    // Avisa o agent pra resetar o state (pro caso de uma nova task começar)
    fetch(`${AGENT_URL}/task_cancel`, { method: "POST" }).catch(() => {});
}

island.addEventListener("click", (e) => {
    if (e.target.tagName === "BUTTON") return;
    if (!island.classList.contains("idle")) return;

    const rect = island.getBoundingClientRect();
    const x = e.clientX;
    const y = e.clientY;

    const dentro =
        x >= rect.left &&
        x <= rect.right &&
        y >= rect.top &&
        y <= rect.bottom;

    if (dentro) {
        window.open("http://127.0.0.1:8080", "_blank");
    }
});

switchToState("idle");
console.log("[MYRA Widget] Iniciado");
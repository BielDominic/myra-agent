// ============================================================
// MYRA Widget - Tauri (mascote expressivo + chrome toggle)
// ============================================================

const invoke = window.__TAURI__.core.invoke;

const IDLE_W = 200, IDLE_H = 44;
const CARD_W = 440, CARD_H = 340;

let lastState = null;
let resetting = false;

async function setWindowSize(state) {
    const compact = document.body.dataset.compact === "on";
    let w = state === "idle" ? IDLE_W : CARD_W;
    const h = state === "idle" ? IDLE_H : CARD_H;
    if (state === "idle" && compact) w = 90;
    // Espera a animacao CSS (300ms) antes de redimensionar a janela
    setTimeout(async () => {
        try {
            await invoke('resize_window', { width: w, height: h });
        } catch (e) {
            console.error("[RESIZE]", e);
        }
    }, 320);
}

function switchView(state) {
    const island = document.getElementById("island");
    if (!island) return;

    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);

    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    const view = document.querySelector(".view-" + state);
    if (view) view.classList.add("active");

    setWindowSize(state);
    updateMascotState(state);
}

const SPEECHES = {
    idle:    ["Oi! \u{1F44B}", "Pronto!", "To aqui!", "Manda ver!"],
    running: ["Pensando...", "Ja vou!", "Executando...", "Um instante!"],
    done:    ["Feito! \u2705", "Consegui!", "Prontinho!", "Ta na mao!"],
    error:   ["Ops! \u{1F605}", "Deu ruim!", "Tenta de novo!", "Ixi..."]
};

function updateMascotState(state) {
    const mascot = document.querySelector(".view-" + state + " .mascot");
    if (!mascot) return;
    const speech = mascot.querySelector('.speech');
    if (!speech) return;

    const msgs = SPEECHES[state] || [];
    if (msgs.length > 0) {
        const msg = msgs[Math.floor(Math.random() * msgs.length)];
        speech.textContent = msg;
        speech.classList.add('show');
        clearTimeout(speech._timeout);
        speech._timeout = setTimeout(() => speech.classList.remove('show'), 2500);
    }
}

function startBlinking() {
    setInterval(() => {
        document.querySelectorAll('.mascot').forEach(m => {
            m.classList.add('blink');
            setTimeout(() => m.classList.remove('blink'), 120);
        });
    }, 3000 + Math.random() * 4000);
}

function startEyeTracking() {
    document.addEventListener('mousemove', (e) => {
        const mascots = document.querySelectorAll('.mascot:not(.done):not(.error)');
        mascots.forEach(mascot => {
            const rect = mascot.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = e.clientX - cx;
            const dy = e.clientY - cy;
            const dist = Math.sqrt(dx * dx + dy * dy);
            const maxOffset = 3;
            const factor = Math.min(dist / 100, 1);
            const ox = (dx / (dist || 1)) * maxOffset * factor;
            const oy = (dy / (dist || 1)) * maxOffset * factor;
            mascot.querySelectorAll('.eye').forEach(eye => {
                eye.style.transform = "translate(" + ox + "px, " + oy + "px)";
            });
        });
    });
}

function setupMascotClick() {
    document.querySelectorAll('.mascot').forEach(m => {
        m.addEventListener('click', (e) => {
            e.stopPropagation();
            console.log("[MASCOT] click -> abrir chat");
        });
    });
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
            console.log("[POLL] " + lastState + " -> " + state + " | passo=" + status.passo_atual + " num=" + status.passo_num);
            lastState = state;

            if (state === "running") {
                const tool = document.getElementById("tool-name");
                if (tool && status.passo_atual) tool.textContent = status.passo_atual;
            }
            if (state === "done") {
                const result = document.getElementById("result-text");
                if (result) result.textContent = status.resultado || "(sem resultado)";
                if (window.myraOnDone) window.myraOnDone();
            }
            if (state === "error") {
                const err = document.getElementById("error-text");
                if (err) err.textContent = status.erro || "(sem mensagem)";
                if (window.myraOnError) window.myraOnError();
            }
            switchView(state);
        } else if (state === "running") {
            const tool = document.getElementById("tool-name");
            if (tool && status.passo_atual) tool.textContent = status.passo_atual;
            const tempo = document.getElementById("meta-tempo");
            if (tempo && status.iniciado_em) {
                const s = Math.floor(Date.now() / 1000 - status.iniciado_em);
                tempo.textContent = "\u23F1 " + s + "s";
            }
            const passos = document.getElementById("meta-passos");
            if (passos && status.passo_num !== undefined && status.passo_total) {
                passos.textContent = "\u2699 " + status.passo_num + "/" + status.passo_total;
            }
        }
    } catch (e) { /* offline */ }
}

const appWin = window.__TAURI__.window.getCurrentWindow();
const chromeEl = document.getElementById('chrome');
const btnSettings = document.getElementById('btn-settings');
const btnClose = document.getElementById('btn-close');

btnSettings?.addEventListener('click', (e) => {
    e.stopPropagation();
    chromeEl.classList.toggle('show');
});

document.addEventListener('click', (e) => {
    if (!chromeEl.contains(e.target) && e.target !== btnSettings) {
        chromeEl.classList.remove('show');
    }
});

btnClose?.addEventListener('click', () => appWin.close());

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
    startBlinking();
    startEyeTracking();
    setupMascotClick();
    setInterval(pollStatus, 300);
});

// ============================================================
// Acões dos botões do card "done"
// ============================================================

// Copia o texto do resultado pro clipboard
async function copyResult() {
    const resultEl = document.getElementById("result-text");
    if (!resultEl) return;
    const texto = resultEl.textContent || "";
    if (!texto.trim()) return;

    try {
        // Tenta usar a API do Tauri (clipboard plugin) - se nao existir, usa fallback
        if (window.__TAURI__ && window.__TAURI__.clipboardManager) {
            await window.__TAURI__.clipboardManager.writeText(texto);
        } else {
            await navigator.clipboard.writeText(texto);
        }
        // Feedback visual: troca o texto do botao temporariamente
        const botoes = document.querySelectorAll('.qa');
        botoes.forEach(b => {
            if (b.textContent.includes("Copiar")) {
                const orig = b.textContent;
                b.textContent = "✅ Copiado!";
                setTimeout(() => { b.textContent = orig; }, 1500);
            }
        });
    } catch (e) {
        console.error("[COPY] Erro:", e);
        // Fallback best-effort via textarea
        try {
            const ta = document.createElement("textarea");
            ta.value = texto;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
        } catch (e2) {
            console.error("[COPY] Fallback falhou:", e2);
        }
    }
}

// Repete a última task enviando de novo pro agent
async function repeatTask() {
    const resultEl = document.getElementById("result-text");
    if (!resultEl) return;
    const objetivo = window.__ultimoObjetivo || null;
    if (!objetivo) {
        console.warn("[REPEAT] Sem objetivo salvo");
        return;
    }
    try {
        // Volta pra idle e manda o mesmo objetivo pro backend
        await fetch("http://127.0.0.1:8000/task_simple", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ objetivo: objetivo })
        }).catch(() => {});
    } catch (e) {
        console.error("[REPEAT] Erro:", e);
    }
}

// Salva o objetivo sempre que uma task nova começa
if (!window.__myraOriginalSwitchView) {
    window.__myraOriginalSwitchView = switchView;
    window.switchView = function(state) {
        if (state === "running") {
            // tenta pegar o objetivo do status atual
            if (window.__ultimoStatus && window.__ultimoStatus.objetivo) {
                window.__ultimoObjetivo = window.__ultimoStatus.objetivo;
            }
        }
        return window.__myraOriginalSwitchView(state);
    };
}

// Expõe no window
window.copyResult = copyResult;
window.repeatTask = repeatTask;
window.cancelTask = cancelTask;
window.resetWidget = resetWidget;
window.closeWidget = closeWidget;
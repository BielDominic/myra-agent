// ============================================================
// MYRA Widget - Tauri (mascote expressivo + chrome toggle)
// ============================================================

const invoke = window.__TAURI__.core.invoke;

const IDLE_W = 220, IDLE_H = 96;
const CARD_W = 440, CARD_H = 340;

let lastState = null;
let resetting = false;

async function setWindowSize(state) {
    const compact = document.body.dataset.compact === "on";
    const runningMode = document.body.dataset.runningMode || "full";

    let w, h;
    if (state === "idle") {
        w = compact ? 90 : IDLE_W;
        h = IDLE_H;
    } else if (state === "running" && runningMode === "pill") {
        w = IDLE_W;
        h = IDLE_H;
    } else {
        w = CARD_W;
        h = CARD_H;
    }

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
            // Olhos: movimento total + leve inclinacao
            const tilt = (ox / 3) * 10;
            mascot.querySelectorAll('.eye').forEach(eye => {
                eye.style.transform = "translate(" + ox + "px, " + oy + "px) rotate(" + tilt + "deg)";
            });
            // Boca: so mexe se ela ta visivel (balao aberto) - evita artefato do WebView2
            const mouth = mascot.querySelector('.mouth');
            const speechOpen = mascot.querySelector('.speech.show');
            if (mouth && speechOpen) {
                const mx = ox * 0.5;
                const my = oy * 0.5;
                mouth.style.transform = "translateX(-50%) translate(" + mx + "px, " + my + "px)";
            }
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
                // Tempo de resposta
                if (status.iniciado_em && status.terminado_em) {
                    const dur = Math.round(status.terminado_em - status.iniciado_em);
                    window.__ultimaDuracao = dur;
                }
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
            if (passos && status.passo_num !== undefined) {
                // Mostra o passo atual. Se o backend mandar "passo_total_conhecido", usa.
                const atual = status.passo_num || 0;
                passos.textContent = "\u2699 " + atual + (atual === 1 ? " passo" : " passos");
            }
            // Timer pequeno da pilula
            const pillTimer = document.getElementById("pill-timer");
            if (pillTimer && status.iniciado_em) {
                const s = Math.floor(Date.now() / 1000 - status.iniciado_em);
                pillTimer.textContent = s + "s";
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

// ============================================================
// Handlers dos botoes das Configuracoes
// ============================================================
window.addEventListener("DOMContentLoaded", () => {
    // --- Tema ---
    const btnTheme = document.getElementById("btn-theme");
    if (btnTheme) {
        btnTheme.addEventListener("click", () => {
            const cur = document.body.dataset.theme || "dark";
            const nxt = cur === "dark" ? "light" : "dark";
            document.body.dataset.theme = nxt;
            localStorage.setItem("myra-theme", nxt);
            btnTheme.classList.toggle("active", nxt === "light");
        });
        const saved = localStorage.getItem("myra-theme");
        if (saved) document.body.dataset.theme = saved;
        btnTheme.classList.toggle("active", document.body.dataset.theme === "light");
    }

    // --- Compacto ---
    const btnCompact = document.getElementById("btn-compact");
    if (btnCompact) {
        btnCompact.addEventListener("click", () => {
            const cur = document.body.dataset.compact === "on";
            document.body.dataset.compact = cur ? "off" : "on";
            localStorage.setItem("myra-compact", cur ? "off" : "on");
            btnCompact.classList.toggle("active", !cur);
            // Redimensiona janela
            setWindowSize(lastState || "idle");
        });
        const saved = localStorage.getItem("myra-compact");
        if (saved === "on") {
            document.body.dataset.compact = "on";
            btnCompact.classList.add("active");
        }
    }

    // --- Som ---
    const btnSound = document.getElementById("btn-sound");
    if (btnSound) {
        btnSound.addEventListener("click", () => {
            const cur = localStorage.getItem("myra-sound") === "on";
            const nxt = !cur;
            localStorage.setItem("myra-sound", nxt ? "on" : "off");
            btnSound.classList.toggle("active", nxt);
        });
        btnSound.classList.toggle("active", localStorage.getItem("myra-sound") === "on");
    }

    // --- Nao perturbe ---
    const btnDnd = document.getElementById("btn-dnd");
    if (btnDnd) {
        btnDnd.addEventListener("click", () => {
            const cur = localStorage.getItem("myra-dnd") === "on";
            const nxt = !cur;
            localStorage.setItem("myra-dnd", nxt ? "on" : "off");
            btnDnd.classList.toggle("active", nxt);
        });
        btnDnd.classList.toggle("active", localStorage.getItem("myra-dnd") === "on");
    }

    // --- Modo pilula em running ---
    const btnToggleMode = document.getElementById("btn-toggle-running-mode");
    if (btnToggleMode) {
        let runningMode = localStorage.getItem("myra-running-mode") || "full";
        document.body.dataset.runningMode = runningMode;

        const updateToggleBtn = () => {
            btnToggleMode.textContent = runningMode === "pill" ? "\u25B2" : "\u25BC";
            btnToggleMode.title = runningMode === "pill" ? "Expandir" : "Recolher";
        };
        updateToggleBtn();

        btnToggleMode.addEventListener("click", (e) => {
            e.stopPropagation();
            runningMode = runningMode === "pill" ? "full" : "pill";
            document.body.dataset.runningMode = runningMode;
            localStorage.setItem("myra-running-mode", runningMode);
            updateToggleBtn();
            // Redimensiona janela
            setWindowSize(lastState || "running");
        });
    }

    // --- Cancelar pela pilula ---
    const btnCancelPill = document.getElementById("btn-cancel-pill");
    if (btnCancelPill) {
        btnCancelPill.addEventListener("click", (e) => {
            e.stopPropagation();
            cancelTask();
        });
        // So mostra no modo pilula
        const updateCancelVisibility = () => {
            const mode = document.body.dataset.runningMode || "full";
            btnCancelPill.style.display = mode === "pill" ? "" : "none";
        };
        updateCancelVisibility();
        // Observa mudanca de modo
        const observer = new MutationObserver(updateCancelVisibility);
        observer.observe(document.body, { attributes: true, attributeFilter: ["data-running-mode"] });
    }

    // --- Travar posicao (NAO mexe em alwaysOnTop, que fica sempre ligado) ---
    const btnTop = document.getElementById("btn-top");
    if (btnTop) {
        let travado = localStorage.getItem("myra-travado") === "on"; // default: destravado

        const aplicarTrava = (trav) => {
            if (trav) {
                const elementos = document.querySelectorAll("[data-tauri-drag-region]");
                elementos.forEach(el => {
                    if (!el.dataset.myraDragBackup) {
                        el.dataset.myraDragBackup = "1";
                    }
                    el.removeAttribute("data-tauri-drag-region");
                });
            } else {
                const elementos = document.querySelectorAll("[data-myra-drag-backup]");
                elementos.forEach(el => {
                    el.setAttribute("data-tauri-drag-region", "");
                    delete el.dataset.myraDragBackup;
                });
            }
        };

        const updateTopBtn = () => {
            btnTop.classList.toggle("active", travado);
            btnTop.textContent = travado ? "\u{1F512} Posicao travada" : "\u{1F4CC} Travar posicao";
        };

        // Aplica estado salvo no boot (so a trava, alwaysOnTop vem do conf)
        aplicarTrava(travado);
        updateTopBtn();
        console.log("[TRAVA] estado inicial:", travado ? "travado" : "livre");

        btnTop.addEventListener("click", () => {
            travado = !travado;
            aplicarTrava(travado);
            localStorage.setItem("myra-travado", travado ? "on" : "off");
            updateTopBtn();
            console.log("[TRAVA]", travado ? "travado" : "livre");
        });
    }
});
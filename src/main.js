// ============================================================
// MYRA Widget - Tauri (mascote expressivo + chrome toggle)
// ============================================================

const invoke = window.__TAURI__.core.invoke;

const IDLE_W = 220, IDLE_H = 44;
const CARD_W = 440, CARD_H = 340;
const SETTINGS_W = 380, SETTINGS_H = 550;

let lastState = null;
let resetting = false;

async function setWindowSize(state) {
    const compact = document.body.dataset.compact === "on";
    let size;
    if (state === "idle") size = compact ? "compact" : "idle";
    else if (state === "settings") {
        // Keep the existing larger settings window.
        const w = SETTINGS_W, h = SETTINGS_H;
        setTimeout(async () => {
            try { await invoke('resize_window', { width: w, height: h }); }
            catch (e) { console.error("[RESIZE]", e); }
        }, 320);
        return;
    } else if (state === "running" && document.body.dataset.runningMode === "pill") size = "pill";
    else size = "running";

    setTimeout(async () => {
        try { await invoke('set_widget_size', { size }); }
        catch (e) { console.error("[RESIZE]", e); }
    }, 320);
}

function switchView(state) {
    const island = document.getElementById("island");
    if (!island) return;

    const settingsOpen = island.classList.contains("settings");
    island.classList.remove("idle", "running", "done", "error");
    island.classList.add(state);

    // Sempre redimensiona a janela nativa quando o estado muda, inclusive em updates SSE.
    setWindowSize(state);

    // A tarefa pode mudar enquanto as configuracoes estao abertas.
    // Atualiza o estado de retorno sem fechar a tela de configuracoes.
    if (settingsOpen) {
        island.dataset.prevState = state;
        document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
        document.querySelector(".view-settings")?.classList.add("active");
        updateMascotState(state);
        return;
    }

    document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
    const view = document.querySelector(".view-" + state);
    if (view) view.classList.add("active");

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
        window.__ultimoStatus = status;
        if (status.objetivo) window.__ultimoObjetivo = status.objetivo;
        renderTaskProgress(status);
        updatePauseResumeButton(status);

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
                saveTaskHistory(status, "done");
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
                saveTaskHistory(status, "error");
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


// Recursos adicionais: progresso, pausa/retomada, historico e rotinas locais
const MYRA_HISTORY_KEY = "myra-task-history-v1";
const MYRA_ROUTINES_KEY = "myra-routines-v1";
const MYRA_MAX_HISTORY = 30;

function safeLocalArray(key) {
    try {
        const value = JSON.parse(localStorage.getItem(key) || "[]");
        return Array.isArray(value) ? value : [];
    } catch (_) { return []; }
}

let _lastTimelineSignature = "";
function renderTaskProgress(status) {
    const objective = document.getElementById("task-objective");
    const fill = document.getElementById("task-progress-fill");
    const bar = fill && fill.parentElement;
    const label = document.getElementById("task-progress-label");
    const percent = document.getElementById("task-progress-percent");
    const timeline = document.getElementById("task-timeline");
    if (!objective || !fill || !label || !percent || !timeline) return;
    const goal = String(status.objetivo || window.__ultimoObjetivo || "").trim();
    objective.textContent = goal;
    objective.hidden = !goal;
    const current = Math.max(0, Number(status.passo_num) || 0);
    const total = Math.max(0, Number(status.passo_total) || 0);
    const isPaused = String(status.passo_atual || "").toUpperCase().includes("PAUSADO");
    const value = total > 0 ? Math.min(95, Math.round(current / total * 100)) : (current > 0 ? 15 : 3);
    fill.style.width = value + "%";
    if (bar) bar.setAttribute("aria-valuenow", String(value));
    label.textContent = isPaused ? "Pausada — pronta para retomar" :
        total > 0 ? ("Etapa " + Math.min(current || 1, total) + " de " + total) :
        current > 0 ? (current + " etapa(s) concluída(s)") : "Planejando";
    percent.textContent = value + "%";
    const history = Array.isArray(status.historico) ? status.historico : [];
    const recent = history.slice(-4);
    const signature = JSON.stringify(recent);
    if (signature === _lastTimelineSignature) return;
    _lastTimelineSignature = signature;
    timeline.replaceChildren();
    if (!recent.length) {
        const item = document.createElement("div");
        item.className = "timeline-empty";
        item.textContent = "As etapas executadas aparecerão aqui.";
        timeline.appendChild(item);
        return;
    }
    recent.forEach(step => {
        const row = document.createElement("div");
        row.className = "timeline-item" + (step.ok === false ? " failed" : " complete");
        const dot = document.createElement("span");
        dot.className = "timeline-dot";
        dot.setAttribute("aria-hidden", "true");
        const name = document.createElement("span");
        name.className = "timeline-name";
        name.textContent = String(step.ferramenta || step.passo || "Etapa").replace(/[_-]+/g, " ");
        const state = document.createElement("span");
        state.className = "timeline-status";
        state.textContent = step.ok === false ? "Falhou" : "Feita";
        row.append(dot, name, state);
        timeline.appendChild(row);
    });
}

function updatePauseResumeButton(status) {
    const btn = document.getElementById("btn-pause-resume");
    if (!btn) return;
    const paused = String(status && status.passo_atual || "").toUpperCase().includes("PAUSADO");
    const stateLabel = document.getElementById("task-state-label");
    if (stateLabel && status && status.state === "running") stateLabel.textContent = paused ? "Pausada" : "Executando...";
    btn.textContent = paused ? "Retomar" : "Pausar";
    btn.title = paused ? "Retomar tarefa (Ctrl+Shift+P)" : "Pausar no próximo ponto seguro (Ctrl+Shift+P)";
    btn.classList.toggle("is-paused", paused);
    btn.disabled = !status || status.state !== "running" || !status.task_id;
}

async function pauseResumeTask() {
    const status = window.__ultimoStatus || {};
    if (status.state !== "running" || !status.task_id) return;
    const paused = String(status.passo_atual || "").toUpperCase().includes("PAUSADO");
    const btn = document.getElementById("btn-pause-resume");
    if (btn) btn.disabled = true;
    try {
        let resumeId = status.task_id;
        // Compatibilidade com o backend que ainda mantém o ID temporário no status.
        if (paused && !String(resumeId || "").startsWith("task-")) {
            const pendingResponse = await fetch("http://127.0.0.1:8000/task_pendentes?limite=20");
            const pendingData = await pendingResponse.json();
            const tasks = Array.isArray(pendingData.tasks) ? pendingData.tasks : [];
            const objective = String(status.objetivo || window.__ultimoObjetivo || "").trim();
            const match = tasks.find(task => String(task.objetivo || "").trim() === objective) || tasks[0];
            if (match && match.task_id) resumeId = match.task_id;
            else throw new Error("A tarefa pausada não apareceu na lista de retomada.");
        }
        const response = paused
            ? await fetch("http://127.0.0.1:8000/task_resume", {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ task_id: resumeId })
              })
            : await fetch("http://127.0.0.1:8000/task_pause", { method: "POST" });
        const data = await response.json();
        if (!response.ok || data.status === "erro") throw new Error(data.result || ("HTTP " + response.status));
        if (btn) btn.textContent = paused ? "Retomando..." : "Pausando...";
    } catch (err) {
        console.error("[TASK PAUSE/RESUME]", err);
        if (btn) {
            btn.disabled = false;
            btn.textContent = "Tentar novamente";
            btn.title = String(err.message || err);
        }
    }
}
window.pauseResumeTask = pauseResumeTask;

function saveTaskHistory(status, outcome) {
    const objective = String(status.objetivo || window.__ultimoObjetivo || "").trim();
    const result = String(outcome === "done" ? (status.resultado || "") : (status.erro || ""));
    const key = String(status.task_id || (objective + "|" + (status.iniciado_em || "")));
    const rows = safeLocalArray(MYRA_HISTORY_KEY);
    if (rows.some(row => row.key === key && row.outcome === outcome)) return;
    const start = Number(status.iniciado_em) || 0;
    const end = Number(status.terminado_em) || Math.floor(Date.now() / 1000);
    rows.unshift({
        key, objective: objective || "Tarefa sem descrição", outcome, result,
        duration: start > 0 ? Math.max(0, end - start) : 0,
        steps: Array.isArray(status.historico) ? status.historico.length : (Number(status.passo_num) || 0),
        finishedAt: Date.now()
    });
    try { localStorage.setItem(MYRA_HISTORY_KEY, JSON.stringify(rows.slice(0, MYRA_MAX_HISTORY))); }
    catch (err) { console.warn("[HISTORY] Falha ao salvar histórico local", err); }
    renderTaskHistory();
}

function renderTaskHistory() {
    const panel = document.getElementById("task-history");
    if (!panel) return;
    const rows = safeLocalArray(MYRA_HISTORY_KEY);
    panel.replaceChildren();
    if (!rows.length) {
        const empty = document.createElement("p");
        empty.className = "local-list-empty";
        empty.textContent = "Nenhuma execução concluída ainda.";
        panel.appendChild(empty);
        return;
    }
    rows.slice(0, 10).forEach(row => {
        const item = document.createElement("div");
        item.className = "history-item";
        const main = document.createElement("div");
        main.className = "history-main";
        const title = document.createElement("span");
        title.className = "history-objective";
        title.textContent = row.objective || "Tarefa";
        title.title = row.objective || "";
        const meta = document.createElement("span");
        meta.className = "history-meta";
        meta.textContent = (row.outcome === "done" ? "Concluída" : "Erro") + " · " +
            (row.steps || 0) + " etapas \u00b7 " + (row.duration || 0) + "s \u00b7 " +
            new Date(row.finishedAt || Date.now()).toLocaleString();
        main.append(title, meta);
        const rerun = document.createElement("button");
        rerun.type = "button";
        rerun.className = "history-rerun";
        rerun.textContent = "Executar";
        rerun.title = "Executar este objetivo novamente";
        rerun.addEventListener("click", () => runMyraObjective(row.objective));
        item.append(main, rerun);
        panel.appendChild(item);
    });
}

async function runMyraObjective(objective) {
    const goal = String(objective || "").trim();
    if (!goal) return;
    if (window.__ultimoStatus && window.__ultimoStatus.state === "running") {
        alert("A MYRA j\u00e1 est\u00e1 executando uma tarefa. Aguarde ou cancele antes de iniciar outra.");
        return;
    }
    try {
        window.__ultimoObjetivo = goal;
        closeSettings();
        const response = await fetch("http://127.0.0.1:8000/task_simple", {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ objetivo: goal })
        });
        const data = await response.json();
        if (!response.ok || data.status === "erro") throw new Error(data.result || ("HTTP " + response.status));
    } catch (err) {
        console.error("[RUN OBJECTIVE]", err);
        alert("Não consegui iniciar a tarefa. Verifique se o backend da MYRA está ativo.");
    }
}

function renderRoutines() {
    const panel = document.getElementById("routine-list");
    if (!panel) return;
    panel.replaceChildren();
    const routines = safeLocalArray(MYRA_ROUTINES_KEY);
    if (!routines.length) {
        const empty = document.createElement("p");
        empty.className = "local-list-empty";
        empty.textContent = "Salve uma tarefa acima para criar sua primeira rotina.";
        panel.appendChild(empty);
        return;
    }
    routines.forEach((routine, index) => {
        const item = document.createElement("div");
        item.className = "routine-item";
        const name = document.createElement("span");
        name.className = "routine-name";
        name.textContent = routine.name;
        name.title = routine.objective;
        const run = document.createElement("button");
        run.type = "button";
        run.className = "history-rerun";
        run.textContent = "Rodar";
        run.addEventListener("click", () => runMyraObjective(routine.objective));
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "routine-remove";
        remove.textContent = "×";
        remove.title = "Remover rotina";
        remove.setAttribute("aria-label", "Remover rotina " + routine.name);
        remove.addEventListener("click", () => {
            const current = safeLocalArray(MYRA_ROUTINES_KEY);
            current.splice(index, 1);
            localStorage.setItem(MYRA_ROUTINES_KEY, JSON.stringify(current));
            renderRoutines();
        });
        item.append(name, run, remove);
        panel.appendChild(item);
    });
}

function setupLocalTaskTools() {
    const historyToggle = document.getElementById("btn-history-toggle");
    const historyPanel = document.getElementById("task-history");
    historyToggle && historyToggle.addEventListener("click", () => {
        const open = historyPanel.hidden;
        historyPanel.hidden = !open;
        historyToggle.textContent = open ? "Ocultar" : "Mostrar";
        historyToggle.setAttribute("aria-expanded", String(open));
        if (open) renderTaskHistory();
    });
    document.getElementById("btn-history-clear")?.addEventListener("click", () => {
        if (!confirm("Apagar todo o histórico local de tarefas? Esta ação não pode ser desfeita.")) return;
        localStorage.removeItem(MYRA_HISTORY_KEY);
        renderTaskHistory();
    });
    const saveBtn = document.getElementById("btn-save-routine");
    saveBtn && saveBtn.addEventListener("click", () => {
        const nameEl = document.getElementById("routine-name");
        const objectiveEl = document.getElementById("routine-objective");
        const name = String(nameEl && nameEl.value || "").trim();
        const objective = String(objectiveEl && objectiveEl.value || "").trim();
        if (!name || !objective) {
            alert("Preencha o nome e a instrução da rotina.");
            return;
        }
        const routines = safeLocalArray(MYRA_ROUTINES_KEY);
        if (routines.length >= 20) {
            alert("Limite de 20 rotinas. Remova uma rotina antiga para adicionar outra.");
            return;
        }
        routines.push({ name: name.slice(0, 48), objective: objective.slice(0, 1200) });
        localStorage.setItem(MYRA_ROUTINES_KEY, JSON.stringify(routines));
        nameEl.value = "";
        objectiveEl.value = "";
        renderRoutines();
    });
    renderTaskHistory();
    renderRoutines();
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
    if (chromeEl && !chromeEl.contains(e.target) && e.target !== btnSettings) {
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
    setupMascotClick();
    setupLocalTaskTools();
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
async function copyError() {
    const errorEl = document.getElementById("error-text");
    const text = String(errorEl && errorEl.textContent || "").trim();
    if (!text) return;
    try {
        if (window.__TAURI__?.clipboardManager?.writeText) {
            await window.__TAURI__.clipboardManager.writeText(text);
        } else if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
        } else {
            throw new Error("Clipboard indispon\u00edvel");
        }
        const btn = document.getElementById("btn-copy-error");
        if (btn) {
            const old = btn.textContent;
            btn.textContent = "Copiado";
            setTimeout(() => { btn.textContent = old; }, 1200);
        }
    } catch (err) {
        console.warn("[COPY ERROR]", err);
        try {
            const ta = document.createElement("textarea");
            ta.value = text;
            document.body.appendChild(ta);
            ta.select();
            document.execCommand("copy");
            ta.remove();
        } catch (_) {}
    }
}

async function retryFailedTask() {
    const objective = String(window.__ultimoObjetivo || window.__ultimoStatus?.objetivo || "").trim();
    if (!objective) {
        alert("N\u00e3o foi poss\u00edvel recuperar o objetivo original desta tarefa.");
        return;
    }
    await runMyraObjective(objective);
}

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
window.copyError = copyError;
window.retryFailedTask = retryFailedTask;
window.repeatTask = repeatTask;
window.cancelTask = cancelTask;
window.resetWidget = resetWidget;
window.closeWidget = closeWidget;

// ============================================================
// Handlers dos botoes das Configuracoes
// ============================================================
window.addEventListener("DOMContentLoaded", () => {
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
            btnTop.textContent = travado ? "Travado" : "Destravado";
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
// ============================================================
// Arraste da janela main: fundo move, controles continuam clicaveis
// ============================================================
function initWidgetDrag() {
    const island = document.getElementById("island");
    const getCurrentWindow = window.__TAURI__?.window?.getCurrentWindow;
    if (!island || typeof getCurrentWindow !== "function" || island.dataset.dragBound === "true") return;
    island.dataset.dragBound = "true";
    const currentWindow = getCurrentWindow();
    // Capture no document para nao depender do bubbling de elementos com
    // data-tauri-drag-region nem de handlers internos da mascote.
    document.addEventListener("mousedown", (e) => {
        if (!island.contains(e.target) || e.button !== 0) return;
        // Respeita a opcao "Travar posicao" mesmo com arraste via JS.
        if (localStorage.getItem("myra-travado") === "on") return;
        if (e.target.closest("button, input, textarea, select, label, [contenteditable], .no-drag, .result-text, .tool-name, .state-text, .meta, .quick-actions")) return;
        e.preventDefault();
        currentWindow.startDragging().catch((err) => console.error("[DRAG] Falha ao mover a janela:", err));
    }, true);
}
// O script pode ser carregado depois de DOMContentLoaded pelo WebView.
// Inicializa nos dois casos, sem registrar listeners duplicados.
if (document.readyState === "loading") {
    window.addEventListener("DOMContentLoaded", initWidgetDrag, { once: true });
} else {
    initWidgetDrag();
}

// Segurança de interação: a janela principal do widget nunca deve ficar
// permanentemente click-through. O cálculo antigo com screenX/devicePixelRatio
// podia marcar a janela inteira como ignorável e bloquear botões e arraste.
window.addEventListener("DOMContentLoaded", async () => {
    try {
        await invoke("set_ignore_cursor_events", { label: "main", ignore: false });
        console.log("[WIDGET] Interação do widget habilitada");
    } catch (err) {
        console.warn("[WIDGET] Não foi possível redefinir click-through:", err);
    }
});
// Atalhos locais: Esc fecha configuracoes; Ctrl+Shift+M compacto; Ctrl+Shift+S som.
document.addEventListener("keydown", (e) => {
    const island = document.getElementById("island");
    if (e.key === "Escape" && island && island.classList.contains("settings")) {
        e.preventDefault();
        document.getElementById("btn-back-settings")?.click();
        return;
    }
    if (!(e.ctrlKey && e.shiftKey && !e.altKey && !e.metaKey)) return;
    const target = e.target;
    if (target && target.closest && target.closest("input, textarea, select, [contenteditable='true']")) return;
    const key = e.key.toLowerCase();
    const button = key === "m" ? document.getElementById("btn-compact")
                  : key === "s" ? document.getElementById("btn-sound")
                  : key === "p" ? document.getElementById("btn-pause-resume")
                  : null;
    if (button && !button.disabled) {
        e.preventDefault();
        button.click();
        return;
    }
    if (key === "h") {
        e.preventDefault();
        if (!document.getElementById("island").classList.contains("settings")) {
            document.getElementById("btn-open-settings")?.click();
        }
        setTimeout(() => {
            const toggle = document.getElementById("btn-history-toggle");
            if (toggle && toggle.getAttribute("aria-expanded") !== "true") toggle.click();
        }, 380);
    }
});

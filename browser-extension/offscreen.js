// MYRA Browser Bridge - polling persistente em offscreen document (Manifest V3)
const DEFAULT_API = "http://127.0.0.1:8000";
const POLL_WAIT = 5;
const POLL_ATTEMPTS = 3;
const POLL_INTERVAL_MS = 5000;

let pollTimer = null;
let activePolls = 0;
let ultimoPollComSucesso = Date.now();
let watchdogTimer = null;

async function fetchSettingsFromSW() {
  const response = await chrome.runtime.sendMessage({ type: "MYRA_GET_SETTINGS" });
  if (!response || response.ok === false) {
    throw new Error(response?.error || "O service worker não devolveu as configurações do Browser Bridge.");
  }
  return response.settings || response;
}

async function bridgeFetch(path, settings, options = {}) {
  const api = settings.myraApi || DEFAULT_API;
  const token = settings.myraToken || "";
  if (!token) throw new Error("Token nao configurado.");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  console.log("[Offscreen] fetch iniciando", path);
  try {
    const response = await fetch(api + path, {
      ...options,
      headers: { ...(options.headers || {}), "X-MYRA-BRIDGE-TOKEN": token },
      cache: "no-store",
      signal: controller.signal
    });
    ultimoPollComSucesso = Date.now();
    console.log("[Offscreen] fetch retornou", response.status, path);
    return response;
  } finally {
    clearTimeout(timeout);
  }
}

async function executeInServiceWorker(command) {
  const response = await chrome.runtime.sendMessage({
    type: "MYRA_EXECUTE_COMMAND",
    command
  });
  if (!response) throw new Error("O service worker nao respondeu ao comando.");
  if (!response.ok) throw new Error(response.error || "Falha ao executar comando no service worker.");
  return response.result;
}

async function pollOnce() {
  activePolls++;
  try {
    const settings = await fetchSettingsFromSW();
    if (!settings.myraEnabled || !settings.myraToken) return;

    for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt++) {
      try {
        console.log("[MYRA Bridge Offscreen] poll tentativa", attempt + 1);
        const res = await bridgeFetch("/browser_bridge/next?wait=" + POLL_WAIT, settings);
        if (!res.ok) throw new Error("HTTP " + res.status);
        const payload = await res.json();
        const cmd = payload.command;
        if (!cmd) continue;

        console.log("[MYRA Bridge Offscreen] comando:", cmd.action);
        let result;
        try {
          result = await executeInServiceWorker(cmd);
        } catch (e) {
          result = { ok: false, error: e?.message || String(e) };
        }

        const completed = await bridgeFetch("/browser_bridge/complete", settings, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ command_id: cmd.command_id, result })
        });
        if (!completed.ok) throw new Error("HTTP " + completed.status + " ao concluir comando");
        console.log("[MYRA Bridge Offscreen] comando concluido:", cmd.action);
        return;
      } catch (e) {
        console.warn("[MYRA Bridge Offscreen] erro:", e?.name, e?.message || e);
        return;
      }
    }
  } catch (e) {
    console.warn("[MYRA Bridge Offscreen] poll falhou:", e?.name, e?.message || e);
  } finally {
    activePolls = Math.max(0, activePolls - 1);
  }
}

function startPolling() {
  if (pollTimer) return;
  console.log("[MYRA Bridge Offscreen] iniciando polling");
  pollTimer = setInterval(() => {
    console.log("[Offscreen] poll tick");
    pollOnce().catch(e => console.warn("[MYRA Bridge Offscreen] poll err:", e?.message || e));
  }, POLL_INTERVAL_MS);
  if (!watchdogTimer) {
    watchdogTimer = setInterval(() => {
      const desde = Date.now() - ultimoPollComSucesso;
      if (desde > 30000) {
        console.warn("[Offscreen] watchdog: sem resposta de fetch há", Math.round(desde / 1000), "s; resetando contador e disparando novo poll");
        // activePolls é apenas telemetria, nunca um bloqueio. Um poll antigo
        // pode continuar pendente, mas não impede novos ciclos de polling.
        activePolls = 0;
        pollOnce().catch(e => console.warn("[Offscreen] watchdog poll err:", e?.message || e));
      }
    }, 10000);
  }
  pollOnce().catch(e => console.warn("[MYRA Bridge Offscreen] initial err:", e?.message || e));
}

function stopPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
  if (watchdogTimer) clearInterval(watchdogTimer);
  watchdogTimer = null;
  console.log("[MYRA Bridge Offscreen] polling parado");
}

async function syncPollingWithSettings() {
  try {
    const settings = await fetchSettingsFromSW();
    if (settings.myraEnabled && settings.myraToken) startPolling();
    else stopPolling();
  } catch (e) {
    console.warn("[MYRA Bridge Offscreen] settings err:", e?.message || e);
    stopPolling();
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "MYRA_SYNC_SETTINGS") {
    syncPollingWithSettings()
      .then(() => sendResponse({ ok: true, polling: Boolean(pollTimer) }))
      .catch(e => sendResponse({ ok: false, error: e?.message || String(e) }));
    return true;
  }
  if (message?.type === "MYRA_OFFSCREEN_STATUS") {
    sendResponse({ ok: true, polling: Boolean(pollTimer), inFlight: false, activePolls });
  }
});

syncPollingWithSettings().catch(e => console.warn("[MYRA Bridge Offscreen] startup err:", e?.message || e));
console.log("[MYRA Bridge Offscreen] documento pronto");

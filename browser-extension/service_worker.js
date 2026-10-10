const DEFAULT_API = "http://127.0.0.1:8000";

// Recria/garante o alarme sempre que o service worker é iniciado.
chrome.alarms.get("myra-bridge-poll", (alarm) => {
  if (!alarm) {
    chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
    console.log("[MYRA Bridge] alarme criado");
  }
});

// Open WebUI is the command source, not the page the user usually wants MYRA to inspect.
function isMyraUiTab(tab) {
  try {
    const url = new URL(tab?.url || "");
    const host = url.hostname.toLowerCase();
    const isLocalHost = ["localhost", "127.0.0.1", "::1", "[::1]"].includes(host);
    return isLocalHost && url.port === "8080";
  } catch {
    return false;
  }
}

async function getTargetTab(urlContains = "") {
  const needle = String(urlContains || "").trim().toLowerCase();

  // An explicit URL substring takes precedence over the active tab and searches
  // all Chrome windows, so MYRA can target one site among many open tabs.
  if (needle) {
    if (needle.length > 300) throw new Error("url_contains deve ter no máximo 300 caracteres.");
    const tabs = await chrome.tabs.query({});
    const matches = tabs
      .filter(tab => Number.isInteger(tab.id) && !isMyraUiTab(tab))
      .filter(tab => {
        try {
          const url = new URL(tab.url || "");
          return (url.protocol === "http:" || url.protocol === "https:") &&
            url.href.toLowerCase().includes(needle);
        } catch {
          return false;
        }
      })
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));

    if (matches.length) return matches[0];
    throw new Error(`Não encontrei nenhuma aba HTTP/HTTPS cuja URL contenha "${urlContains}". Confira o trecho e tente novamente.`);
  }

  const [active] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!active || !Number.isInteger(active.id)) {
    throw new Error("Nenhuma aba ativa encontrada no Chrome.");
  }
  if (!isMyraUiTab(active)) return active;

  // If the command was submitted from Open WebUI, select the most recently
  // accessed normal web page instead of reading MYRA's own prompt.
  const tabs = await chrome.tabs.query({ lastFocusedWindow: true });
  const candidates = tabs
    .filter(tab => Number.isInteger(tab.id) && !isMyraUiTab(tab))
    .filter(tab => {
      try {
        const url = new URL(tab.url || "");
        return url.protocol === "http:" || url.protocol === "https:";
      } catch {
        return false;
      }
    })
    .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));

  if (candidates.length) return candidates[0];
  throw new Error("A aba ativa é o Open WebUI e não encontrei outra página HTTP/HTTPS no Chrome para ler. Abra a página desejada e tente novamente.");
}

async function getSettings() {
  return await chrome.storage.local.get(["myraApi", "myraEnabled", "myraToken"]);
}

async function bridgeFetch(path, settings, options = {}) {
  const api = settings.myraApi || DEFAULT_API;
  const token = settings.myraToken || "";
  if (!token) throw new Error("Configure o token MYRA Browser Bridge na extensão.");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    return await fetch(api + path, {
      ...options,
      headers: { ...(options.headers || {}), "X-MYRA-BRIDGE-TOKEN": token },
      cache: "no-store",
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeout);
  }
}

async function executeBridgeCommand(command) {
  if (command.action === "read_active_tab") {
    const tab = await getTargetTab(command.args?.url_contains);
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => ({
        title: document.title,
        url: location.href,
        text: (document.body?.innerText || "").slice(0, 12000)
      })
    });
    return { ok: true, result };
  }

  if (command.action === "navigate_active_tab") {
    const tab = await getTargetTab();
    const url = new URL(String(command.args?.url || ""));
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("Somente URLs HTTP/HTTPS são permitidas.");
    await chrome.tabs.update(tab.id, { url: url.href });
    return { ok: true, result: { tabId: tab.id, url: url.href } };
  }

  if (command.action === "click_text") {
    const tab = await getTargetTab();
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (needle) => {
        const norm = s => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
        const target = norm(needle);
        const candidates = [...document.querySelectorAll("button,a,[role=button],input[type=button],input[type=submit]")];
        const el = candidates.find(e => {
          const style = getComputedStyle(e);
          return style.visibility !== "hidden" && style.display !== "none" &&
            norm(e.innerText || e.getAttribute("aria-label") || e.value) === target;
        });
        if (!el) return { ok: false, error: "Não encontrei botão/link visível com esse texto exato." };
        el.click();
        return { ok: true, result: { clicked: (el.innerText || el.getAttribute("aria-label") || el.value || "").slice(0, 200) } };
      },
      args: [String(command.args?.text || "")]
    });
    if (result?.ok === false) throw new Error(result.error || "O clique falhou.");
    return result || { ok: false, error: "A página não retornou resultado." };
  }

  throw new Error("Ação desconhecida ou não permitida: " + String(command.action));
}

async function pollOnce() {
  const settings = await getSettings();
  if (!settings.myraEnabled || !settings.myraToken) return;
  console.log("[MYRA Bridge] polling...");
  try {
    const response = await bridgeFetch("/browser_bridge/next?wait=5", settings);
    console.log("[MYRA Bridge] next HTTP", response.status);
    if (!response.ok) throw new Error("Backend Bridge respondeu HTTP " + response.status);
    const payload = await response.json();
    const command = payload.command;
    if (!command) return;
    console.log("[MYRA Bridge] comando:", command.action);
    let result;
    try {
      result = await executeBridgeCommand(command);
    } catch (error) {
      result = { ok: false, error: error?.message || String(error) };
    }
    await bridgeFetch("/browser_bridge/complete", settings, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command_id: command.command_id, result })
    });
    console.log("[MYRA Bridge] completado");
  } catch (error) {
    console.warn("[MYRA Bridge] erro:", error?.name, error?.message || error);
  }
}

async function startPolling() {
  try {
    await pollOnce();
  } catch (error) {
    console.warn("[MYRA Bridge]", error?.message || error);
  }
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.get("myra-bridge-poll", (alarm) => {
  if (!alarm) {
    chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
    console.log("[MYRA Bridge] alarme criado");
  }
});
});
chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.get("myra-bridge-poll", (alarm) => {
  if (!alarm) {
    chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
    console.log("[MYRA Bridge] alarme criado");
  }
});
});

// Cada alarme executa apenas uma rodada; o service worker pode ser suspenso entre elas.
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "myra-bridge-poll") return;
  try {
    await pollOnce();
  } catch (error) {
    console.warn("[MYRA Bridge]", error?.message || error);
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== "string") return;
  (async () => {
    try {
      if (message.type === "MYRA_GET_ACTIVE_TAB") {
        const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        sendResponse({ ok: true, tab: tab ? { id: tab.id, title: tab.title, url: tab.url } : null });
        return;
      }
      if (message.type === "MYRA_READ_ACTIVE_TAB") {
        const result = await executeBridgeCommand({ action: "read_active_tab", args: { url_contains: message.url_contains || "" } });
        sendResponse(result);
        return;
      }
      if (message.type === "MYRA_NAVIGATE_ACTIVE_TAB") {
        const result = await executeBridgeCommand({ action: "navigate_active_tab", args: { url: message.url } });
        sendResponse(result);
        return;
      }
      if (message.type === "MYRA_CLICK_TEXT") {
        const result = await executeBridgeCommand({ action: "click_text", args: { text: message.text } });
        sendResponse(result);
        return;
      }
      if (message.type === "MYRA_STATUS") {
        const data = await getSettings();
        sendResponse({ ok: true, api: data.myraApi || DEFAULT_API, enabled: Boolean(data.myraEnabled), hasToken: Boolean(data.myraToken) });
        return;
      }
      if (message.type === "MYRA_SAVE_SETTINGS") {
        const api = new URL(message.api || DEFAULT_API);
        if (api.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(api.hostname)) {
          throw new Error("Por segurança, a API deve usar http://localhost ou http://127.0.0.1.");
        }
        const token = String(message.token || "").trim();
        if (message.enabled && token.length < 24) {
          throw new Error("Informe um token local com pelo menos 24 caracteres.");
        }
        await chrome.storage.local.set({ myraApi: api.origin, myraToken: token, myraEnabled: Boolean(message.enabled) });
        if (message.enabled) startPolling();
        else pollRequested = false;
        sendResponse({ ok: true });
        return;
      }
    } catch (error) {
      sendResponse({ ok: false, error: error?.message || String(error) });
    }
  })();
  return true;
});

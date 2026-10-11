// ============================================================
// MYRA Browser Bridge - service worker
// Arquitetura: alarme + setInterval enquanto worker esta vivo
// ============================================================

const DEFAULT_API = "http://127.0.0.1:8000";
const POLL_WAIT = 5;          // segundos por long-poll
const POLL_ATTEMPTS = 3;      // tentativas por ciclo

let pollIntervalHandle = null;

// ---------- Helpers ----------

function isMyraUiTab(tab) {
  try {
    const url = new URL(tab?.url || "");
    const host = url.hostname.toLowerCase();
    const isLocal = ["localhost", "127.0.0.1", "::1", "[::1]"].includes(host);
    return isLocal && url.port === "8080";
  } catch { return false; }
}

async function getTargetTab(urlContains = "") {
  const needle = String(urlContains || "").trim().toLowerCase();
  if (needle) {
    if (needle.length > 300) throw new Error("url_contains muito longo.");
    const tabs = await chrome.tabs.query({});
    const matches = tabs
      .filter(t => Number.isInteger(t.id) && !isMyraUiTab(t))
      .filter(t => {
        try {
          const u = new URL(t.url || "");
          return (u.protocol === "http:" || u.protocol === "https:") &&
            u.href.toLowerCase().includes(needle);
        } catch { return false; }
      })
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
    if (matches.length) return matches[0];
    throw new Error(`Nenhuma aba HTTP/HTTPS com URL contendo "${urlContains}".`);
  }

  const [active] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
  if (!active || !Number.isInteger(active.id)) throw new Error("Nenhuma aba ativa.");
  if (!isMyraUiTab(active)) return active;

  const tabs = await chrome.tabs.query({ lastFocusedWindow: true });
  const candidates = tabs
    .filter(t => Number.isInteger(t.id) && !isMyraUiTab(t))
    .filter(t => {
      try {
        const u = new URL(t.url || "");
        return u.protocol === "http:" || u.protocol === "https:";
      } catch { return false; }
    })
    .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0));
  if (candidates.length) return candidates[0];
  throw new Error("Aba ativa eh o Open WebUI e nao ha outra pagina HTTP/HTTPS.");
}

async function getSettings() {
  return await chrome.storage.local.get(["myraApi", "myraEnabled", "myraToken"]);
}

async function bridgeFetch(path, settings, options = {}) {
  const api = settings.myraApi || DEFAULT_API;
  const token = settings.myraToken || "";
  if (!token) throw new Error("Token nao configurado.");
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

function waitForTabComplete(tabId, timeoutMs = 20000) {
  return new Promise(async (resolve, reject) => {
    let settled = false;
    const finish = (err) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      chrome.tabs.onUpdated.removeListener(onUpdated);
      chrome.tabs.onRemoved.removeListener(onRemoved);
      err ? reject(err) : resolve();
    };
    const onUpdated = (updatedId, changeInfo) => {
      if (updatedId === tabId && changeInfo.status === "complete") finish();
    };
    const onRemoved = removedId => {
      if (removedId === tabId) finish(new Error("Aba temporaria foi fechada antes de carregar."));
    };
    const timer = setTimeout(() => finish(new Error("TIMEOUT: a pagina nao carregou em 20 segundos.")), timeoutMs);
    chrome.tabs.onUpdated.addListener(onUpdated);
    chrome.tabs.onRemoved.addListener(onRemoved);
    try {
      const current = await chrome.tabs.get(tabId);
      if (current.status === "complete") finish();
    } catch (e) {
      finish(new Error("Nao foi possivel acompanhar o carregamento da aba: " + (e?.message || e)));
    }
  });
}

async function executeBridgeCommand(command) {
  if (command.action === "get_tabs") {
    const tabs = await chrome.tabs.query({});
    const visibleTabs = tabs
      .filter(tab => Number.isInteger(tab.id))
      .filter(tab => {
        try {
          const url = new URL(tab.url || "");
          if (url.protocol !== "http:" && url.protocol !== "https:") return false;
          const host = url.hostname.toLowerCase();
          if (host === "::1" || host === "[::1]") return false;
          if (["localhost", "127.0.0.1"].includes(host) && ["8080", "3000"].includes(url.port)) return false;
          return true;
        } catch {
          return false;
        }
      })
      .sort((a, b) => (b.lastAccessed || 0) - (a.lastAccessed || 0))
      .slice(0, 50)
      .map(tab => ({
        id: tab.id,
        title: tab.title || "",
        url: tab.url || "",
        active: Boolean(tab.active),
        windowId: tab.windowId
      }));
    return { ok: true, result: { tabs: visibleTabs } };
  }
  if (command.action === "read_active_tab") {
    const tab = await getTargetTab(command.args?.url_contains);
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const visible = el => {
          const s = getComputedStyle(el);
          return s.display !== "none" && s.visibility !== "hidden";
        };
        const links = [...document.querySelectorAll("a")]
          .filter(el => visible(el) && (el.innerText || "").trim() && el.href)
          .slice(0, 30)
          .map(el => ({ text: el.innerText.trim().slice(0, 160), href: el.href }));
        const buttons = [...document.querySelectorAll("button,[role=button],input[type=button],input[type=submit]")]
          .filter(el => visible(el))
          .map(el => (el.innerText || el.getAttribute("aria-label") || el.value || "").trim())
          .filter(Boolean).slice(0, 20);
        const inputs = [...document.querySelectorAll("input,textarea")]
          .filter(el => visible(el))
          .slice(0, 15)
          .map(el => ({ placeholder: el.getAttribute("placeholder") || "", name: el.getAttribute("name") || "", type: el.getAttribute("type") || "text" }))
          .filter(el => el.placeholder || el.name);

          const tables = [...document.querySelectorAll("table")]
            .slice(0, 5)
            .map(table => {
              const rows = [...table.querySelectorAll("tr")]
                .slice(0, 50)
                .map(tr => [...tr.querySelectorAll("th,td")]
                  .slice(0, 10)
                  .map(cell => (cell.innerText || cell.textContent || "")
                    .replace(/\s+/g, " ").trim().slice(0, 300)))
                .filter(row => row.length >= 2 && row.filter(cell => cell).length >= 2);
              return {
                caption: (table.caption?.innerText || table.getAttribute("aria-label") || "").trim().slice(0, 300),
                rows
              };
            })
            .filter(table => table.rows.length >= 2);
        return {
          title: document.title,
          url: location.href,
          text: (document.body?.innerText || "").slice(0, 12000),
          links,
          buttons,
          inputs,
          tables
        };
      }
    });
    return { ok: true, result };
  }
  if (command.action === "read_page_url") {
    const rawUrl = String(command.args?.url || "").trim();
    const parsed = new URL(rawUrl);
    if (!["http:", "https:"].includes(parsed.protocol)) throw new Error("Somente URLs HTTP/HTTPS podem ser lidas.");
    let tempTab = null;
    try {
      tempTab = await chrome.tabs.create({ url: parsed.href, active: false });
      await waitForTabComplete(tempTab.id, 20000);
      const [{ result }] = await chrome.scripting.executeScript({
        target: { tabId: tempTab.id },
        func: () => {
          const visible = el => {
            const s = getComputedStyle(el);
            return s.display !== "none" && s.visibility !== "hidden";
          };
          const links = [...document.querySelectorAll("a")]
            .filter(el => visible(el) && (el.innerText || "").trim() && el.href)
            .slice(0, 30)
            .map(el => ({ text: el.innerText.trim().slice(0, 160), href: el.href }));

          const tables = [...document.querySelectorAll("table")]
            .slice(0, 5)
            .map(table => {
              const rows = [...table.querySelectorAll("tr")]
                .slice(0, 50)
                .map(tr => [...tr.querySelectorAll("th,td")]
                  .slice(0, 10)
                  .map(cell => (cell.innerText || cell.textContent || "")
                    .replace(/\s+/g, " ").trim().slice(0, 300)))
                .filter(row => row.length >= 2 && row.filter(cell => cell).length >= 2);
              return {
                caption: (table.caption?.innerText || table.getAttribute("aria-label") || "").trim().slice(0, 300),
                rows
              };
            })
            .filter(table => table.rows.length >= 2);
          return {
            title: document.title,
            url: location.href,
            text: (document.body?.innerText || "").slice(0, 12000),
            links,
            buttons: [...document.querySelectorAll("button,[role=button],input[type=button],input[type=submit]")]
              .filter(el => visible(el))
              .map(el => (el.innerText || el.getAttribute("aria-label") || el.value || "").trim())
              .filter(Boolean).slice(0, 20),
            inputs: [...document.querySelectorAll("input,textarea")]
              .filter(el => visible(el)).slice(0, 15)
              .map(el => ({ placeholder: el.getAttribute("placeholder") || "", name: el.getAttribute("name") || "", type: el.getAttribute("type") || "text" }))
              .filter(el => el.placeholder || el.name),
            tables
          };
        }
      });
      return { ok: true, result };
    } finally {
      if (tempTab?.id != null) {
        try { await chrome.tabs.remove(tempTab.id); } catch (e) {
          console.warn("[MYRA Bridge] nao foi possivel fechar aba temporaria:", e?.message || e);
        }
      }
    }
  }
  if (command.action === "navigate_active_tab") {
    const tab = await getTargetTab();
    const url = new URL(String(command.args?.url || ""));
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("Somente HTTP/HTTPS.");
    await chrome.tabs.update(tab.id, { url: url.href });
    return { ok: true, result: { tabId: tab.id, url: url.href } };
  }
  if (command.action === "click_text") {
    const tab = await getTargetTab();
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (needle) => {
        const norm = s => (s || "").replace(/\s+/g, " ").trim().toLowerCase();
        const target = norm(needle);
        const candidates = [...document.querySelectorAll("button,a,[role=button],input[type=button],input[type=submit]")];
        const el = candidates.find(e => {
          const st = getComputedStyle(e);
          return st.visibility !== "hidden" && st.display !== "none" &&
            norm(e.innerText || e.getAttribute("aria-label") || e.value) === target;
        });
        if (!el) return { ok: false, error: "Botao/link nao encontrado." };
        el.click();
        return { ok: true, result: { clicked: (el.innerText || "").slice(0, 200) } };
      },
      args: [String(command.args?.text || "")]
    });
    if (result?.ok === false) throw new Error(result.error || "Clique falhou.");
    return result || { ok: false, error: "Sem resultado." };
  }
  throw new Error("Acao desconhecida: " + String(command.action));
}

// ---------- Polling ----------

async function pollOnce() {
  const settings = await getSettings();
  if (!settings.myraEnabled || !settings.myraToken) return;

  for (let attempt = 0; attempt < POLL_ATTEMPTS; attempt++) {
    console.log("[MYRA Bridge] poll tentativa", attempt + 1);
    try {
      const res = await bridgeFetch("/browser_bridge/next?wait=" + POLL_WAIT, settings);
      console.log("[MYRA Bridge] next HTTP", res.status);
      if (!res.ok) throw new Error("HTTP " + res.status);
      const payload = await res.json();
      const cmd = payload.command;
      if (!cmd) continue;
      console.log("[MYRA Bridge] comando:", cmd.action);
      let result;
      try { result = await executeBridgeCommand(cmd); }
      catch (e) { result = { ok: false, error: e?.message || String(e) }; }
      await bridgeFetch("/browser_bridge/complete", settings, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_id: cmd.command_id, result })
      });
      console.log("[MYRA Bridge] completado");
      return;
    } catch (e) {
      console.warn("[MYRA Bridge] erro:", e?.name, e?.message || e);
      return;
    }
  }
}

function startInterval() {
  if (pollIntervalHandle) return;
  console.log("[MYRA Bridge] iniciando setInterval");
  pollIntervalHandle = setInterval(() => {
    pollOnce().catch(e => console.warn("[MYRA Bridge] interval err:", e?.message || e));
  }, 5000);
  // Roda uma vez imediatamente
  pollOnce().catch(e => console.warn("[MYRA Bridge] initial err:", e?.message || e));
}

function stopInterval() {
  if (pollIntervalHandle) {
    clearInterval(pollIntervalHandle);
    pollIntervalHandle = null;
    console.log("[MYRA Bridge] parado setInterval");
  }
}

// ---------- Registro do alarme (backup) ----------

chrome.alarms.get("myra-bridge-poll", (alarm) => {
  if (!alarm) {
    chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
    console.log("[MYRA Bridge] alarme criado");
  }
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.get("myra-bridge-poll", (alarm) => {
    if (!alarm) chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
  });
});

chrome.runtime.onStartup.addListener(() => {
  chrome.alarms.get("myra-bridge-poll", (alarm) => {
    if (!alarm) chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
  });
  startInterval();
});

chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name !== "myra-bridge-poll") return;
  console.log("[MYRA Bridge] alarme disparou");
  // Garante que o interval ta vivo (Chrome pode ter suspenso)
  startInterval();
});

// ---------- Mensagens do popup ----------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== "string") return;
  (async () => {
    try {
      if (message.type === "MYRA_STATUS") {
        const d = await getSettings();
        sendResponse({ ok: true, api: d.myraApi || DEFAULT_API, enabled: Boolean(d.myraEnabled), hasToken: Boolean(d.myraToken) });
        return;
      }
      if (message.type === "MYRA_SAVE_SETTINGS") {
        const api = new URL(message.api || DEFAULT_API);
        if (api.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(api.hostname)) {
          throw new Error("API deve ser http://localhost ou http://127.0.0.1.");
        }
        const token = String(message.token || "").trim();
        if (message.enabled && token.length < 24) throw new Error("Token curto (min 24).");
        await chrome.storage.local.set({ myraApi: api.origin, myraToken: token, myraEnabled: Boolean(message.enabled) });
        if (message.enabled) startInterval(); else stopInterval();
        sendResponse({ ok: true });
        return;
      }
      if (message.type === "MYRA_READ_ACTIVE_TAB") {
        sendResponse(await executeBridgeCommand({ action: "read_active_tab", args: { url_contains: message.url_contains || "" } }));
        return;
      }
      if (message.type === "MYRA_NAVIGATE_ACTIVE_TAB") {
        sendResponse(await executeBridgeCommand({ action: "navigate_active_tab", args: { url: message.url } }));
        return;
      }
      if (message.type === "MYRA_CLICK_TEXT") {
        sendResponse(await executeBridgeCommand({ action: "click_text", args: { text: message.text } }));
        return;
      }
    } catch (e) {
      sendResponse({ ok: false, error: e?.message || String(e) });
    }
  })();
  return true;
});

// ---------- Arranque ----------
// Roda toda vez que o worker acorda
startInterval();
console.log("[MYRA Bridge] service worker pronto");
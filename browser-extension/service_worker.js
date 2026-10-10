const DEFAULT_API = "http://127.0.0.1:8000";

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
        const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        if (!tab || !Number.isInteger(tab.id)) throw new Error("Nenhuma aba ativa encontrada.");
        const [{ result }] = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: () => ({
            title: document.title,
            url: location.href,
            text: (document.body?.innerText || "").slice(0, 12000)
          })
        });
        sendResponse({ ok: true, result });
        return;
      }
      if (message.type === "MYRA_NAVIGATE_ACTIVE_TAB") {
        const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        if (!tab || !Number.isInteger(tab.id)) throw new Error("Nenhuma aba ativa encontrada.");
        const url = new URL(message.url);
        if (!["http:", "https:"].includes(url.protocol)) throw new Error("Somente URLs HTTP/HTTPS são permitidas.");
        await chrome.tabs.update(tab.id, { url: url.href });
        sendResponse({ ok: true, tabId: tab.id, url: url.href });
        return;
      }
      if (message.type === "MYRA_CLICK_TEXT") {
        const [tab] = await chrome.tabs.query({ active: true, lastFocusedWindow: true });
        if (!tab || !Number.isInteger(tab.id)) throw new Error("Nenhuma aba ativa encontrada.");
        const result = await chrome.scripting.executeScript({
          target: { tabId: tab.id },
          func: (needle) => {
            const norm = s => (s || "").replace(/\\s+/g, " ").trim().toLowerCase();
            const target = norm(needle);
            const candidates = [...document.querySelectorAll("button,a,[role=button],input[type=button],input[type=submit]")];
            const el = candidates.find(e => norm(e.innerText || e.getAttribute("aria-label") || e.value) === target);
            if (!el) return { ok: false, error: "Não encontrei um botão ou link com esse texto." };
            el.click();
            return { ok: true, clicked: (el.innerText || el.getAttribute("aria-label") || el.value || "").slice(0, 200) };
          },
          args: [String(message.text || "")]
        });
        sendResponse(result?.[0]?.result || { ok: false, error: "Sem resultado da página." });
        return;
      }
      if (message.type === "MYRA_STATUS") {
        const data = await chrome.storage.local.get(["myraApi", "myraEnabled"]);
        sendResponse({ ok: true, api: data.myraApi || DEFAULT_API, enabled: Boolean(data.myraEnabled) });
        return;
      }
      if (message.type === "MYRA_SAVE_SETTINGS") {
        const api = new URL(message.api || DEFAULT_API);
        if (!["http:", "https:"].includes(api.protocol) || !["127.0.0.1", "localhost"].includes(api.hostname)) {
          throw new Error("Por segurança, a API deve apontar para localhost ou 127.0.0.1.");
        }
        await chrome.storage.local.set({ myraApi: api.origin, myraEnabled: Boolean(message.enabled) });
        sendResponse({ ok: true });
      }
    } catch (error) {
      sendResponse({ ok: false, error: error?.message || String(error) });
    }
  })();
  return true;
});

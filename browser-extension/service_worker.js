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
  const data = await chrome.storage.local.get(["myraApi", "myraEnabled", "myraToken"]);
  // Persistencia: se o token existe mas enabled nunca foi setado,
  // assume true e grava no storage (nao perde mais ao recarregar)
  if (data.myraToken && data.myraEnabled !== true) {
    data.myraEnabled = true;
    try { await chrome.storage.local.set({ myraEnabled: true }); } catch (e) {}
  }
  return data;
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
  if (command.action === "new_tab") {
    const rawUrl = String(command.args?.url || "").trim();
    let url;
    try {
      url = new URL(rawUrl);
    } catch {
      throw new Error("URL inválida. Informe uma URL HTTP/HTTPS completa.");
    }
    if (!["http:", "https:"].includes(url.protocol)) {
      throw new Error("Somente URLs HTTP/HTTPS podem ser abertas em nova aba.");
    }
    const tab = await chrome.tabs.create({ url: url.href, active: true });
    try {
      await waitForTabComplete(tab.id, 20000);
    } catch (e) {
      return {
        ok: true,
        result: {
          tabId: tab.id,
          url: tab.url || url.href,
          loaded: false,
          warning: e?.message || String(e)
        }
      };
    }
    const loadedTab = await chrome.tabs.get(tab.id);
    return {
      ok: true,
      result: {
        tabId: loadedTab.id,
        url: loadedTab.url || url.href,
        title: loadedTab.title || "",
        loaded: true
      }
    };
  }
  if (command.action === "search_google_visivel") {
    const term = String(command.args?.term || "").trim();
    const delayTypingMs = Number(command.args?.delay_typing_ms ?? 150);
    const scrollSuave = command.args?.scroll_suave !== false;
    if (!term || term.length > 200) {
      throw new Error("termo deve conter de 1 a 200 caracteres.");
    }
    if (!Number.isFinite(delayTypingMs) || delayTypingMs < 0 || delayTypingMs > 1000) {
      throw new Error("delay_typing_ms deve estar entre 0 e 1000.");
    }

    const tab = await chrome.tabs.create({ url: "https://www.google.com", active: true });
    const tabId = tab.id;
    try {
      await waitForTabComplete(tabId, 20000);
    } catch (e) {
      const current = await chrome.tabs.get(tabId).catch(() => null);
      throw new Error(
        "Google não carregou em 20 segundos. URL atual: " +
        (current?.url || tab.url || "desconhecida") + ". " + (e?.message || String(e))
      );
    }

    const initialTab = await chrome.tabs.get(tabId);
    const initialUrl = initialTab.url || "https://www.google.com";
    const typing = await chrome.scripting.executeScript({
      target: { tabId },
      func: async (searchTerm, delayMs) => {
        const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
        const el = document.querySelector('input[name="q"], textarea[name="q"]');
        if (!el) {
          return { ok: false, error: "Caixa de busca do Google não encontrada (input[name=q] ou textarea[name=q])." };
        }
        if (el.disabled || el.readOnly) {
          return { ok: false, error: "A caixa de busca do Google está desabilitada ou somente leitura." };
        }

        el.focus();
        const setter = el instanceof HTMLTextAreaElement
          ? Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")?.set
          : Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set;
        if (setter) setter.call(el, "");
        else el.value = "";
        el.dispatchEvent(new InputEvent("input", {
          bubbles: true, inputType: "deleteContentBackward", data: null
        }));

        for (const char of searchTerm) {
          const key = char.length === 1 ? char : "Unidentified";
          const code = char.length === 1 && /^[a-z]$/i.test(char)
            ? "Key" + char.toUpperCase()
            : char === " " ? "Space" : "Unidentified";
          const keyCode = char.length === 1 ? char.toUpperCase().charCodeAt(0) : 0;
          el.dispatchEvent(new KeyboardEvent("keydown", {
            key, code, keyCode, which: keyCode, bubbles: true, cancelable: true
          }));
          el.dispatchEvent(new InputEvent("beforeinput", {
            inputType: "insertText", data: char, bubbles: true, cancelable: true
          }));
          const current = String(el.value || "");
          if (setter) setter.call(el, current + char);
          else el.value = current + char;
          el.dispatchEvent(new InputEvent("input", {
            inputType: "insertText", data: char, bubbles: true
          }));
          el.dispatchEvent(new KeyboardEvent("keyup", {
            key, code, keyCode, which: keyCode, bubbles: true
          }));
          if (delayMs > 0) await sleep(delayMs);
        }

        await sleep(300);
        for (const type of ["keydown", "keypress", "keyup"]) {
          el.dispatchEvent(new KeyboardEvent(type, {
            key: "Enter", code: "Enter", keyCode: 13, which: 13,
            bubbles: true, cancelable: true
          }));
        }
        const form = el.form || el.closest("form");
        if (!form) return { ok: false, error: "A caixa de busca foi encontrada, mas não pertence a um formulário." };
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.submit();
        return { ok: true, typed: searchTerm, submitted: true };
      },
      args: [term, delayTypingMs]
    });

    const typingResult = typing?.[0]?.result;
    if (!typingResult?.ok) {
      throw new Error(typingResult?.error || "Não foi possível digitar e enviar a pesquisa no Google.");
    }

    try {
      await new Promise((resolve, reject) => {
        let settled = false;
        const finish = (error) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          chrome.tabs.onUpdated.removeListener(onUpdated);
          chrome.tabs.onRemoved.removeListener(onRemoved);
          error ? reject(error) : resolve();
        };
        const onUpdated = async (updatedId, changeInfo) => {
          if (updatedId !== tabId || changeInfo.status !== "complete") return;
          try {
            const current = await chrome.tabs.get(tabId);
            if (current.url && current.url !== initialUrl) finish();
          } catch (e) {
            finish(new Error("Não foi possível verificar a página de resultados."));
          }
        };
        const onRemoved = removedId => {
          if (removedId === tabId) finish(new Error("A aba do Google foi fechada antes de carregar os resultados."));
        };
        const timer = setTimeout(async () => {
          const current = await chrome.tabs.get(tabId).catch(() => null);
          finish(new Error(
            "TIMEOUT: os resultados do Google não carregaram em 20 segundos. URL atual: " +
            (current?.url || "desconhecida")
          ));
        }, 20000);
        chrome.tabs.onUpdated.addListener(onUpdated);
        chrome.tabs.onRemoved.addListener(onRemoved);
      });
    } catch (e) {
      const current = await chrome.tabs.get(tabId).catch(() => null);
      throw new Error((e?.message || String(e)) + " URL atual: " + (current?.url || "desconhecida"));
    }

    if (scrollSuave) {
      await new Promise(resolve => setTimeout(resolve, 500));
      await chrome.scripting.executeScript({
        target: { tabId },
        func: async () => {
          const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
          let previousHeight = 0;
          let stableHeightSteps = 0;
          for (let step = 0; step < 500; step++) {
            const height = Math.max(
              document.documentElement?.scrollHeight || 0,
              document.body?.scrollHeight || 0
            );
            if (height === previousHeight) stableHeightSteps++;
            else stableHeightSteps = 0;
            previousHeight = height;
            const y = Math.min(window.scrollY + 200, height);
            window.scrollTo({ top: y, behavior: "smooth" });
            await sleep(50);
            if (y >= height && stableHeightSteps >= 2) break;
          }
          window.scrollTo({ top: 0, behavior: "smooth" });
          await sleep(250);
          return { scrollHeight: previousHeight, returnedToTop: window.scrollY < 100 };
        }
      });
    }

    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const visible = el => {
          const style = getComputedStyle(el);
          return style.display !== "none" && style.visibility !== "hidden";
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
            .map(el => ({
              placeholder: el.getAttribute("placeholder") || "",
              name: el.getAttribute("name") || "",
              type: el.getAttribute("type") || "text"
            }))
            .filter(el => el.placeholder || el.name),
          tables
        };
      }
    });
    return { ok: true, result: { ...result, tabId, visible: true } };
  }

  if (command.action === "search_google") {
    const term = String(command.args?.term || "").trim();
    if (!term || term.length > 200) {
      throw new Error("termo deve conter de 1 a 200 caracteres.");
    }
    const searchUrl = "https://www.google.com/search?" + new URLSearchParams({ q: term }).toString();
    // Reutiliza o mesmo fluxo seguro de leitura: aguarda o carregamento,
    // extrai title/url/text/links/tables e fecha a aba temporária em finally.
    return await executeBridgeCommand({ action: "read_page_url", args: { url: searchUrl } });
  }
  if (command.action === "scroll") {
    const direction = String(command.args?.direction || "down").toLowerCase();
    const rawAmount = command.args?.amount;
    const amount = rawAmount === undefined || rawAmount === null ? 500 : Number(rawAmount);
    if (!["up", "down", "top", "bottom"].includes(direction)) {
      throw new Error('direcao deve ser "up", "down", "top" ou "bottom".');
    }
    if (!Number.isFinite(amount) || amount < 0 || amount > 100000) {
      throw new Error("quantidade deve ser um número entre 0 e 100000 pixels.");
    }
    const tab = await getTargetTab();
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (direction, amount) => {
        if (direction === "top") window.scrollTo({ top: 0, behavior: "instant" });
        else if (direction === "bottom") window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "instant" });
        else window.scrollBy({ top: direction === "up" ? -amount : amount, behavior: "instant" });
        return { scrolled: true, scrollY: Math.round(window.scrollY), direction };
      },
      args: [direction, amount]
    });
    return { ok: true, result };
  }
  if (command.action === "close_tab") {
    const rawTabId = command.args?.tab_id;
    let tab;
    if (rawTabId === undefined || rawTabId === null || rawTabId === "") {
      tab = await getTargetTab();
    } else {
      const tabId = Number(rawTabId);
      if (!Number.isSafeInteger(tabId) || tabId <= 0) {
        throw new Error("tab_id inválido: informe o ID numérico retornado por browser_get_tabs.");
      }
      tab = await chrome.tabs.get(tabId);
    }
    if (!Number.isInteger(tab.id)) throw new Error("Aba inválida.");
    let url;
    try { url = new URL(tab.url || ""); } catch { throw new Error("Aba sem URL HTTP/HTTPS válida; não será fechada."); }
    if (!["http:", "https:"].includes(url.protocol) || isMyraUiTab(tab)) {
      throw new Error("Por segurança, só é permitido fechar abas HTTP/HTTPS de sites, não páginas internas do navegador ou do MYRA.");
    }
    const closed = { tabId: tab.id, url: tab.url || "", title: tab.title || "" };
    await chrome.tabs.remove(tab.id);
    return { ok: true, result: { ...closed, closed: true } };
  }
  if (command.action === "navigate_active_tab") {
    const tab = await getTargetTab();
    const url = new URL(String(command.args?.url || ""));
    if (!["http:", "https:"].includes(url.protocol)) throw new Error("Somente HTTP/HTTPS.");
    await chrome.tabs.update(tab.id, { url: url.href });
    return { ok: true, result: { tabId: tab.id, url: url.href } };
  }
  if (command.action === "type_text") {
    const tab = await getTargetTab();
    const campo = String(command.args?.campo || "").trim();
    const texto = String(command.args?.texto ?? "");
    if (!campo) throw new Error("Informe campo como seletor CSS ou label acessível.");
    if (campo.length > 500) throw new Error("campo deve ter no máximo 500 caracteres.");
    if (texto.length > 5000) throw new Error("texto deve ter no máximo 5000 caracteres.");
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (campo, texto) => {
        const norm = s => String(s || "").replace(/\s+/g, " ").trim().toLocaleLowerCase();
        const pareceSeletor = campo.startsWith("#") || campo.startsWith(".") ||
          campo.startsWith("[") || campo.includes("=");
        let matches = [];
        if (pareceSeletor) {
          try {
            matches = [...document.querySelectorAll(campo)];
          } catch (e) {
            return { ok: false, error: "Seletor CSS inválido: " + (e?.message || String(e)) };
          }
        } else {
          const labels = [...document.querySelectorAll("label")]
            .filter(label => norm(label.innerText || label.textContent) === norm(campo));
          if (labels.length > 1) {
            return { ok: false, error: "Label ambíguo: mais de um label corresponde a '" + campo + "'." };
          }
          if (labels.length === 1) {
            const label = labels[0];
            const id = label.getAttribute("for");
            const control = id ? document.getElementById(id) : label.control;
            if (control) matches = [control];
          }
        }
        if (matches.length === 0) {
          return { ok: false, error: "Campo não encontrado para: '" + campo + "'." };
        }
        if (matches.length > 1) {
          return { ok: false, error: "Campo ambíguo: o seletor '" + campo + "' corresponde a " + matches.length + " elementos." };
        }
        const el = matches[0];
        if (!("value" in el)) {
          return { ok: false, error: "O elemento encontrado não aceita texto (não possui propriedade value)." };
        }
        if (el.disabled || el.readOnly) {
          return { ok: false, error: "O campo está desabilitado ou somente leitura." };
        }
        el.focus();
        const proto = el instanceof HTMLTextAreaElement
          ? HTMLTextAreaElement.prototype
          : el instanceof HTMLInputElement
            ? HTMLInputElement.prototype
            : null;
        const setter = proto && Object.getOwnPropertyDescriptor(proto, "value")?.set;
        if (setter) setter.call(el, "");
        else el.value = "";
        if (setter) setter.call(el, texto);
        else el.value = texto;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
        return { ok: true, result: { field: campo, typed: texto } };
      },
      args: [campo, texto]
    });
    if (result?.ok === false) throw new Error(result.error || "Não foi possível digitar no campo.");
    return result || { ok: false, error: "Sem resultado ao digitar no campo." };
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

// ---------- Offscreen polling ----------

// O polling vive no offscreen document; o service worker só acorda para
// executar comandos da extensão ou para garantir que o offscreen exista.
let ensureOffscreenPromise = null;

async function ensureOffscreenDocument() {
  if (!chrome.offscreen) {
    throw new Error("chrome.offscreen indisponível. Atualize o Chrome para uma versão compatível.");
  }
  if (ensureOffscreenPromise) return ensureOffscreenPromise;
  ensureOffscreenPromise = (async () => {
    const exists = await chrome.offscreen.hasDocument();
    if (!exists) {
      await chrome.offscreen.createDocument({
        url: "offscreen.html",
        reasons: ["WORKERS"],
        justification: "Manter o polling do Browser Bridge ativo enquanto o service worker MV3 estiver suspenso."
      });
      console.log("[MYRA Bridge] offscreen document criado");
    }
  })();
  try {
    await ensureOffscreenPromise;
  } finally {
    ensureOffscreenPromise = null;
  }
}

function startInterval() {
  ensureOffscreenDocument()
    .then(() => console.log("[MYRA Bridge] polling delegado ao offscreen document"))
    .catch(e => console.warn("[MYRA Bridge] falha ao iniciar offscreen:", e?.message || e));
}

function stopInterval() {
  // A mudança de myraEnabled no chrome.storage.local é observada pelo offscreen.
  // Nenhum timer do service worker precisa ser limpo.
  console.log("[MYRA Bridge] polling será pausado pelo offscreen conforme as configurações");
}

// Recria o offscreen quando a extensão instala/atualiza ou o Chrome inicia.
chrome.runtime.onInstalled.addListener(() => startInterval());
chrome.runtime.onStartup.addListener(() => startInterval());
chrome.alarms.get("myra-bridge-poll", (alarm) => {
  if (!alarm) chrome.alarms.create("myra-bridge-poll", { periodInMinutes: 0.5 });
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
});
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "myra-bridge-poll") startInterval();
});

// ---------- Mensagens do popup ----------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message.type !== "string") return;
  (async () => {
    try {
      if (message.type === "MYRA_EXECUTE_COMMAND") {
        try {
          const result = await executeBridgeCommand(message.command || {});
          sendResponse({ ok: true, result });
        } catch (e) {
          sendResponse({ ok: false, error: e?.message || String(e) });
        }
        return;
      }
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
// Roda toda vez que o worker acorda e garante o documento de polling.
startInterval();
console.log("[MYRA Bridge] service worker pronto");
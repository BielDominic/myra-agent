const $ = (id) => document.getElementById(id);
const show = (value) => { $("result").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2); };
const send = (message) => new Promise((resolve) => chrome.runtime.sendMessage(message, resolve));

(async () => {
  const status = await send({ type: "MYRA_STATUS" });
  if (status?.ok) {
    $("api").value = status.api;
    $("enabled").checked = status.enabled;
  }
})();

$("save").addEventListener("click", async () => {
  const enabled = $("enabled").checked;
  if (enabled) {
    const granted = await chrome.permissions.request({ origins: ["http://*/*", "https://*/*"] });
    if (!granted) {
      show("Permissão de acesso às páginas não concedida. A integração automática não foi habilitada.");
      return;
    }
  }
  const result = await send({
    type: "MYRA_SAVE_SETTINGS",
    api: $("api").value.trim(),
    token: $("token").value.trim(),
    enabled
  });
  show(result?.ok ? "Configuração salva. A integração está habilitada." : result?.error || "Falha ao salvar.");
});
$("read").addEventListener("click", async () => {
  show(await send({ type: "MYRA_READ_ACTIVE_TAB" }));
});
$("navigate").addEventListener("click", async () => {
  show(await send({ type: "MYRA_NAVIGATE_ACTIVE_TAB", url: $("url").value.trim() }));
});
$("click").addEventListener("click", async () => {
  show(await send({ type: "MYRA_CLICK_TEXT", text: $("text").value }));
});

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
  const result = await send({
    type: "MYRA_SAVE_SETTINGS",
    api: $("api").value.trim(),
    token: $("token").value.trim(),
    enabled: $("enabled").checked
  });
  show(result?.ok ? "Configuração salva. A extensão está conectada enquanto o Chrome mantiver o serviço ativo." : result?.error || "Falha ao salvar.");
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

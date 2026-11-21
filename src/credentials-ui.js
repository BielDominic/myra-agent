(() => {
  const API = "http://127.0.0.1:8000";
  const $ = id => document.getElementById(id);
  const service = () => $("credential-service").value === "custom"
    ? $("credential-custom").value.trim().toLowerCase()
    : $("credential-service").value;

  function updateFields() {
    const selected = $("credential-service").value;
    const custom = selected === "custom";
    $("credential-custom-wrap").hidden = !custom;
    $("credential-user-label").textContent = selected === "telegram"
      ? "IDs de chats autorizados (separados por vírgula)"
      : selected === "gmail" ? "Conta Gmail" : "Usuário / identificador (opcional)";
    $("credential-username").placeholder = selected === "telegram"
      ? "123456789, 987654321" : selected === "gmail" ? "voce@gmail.com" : "Identificador da conta";
    $("credential-secret-label").textContent = selected === "telegram"
      ? "Token do bot" : "Segredo / senha de aplicativo";
    $("credential-hint").textContent = selected === "gmail"
      ? "Use uma senha de app do Google com IMAP/SMTP ativados. Não use sua senha normal. Gmail OAuth será implementado para escopos mais amplos."
      : selected === "telegram"
        ? "Informe o token do BotFather e os IDs numéricos autorizados. Após salvar, reinicie o backend da MYRA para carregar o bot."
        : "O segredo será criptografado localmente. Salvar não conecta automaticamente um app sem um adaptador específico.";
  }

  async function refresh() {
    const host = $("credential-list");
    if (!host) return;
    host.replaceChildren();
    try {
      const response = await fetch(API + "/credentials", { cache: "no-store" });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Cofre indisponível");
      const entries = data.credentials || [];
      if (!entries.length) {
        const empty = document.createElement("p");
        empty.className = "muted-note";
        empty.textContent = "Nenhuma credencial salva.";
        host.append(empty);
        return;
      }
      entries.forEach(item => {
        const row = document.createElement("div");
        row.className = "credential-row";
        const info = document.createElement("div");
        const title = document.createElement("strong");
        const detail = document.createElement("small");
        const remove = document.createElement("button");
        title.textContent = item.label || item.service;
        detail.textContent = item.service.toUpperCase() + " · " +
          (item.username || "sem identificador") + " · segredo protegido";
        info.append(title, detail);
        remove.type = "button";
        remove.className = "soft-button danger-button";
        remove.textContent = "Excluir";
        remove.addEventListener("click", async () => {
          if (!confirm("Excluir esta credencial do cofre local?")) return;
          remove.disabled = true;
          try {
            const result = await fetch(API + "/credentials/" +
              encodeURIComponent(item.service), { method: "DELETE" });
            const body = await result.json().catch(() => ({}));
            if (!result.ok) throw new Error(body.detail || "Falha ao excluir");
            await refresh();
          } catch (error) {
            remove.disabled = false;
            alert(error.message);
          }
        });
        row.append(info, remove);
        host.append(row);
      });
    } catch (error) {
      const p = document.createElement("p");
      p.className = "muted-note";
      p.textContent = "Erro ao consultar cofre: " + error.message;
      host.append(p);
    }
  }

  async function save() {
    const serviceId = service();
    const secret = $("credential-secret").value;
    const status = $("credential-save-status");
    const button = $("credential-save");
    if (!serviceId || !secret.trim()) {
      status.textContent = "Informe o serviço e o segredo antes de salvar.";
      return;
    }
    button.disabled = true;
    status.textContent = "Criptografando e salvando no cofre do Windows...";
    try {
      const response = await fetch(API + "/credentials", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          service: serviceId,
          label: $("credential-label").value.trim(),
          username: $("credential-username").value.trim(),
          secret
        })
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || "Não foi possível salvar");
      $("credential-secret").value = "";
      status.textContent = serviceId === "telegram"
        ? "Credencial protegida. Reinicie o backend para carregar o bot."
        : serviceId === "gmail"
          ? "Credencial protegida e disponível para as funções de e-mail Gmail."
          : "Credencial protegida. O conector específico ainda precisa ser configurado.";
      await refresh();
    } catch (error) {
      status.textContent = "Falha: " + error.message;
    } finally {
      button.disabled = false;
    }
  }

  $("credential-service")?.addEventListener("change", updateFields);
  $("credential-save")?.addEventListener("click", save);
  $("credential-refresh")?.addEventListener("click", refresh);
  window.refreshMyraCredentials = refresh;
  updateFields();
})();

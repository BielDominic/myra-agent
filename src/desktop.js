(() => {
  const API = "http://127.0.0.1:8000";
  const STORAGE_KEY = "myra-desktop-conversations-v2";
  const CODE_KEY = "myra-code-studio-v1";
  const PROJECT_KEY = "myra-projects-v1";
  const PREF_KEY = "myra-desktop-prefs-v1";
  const QUEUE_KEY = "myra-desktop-message-queue-v1";
  const $ = id => document.getElementById(id);
  let conversations = load(STORAGE_KEY, []);
  let projects = load(PROJECT_KEY, []);
  let activeId = conversations[0]?.id || null;
  let busy = false, online = false, executionMode = false, selectedModel = "", taskModelLocked = false;
  let imageGenerationBusy = false, imageEditBusy = false, voiceStarting = false, voiceTranscriptionBusy = false, voiceReadBusy = false;
  const GITHUB_PROJECT_PATH_KEY = "myra-github-project-path-v1";
  let historySelectionMode = false;
  let historyFilter = "";
  const selectedConversationIds = new Set();
  const activeSkills = new Set();
  let mediaRecorder = null, recordedChunks = [], voiceLoopActive = false, liveVoiceMode = false, speakNextResponse = false, liveVadContext = null, liveVadFrame = 0;
  let runtimeConfig = null, voiceAudio = null;
  let wakeStream=null,wakeContext=null,wakeAnalyser=null,wakeFrame=0,wakeRecorder=null,wakeChunks=[],wakeLastVoice=0,wakeStartedAt=0,wakeArmed=false,wakeActive=false,wakeBusy=false,wakeAbortController=null;
  let pendingImages = [];
  let pendingDocuments = [];
  const CHAT_AGENTS={general:"Voc\u00ea \u00e9 MYRA, assistente local generalista. Use ferramentas autorizadas quando a pessoa pedir a\u00e7\u00f5es.",developer:"Voc\u00ea \u00e9 a agente programadora s\u00eanior da MYRA. Planeje, implemente c\u00f3digo completo, escreva testes, execute valida\u00e7\u00f5es, revise seguran\u00e7a, desempenho, acessibilidade e documente decis\u00f5es. N\u00e3o invente resultados de testes.",browser:"Voc\u00ea \u00e9 a agente especialista em navegador. Use Browser Bridge/Playwright para navegar, ler, clicar, preencher, baixar e validar p\u00e1ginas. Nunca afirme que uma a\u00e7\u00e3o web foi conclu\u00edda sem evid\u00eancia.",research:"Voc\u00ea \u00e9 a agente pesquisadora. Pesquise fontes externas atuais, compare evid\u00eancias, cite URLs e diferencie fatos de infer\u00eancias.",vision:"Voc\u00ea \u00e9 a agente visual. Analise imagens anexadas e capturas com aten\u00e7\u00e3o a detalhes vis\u00edveis. N\u00e3o invente o que n\u00e3o est\u00e1 na imagem.",computer:"Voc\u00ea \u00e9 a agente de controle do computador. Use invent\u00e1rio de aplicativos, janelas, UI Automation e ferramentas locais. Pe\u00e7a confirma\u00e7\u00e3o para a\u00e7\u00f5es destrutivas ou com risco de perda de dados."};
  let codeFiles = load(CODE_KEY, null) || {
    "index.html": {lang:"HTML",content:'<!doctype html>\n<html lang="pt-BR">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width,initial-scale=1">\n  <title>Meu projeto</title>\n</head>\n<body>\n  <main class="hero">\n    <span class="eyebrow">MYRA CODE STUDIO</span>\n    <h1>Olá, mundo.</h1>\n    <p>Seu próximo projeto começa aqui.</p>\n    <button onclick="document.querySelector(\'p\').textContent=\'Está funcionando!\'">Testar interação</button>\n  </main>\n</body>\n</html>'},
    "style.css": {lang:"CSS",content:'* { box-sizing: border-box; }\nbody { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Inter, system-ui, sans-serif; background: #0d1020; color: #f5f3ff; }\n.hero { text-align: center; padding: 48px; }\n.eyebrow { color: #8b5cf6; letter-spacing: .18em; font-size: 11px; }\nh1 { font-size: clamp(36px, 8vw, 72px); margin: 16px 0; }\np { color: #a6a6bb; }\nbutton { border: 0; border-radius: 9px; padding: 12px 18px; background: #7c3aed; color: white; cursor: pointer; }'},
    "script.js": {lang:"JS",content:'console.log("MYRA sandbox ready");'}
  };
  let activeFile = "index.html", previewTimer = null;
  function load(key, fallback) { try { const v = JSON.parse(localStorage.getItem(key)); return v ?? fallback; } catch (_) { return fallback; } }
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { console.warn("[MYRA] storage",e); } }
  function activeConversation(){return conversations.find(x=>x.id===activeId)}
  function createConversation(render=true){const item={id:"chat-"+Date.now()+"-"+Math.random().toString(36).slice(2,7),title:"Nova conversa",messages:[],agentId:$("chat-agent")?.value||"general",updatedAt:Date.now()};conversations.unshift(item);activeId=item.id;if(render){save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();renderMessages()}return item.id}
  let sidebarUndoTimer=null,sidebarUndoPayload=null;
  function sidebarDateGroup(item){
    const now=new Date(),d=new Date(Number(item.updatedAt||Date.now()));
    const today=new Date(now.getFullYear(),now.getMonth(),now.getDate()).getTime();
    const day=new Date(d.getFullYear(),d.getMonth(),d.getDate()).getTime();
    const diff=Math.floor((today-day)/86400000);
    if(item.pinned)return "Fixadas";
    if(diff<=0)return "Hoje";
    if(diff===1)return "Ontem";
    if(diff<7)return "Últimos 7 dias";
    if(diff<30)return "Últimos 30 dias";
    return "Anteriores";
  }
  function sidebarUndoDelete(item){
    if(sidebarUndoTimer)clearTimeout(sidebarUndoTimer);
    sidebarUndoPayload={item,index:conversations.findIndex(c=>c.id===item.id),previousActive:activeId};
    conversations=conversations.filter(c=>c.id!==item.id);
    if(activeId===item.id)activeId=conversations[0]?.id||null;
    if(!conversations.length)createConversation(false);
    save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();renderMessages();
    let toast=$("sidebar-undo-toast");
    if(!toast){toast=document.createElement("div");toast.id="sidebar-undo-toast";toast.className="sidebar-undo-toast";$("sidebar").append(toast)}
    toast.replaceChildren();const label=document.createElement("span");label.textContent="Conversa excluída";
    const undo=document.createElement("button");undo.type="button";undo.textContent="Desfazer";undo.addEventListener("click",()=>{if(!sidebarUndoPayload)return;const p=sidebarUndoPayload;conversations.splice(Math.max(0,Math.min(p.index,conversations.length)),0,p.item);activeId=p.previousActive===p.item.id?p.item.id:activeId;save(STORAGE_KEY,conversations.slice(0,60));sidebarUndoPayload=null;clearTimeout(sidebarUndoTimer);toast.remove();renderSidebar();renderMessages()});
    toast.append(label,undo);sidebarUndoTimer=setTimeout(()=>{sidebarUndoPayload=null;toast.remove()},8000);
  }
  function renderSidebar(){
    const list=$("conversation-list");list.replaceChildren();
    const filtered=conversations.filter(item=>!historyFilter||String(item.title||"Nova conversa").toLocaleLowerCase().includes(historyFilter)).slice(0,60);
    const order=["Fixadas","Hoje","Ontem","Últimos 7 dias","Últimos 30 dias","Anteriores"];
    const groups=new Map(order.map(name=>[name,[]]));
    filtered.forEach(item=>groups.get(sidebarDateGroup(item)).push(item));
    order.forEach(groupName=>{
      const items=groups.get(groupName);if(!items.length)return;
      const heading=document.createElement("div");heading.className="conversation-group-heading";heading.textContent=groupName;list.append(heading);
      items.forEach(item=>{
        const row=document.createElement("div");row.className="conversation-row-wrap"+(item.id===activeId?" active":"");row.dataset.chatId=item.id;
        if(historySelectionMode){const check=document.createElement("input");check.type="checkbox";check.className="conversation-select";check.checked=selectedConversationIds.has(item.id);check.setAttribute("aria-label","Selecionar "+(item.title||"conversa"));check.addEventListener("change",()=>{check.checked?selectedConversationIds.add(item.id):selectedConversationIds.delete(item.id);updateHistoryBulk()});row.append(check)}
        const b=document.createElement("button");b.type="button";b.className="conversation-row"+(item.id===activeId?" active":"");
        const icon=document.createElement("i");icon.className="conversation-status"+(item.id===activeId&&busy?" streaming":"");icon.textContent=item.pinned?"◆":"";
        const title=document.createElement("span");title.textContent=item.title||"Nova conversa";title.title=title.textContent;
        b.append(icon,title);b.addEventListener("click",()=>{if(historySelectionMode){selectedConversationIds.has(item.id)?selectedConversationIds.delete(item.id):selectedConversationIds.add(item.id);renderSidebar();return}activeId=item.id;item.lastViewedAt=Date.now();save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();renderMessages();showView("chat")});row.append(b);
        const actions=document.createElement("div");actions.className="conversation-row-actions";
        const more=document.createElement("button");more.type="button";more.className="conversation-more";more.textContent="···";more.title="Opções da conversa";more.setAttribute("aria-label","Opções de "+(item.title||"conversa"));
        const menu=document.createElement("div");menu.className="conversation-context-menu";menu.hidden=true;
        const makeAction=(label,fn)=>{const button=document.createElement("button");button.type="button";button.textContent=label;button.addEventListener("click",e=>{e.stopPropagation();menu.hidden=true;fn()});menu.append(button)};
        makeAction("Renomear",()=>{const value=window.prompt("Nome da conversa:",item.title||"");if(value&&value.trim()){item.title=value.trim().slice(0,120);item.updatedAt=Date.now();save(STORAGE_KEY,conversations.slice(0,60));renderSidebar()}});
        makeAction(item.pinned?"Desafixar":"Fixar no topo",()=>{item.pinned=!item.pinned;item.updatedAt=Date.now();save(STORAGE_KEY,conversations.slice(0,60));renderSidebar()});
        makeAction("Excluir",()=>sidebarUndoDelete(item));
        more.addEventListener("click",e=>{e.stopPropagation();document.querySelectorAll(".conversation-context-menu").forEach(x=>{if(x!==menu)x.hidden=true});menu.hidden=!menu.hidden});
        actions.append(more,menu);row.append(actions);list.append(row);
      });
    });
    if(!filtered.length){const empty=document.createElement("p");empty.className="conversation-list-empty";empty.textContent=historyFilter?"Nenhuma conversa encontrada.":"Suas conversas aparecerão aqui.";list.append(empty)}
    $("select-history").setAttribute("aria-pressed",String(historySelectionMode));$("history-bulk").hidden=!historySelectionMode;updateHistoryBulk();
    const collapsed=localStorage.getItem("myra-sidebar-collapsed-v1")==="true";$("sidebar")?.classList.toggle("sidebar-collapsed",collapsed);
    const toggle=$("sidebar-collapse-toggle");if(toggle){toggle.setAttribute("aria-label",collapsed?"Expandir barra lateral":"Recolher barra lateral");toggle.title=collapsed?"Expandir barra lateral":"Recolher barra lateral"}
  }
  function updateHistoryBulk(){const count=selectedConversationIds.size;$("history-selected-count").textContent=count+" selecionada(s)";$("delete-selected-history").disabled=count===0;$("select-all-history").checked=conversations.length>0&&conversations.every(c=>selectedConversationIds.has(c.id))}
  function deleteConversations(ids){
    const targets=conversations.filter(c=>ids.includes(c.id));if(!targets.length)return;
    const count=targets.length;showModal("Excluir conversas",count===1?"Esta conversa será excluída deste dispositivo. Esta ação não afeta seus arquivos nem seus plugins.":"Você está prestes a excluir "+count+" conversas selecionadas deste dispositivo. Seus plugins e arquivos não serão alterados.","delete-history");
    $("modal-confirm").textContent=count===1?"Excluir conversa":"Excluir "+count+" conversas";
    $("modal-confirm").onclick=()=>{conversations=conversations.filter(c=>!ids.includes(c.id));ids.forEach(id=>selectedConversationIds.delete(id));if(!conversations.some(c=>c.id===activeId))activeId=conversations[0]?.id||null;if(!conversations.length)createConversation(false);save(STORAGE_KEY,conversations.slice(0,60));closeModal();renderSidebar();renderMessages()};
  }
  function renderMessages(){const c=activeConversation(),box=$("messages");box.replaceChildren();const empty=!c||!c.messages.length;$("welcome").hidden=!empty;if(c&&$("chat-agent"))$("chat-agent").value=c.agentId||"general";if(!empty)c.messages.forEach(m=>{appendMessage(m.role,m.content,false);if(m.image){const img=document.createElement("img");img.className="chat-image-attachment generated-image";img.alt="Imagem gerada pela MYRA";img.src=m.image;const content=box.lastElementChild?.querySelector(".message-content");content?.append(img,createImageDownloadButton(m.image,m.filename||"myra-image.png"))}});$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight}
  function createImageDownloadButton(imageUrl,filename){const button=document.createElement("button");button.type="button";button.className="image-download-button";button.textContent="Baixar imagem";button.addEventListener("click",async()=>{button.disabled=true;button.textContent="Preparando...";try{const response=await fetch(imageUrl);if(!response.ok)throw new Error("Não foi possível obter o arquivo da imagem.");const blob=await response.blob();const url=URL.createObjectURL(blob);const a=document.createElement("a");a.href=url;a.download=String(filename||"myra-image.png").split(/[\\/]/).pop();document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);button.textContent="Imagem baixada"}catch(error){button.textContent="Falha ao baixar";setComposerStatus(error.message)}finally{setTimeout(()=>{button.disabled=false;button.textContent="Baixar imagem"},1800)}});return button}

  function appendMessage(role,content,scroll=true){
    const row=document.createElement("div");row.className="message "+(role==="user"?"user":"assistant");
    const body=document.createElement("div");body.className="message-content";
    const label=document.createElement("div");label.className="message-label";label.textContent=role==="user"?"VOC?":"MYRA";
    const text=document.createElement("div");let questionnaire=null,display=String(content||"");
    if(role!=="user"){
      const openTags=["[[MYRA_QUESTIONS]]","[[MYRA_QUESTIONS]"],closeTags=["[[/MYRA_QUESTIONS]]","[/MYRA_QUESTIONS]"];
      let start=-1,openTag="",end=-1,closeTag="";
      for(const tag of openTags){const pos=display.indexOf(tag);if(pos>=0&&(start<0||pos<start)){start=pos;openTag=tag}}
      if(start>=0){for(const tag of closeTags){const pos=display.indexOf(tag,start+openTag.length);if(pos>=0&&(end<0||pos<end)){end=pos;closeTag=tag}}}
      if(start>=0&&end>start){try{questionnaire=JSON.parse(display.slice(start+openTag.length,end).trim());display=(display.slice(0,start)+display.slice(end+closeTag.length)).trim()}catch(e){console.warn("Questionnaire JSON inv?lido",e)}}
    }
    body.append(label);
    if(role==="user"){if(Array.isArray(content)){const t=content.find(x=>x&&x.type==="text")?.text||"";text.textContent=t;body.append(text);content.filter(x=>x&&x.type==="image_url"&&x.image_url?.url).forEach(x=>{const img=document.createElement("img");img.className="chat-image-attachment";img.alt="Imagem anexada";img.src=x.image_url.url;img.loading="lazy";body.append(img)})}else{text.textContent=display;body.append(text)}}else{renderAssistantContent(body,display)}
    row.append(body);$("messages").appendChild(row);
    if(questionnaire)renderQuestionnaire(body,questionnaire);
    if(scroll)$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight;
  }
  function renderAssistantContent(parent,content){
    const source=String(content||""),fence=String.fromCharCode(96).repeat(3),parts=source.split(fence),blocks=[];
    let plain=parts[0]||"";
    for(let i=1;i<parts.length;i+=2){
      const raw=parts[i]||"",newline=raw.indexOf("\n");
      if(newline<0){plain+=fence+raw;continue}
      const lang=raw.slice(0,newline).trim().toLowerCase()||"text";
      blocks.push({lang,code:raw.slice(newline+1).trimEnd()});
      plain+=(parts[i+1]||"");
    }
    const prose=document.createElement("div");prose.className="assistant-prose";prose.textContent=plain.trim();if(plain.trim())parent.append(prose);if(!blocks.length)return;
    const files=[];
    blocks.forEach(block=>{
      const ext=block.lang==="html"||block.lang==="htm"?"html":block.lang==="css"?"css":(["js","javascript","jsx","ts","typescript"].includes(block.lang)?"js":null);
      if(ext)files.push({name:ext==="html"?"index.html":ext==="css"?"style.css":"script.js",lang:ext.toUpperCase(),content:block.code});
      else{const pre=document.createElement("pre");pre.className="chat-code-block";const code=document.createElement("code");code.textContent=block.code;pre.append(code);parent.append(pre)}
    });
    if(!files.length)return;
    files.forEach(file=>{codeFiles[file.name]=file});activeFile=files.some(f=>f.name==="index.html")?"index.html":files[0].name;save(CODE_KEY,codeFiles);renderFiles();loadActiveCode();
    const artifact=document.createElement("section");artifact.className="chat-code-artifact";const head=document.createElement("div");head.className="chat-code-head";const title=document.createElement("strong");title.textContent="Projeto gerado pela MYRA";const actions=document.createElement("div");
    const open=document.createElement("button");open.type="button";open.className="soft-button";open.textContent="Abrir no Code Studio";open.addEventListener("click",()=>{showView("code");renderFiles();loadActiveCode();renderPreview()});
    const frame=document.createElement("iframe");frame.className="chat-artifact-preview";frame.title="Preview do projeto criado no chat";frame.setAttribute("sandbox","allow-scripts");frame.srcdoc=buildPreview();
    const codePanel=document.createElement("pre");codePanel.className="chat-code-block chat-artifact-code";codePanel.hidden=true;const codeView=document.createElement("code");codeView.textContent=files.map(file=>"// "+file.name+"\n"+file.content).join("\n\n");codePanel.append(codeView);
    const tabs=document.createElement("div");tabs.className="chat-code-tabs";const previewTab=document.createElement("button");previewTab.type="button";previewTab.className="active";previewTab.textContent="Pré-visualização";const codeTab=document.createElement("button");codeTab.type="button";codeTab.textContent="Código";
    previewTab.addEventListener("click",()=>{frame.hidden=false;codePanel.hidden=true;previewTab.classList.add("active");codeTab.classList.remove("active")});codeTab.addEventListener("click",()=>{frame.hidden=true;codePanel.hidden=false;codeTab.classList.add("active");previewTab.classList.remove("active")});tabs.append(previewTab,codeTab);
    const run=document.createElement("button");run.type="button";run.className="primary-button";run.textContent="Atualizar preview";run.addEventListener("click",()=>{frame.srcdoc=buildPreview()});actions.append(open,run);head.append(title,actions);artifact.append(head,tabs,frame,codePanel);
    const filebar=document.createElement("div");filebar.className="chat-artifact-files";filebar.textContent="Arquivos: "+files.map(f=>f.name).join(" · ");artifact.append(filebar);parent.append(artifact);
  }
  function renderQuestionnaire(parent,data){
    const card=document.createElement("form");card.className="myra-questionnaire";
    const heading=document.createElement("strong");heading.textContent=data.title||"S? preciso confirmar alguns detalhes";card.append(heading);
    (Array.isArray(data.questions)?data.questions:[]).slice(0,5).forEach((q,index)=>{
      const wrap=document.createElement("label");wrap.className="question-field";
      const caption=document.createElement("span");caption.textContent=q.label||q.question||q.placeholder||("Pergunta "+(index+1));wrap.append(caption);
      let control;
      if(q.type==="choice"&&Array.isArray(q.options)){
        control=document.createElement("select");const empty=document.createElement("option");empty.value="";empty.textContent="Selecione uma op\u00e7\u00e3o";control.append(empty);
        q.options.slice(0,12).forEach(value=>{const opt=document.createElement("option");opt.value=String(value);opt.textContent=String(value);control.append(opt)});
      }else{control=document.createElement("input");control.type="text";control.placeholder=q.placeholder||"Digite sua resposta"; }
      control.dataset.questionId=q.id||("q"+index);control.dataset.questionLabel=q.label||("Pergunta "+(index+1));control.required=q.required!==false;wrap.append(control);card.append(wrap);
    });
    const submit=document.createElement("button");submit.type="submit";submit.className="primary-button";submit.textContent="Enviar respostas";card.append(submit);
    card.addEventListener("submit",event=>{event.preventDefault();const answers=[];let valid=true;card.querySelectorAll("[data-question-id]").forEach(control=>{if(control.required&&!control.value.trim())valid=false;answers.push(control.dataset.questionLabel+": "+(control.value.trim()||"N\u00e3o informado"))});if(!valid){card.querySelector("[data-question-id]:invalid")?.focus();return}card.querySelectorAll("input,select,button").forEach(el=>el.disabled=true);sendMessage("Respostas ao question\u00e1rio da MYRA:"+String.fromCharCode(10)+answers.join(String.fromCharCode(10)));});
    parent.append(card);
  }
  async function installCatalogPlugin(plugin,button){
    if(!plugin?.installable||plugin.installed)return;
    button.disabled=true;button.textContent="Baixando...";
    const status=$("plugin-source-status");
    try{
      const packageResponse=await fetch(API+"/plugins/catalog/"+encodeURIComponent(plugin.id)+"/package",{cache:"no-store",signal:AbortSignal.timeout(15000)});
      if(!packageResponse.ok){const body=await packageResponse.json().catch(()=>({}));throw new Error(body.detail||"Pacote nativo indisponível.")}
      const archive=await packageResponse.blob();
      status.textContent="Pacote recebido. Validando manifesto e integridade...";
      const validationResponse=await fetch(API+"/plugins/validate",{method:"POST",headers:{"Content-Type":"application/zip"},body:archive,signal:AbortSignal.timeout(30000)});
      const validation=await validationResponse.json().catch(()=>({}));
      if(!validationResponse.ok)throw new Error(validation.detail||"A validação do pacote falhou.");
      const summary="Instalar "+validation.name+" v"+validation.version+"?\n\nTipo: "+validation.type+"\nArquivos: "+validation.files+"\nSHA-256: "+validation.sha256+"\n\nA extensão será instalada desativada. Você poderá ativá-la depois.";
      if(!window.confirm(summary)){status.textContent="Instalação cancelada. Nenhuma alteração foi feita.";button.disabled=false;button.textContent="Instalar";return}
      button.textContent="Instalando...";
      const installResponse=await fetch(API+"/plugins/install",{method:"POST",headers:{"Content-Type":"application/zip"},body:archive,signal:AbortSignal.timeout(30000)});
      const installed=await installResponse.json().catch(()=>({}));
      if(!installResponse.ok)throw new Error(installed.detail||"Não foi possível instalar o pacote.");
      status.textContent="Instalado: "+installed.name+" v"+installed.version+". Ative na lista de instalados para usar no chat.";
      const installedHost=$("plugin-installed-list");if(installedHost)installedHost.dataset.loaded="false";
      await refreshInstalledPlugins();await renderPlugins();
    }catch(error){status.textContent="Falha na instalação: "+error.message;button.disabled=false;button.textContent="Instalar"}
  }
  async function renderPlugins(){
    const host=$("plugin-grid");if(!host)return;host.replaceChildren();
    const query=($("plugin-search").value||"").trim().toLowerCase(),category=$("plugin-category").value;
    const loading=document.createElement("p");loading.className="muted-note";loading.textContent="Carregando biblioteca MYRA...";host.append(loading);
    try{
      const response=await fetch(API+"/plugins/catalog",{cache:"no-store",signal:AbortSignal.timeout(7000)});
      const data=await response.json().catch(()=>({}));if(!response.ok)throw new Error(data.detail||"Biblioteca MYRA indisponível.");
      const entries=Array.isArray(data.plugins)?data.plugins:[];host.replaceChildren();
      const filtered=entries.filter(p=>(category==="all"||p.category===category)&&[p.name,p.description,p.type,p.category].join(" ").toLowerCase().includes(query));
      if(!filtered.length){const empty=document.createElement("p");empty.className="muted-note";empty.textContent="Nenhuma extensão encontrada nesta categoria.";host.append(empty)}
      filtered.forEach(p=>{
        const card=document.createElement("article");card.className="plugin-card";
        const top=document.createElement("div");top.className="plugin-card-top";const type=document.createElement("span");type.textContent=String(p.type||"plugin").toUpperCase();const state=document.createElement("span");state.className="plugin-state "+(p.status==="native"?"native":p.status==="available"?"available":"planned");state.textContent=p.installed?(p.enabled?"ATIVO":"INSTALADO"):p.status==="native"?"NATIVO":p.installable?"PRONTO PARA INSTALAR":"EM DESENVOLVIMENTO";top.append(type,state);
        const name=document.createElement("h3");name.textContent=p.name||p.id;const desc=document.createElement("p");desc.textContent=p.description||"Sem descrição.";
        const actions=document.createElement("div");actions.className="plugin-card-actions";
        const source=document.createElement("small");source.textContent=p.source||"Componente interno da MYRA";actions.append(source);
        if(p.installable){
          const install=document.createElement("button");install.type="button";install.className=p.installed?"soft-button":"primary-button";install.textContent=p.installed?"Já instalado":"Instalar";install.disabled=Boolean(p.installed);install.addEventListener("click",()=>installCatalogPlugin(p,install));actions.append(install);
        }else if(p.status==="native"){
          const native=document.createElement("small");native.className="plugin-state native";native.textContent="Disponível no chat";actions.append(native);
        }
        card.append(top,name,desc,actions);host.append(card);
      });
    }catch(error){host.replaceChildren();const message=document.createElement("p");message.className="muted-note";message.textContent="Não foi possível carregar a biblioteca: "+error.message;host.append(message)}
    const installedHost=$("plugin-installed-list");if(installedHost&&installedHost.dataset.loaded!=="true")refreshInstalledPlugins();
  }
  async function refreshInstalledPlugins(){
    const host=$("plugin-installed-list");if(!host||host.dataset.loading==="true")return;
    host.dataset.loading="true";
    try{
      const response=await fetch(API+"/plugins",{cache:"no-store",signal:AbortSignal.timeout(5000)});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||"Não foi possível consultar os plugins instalados.");
      const plugins=Array.isArray(data.plugins)?data.plugins:[];
      host.replaceChildren();
      if(!plugins.length){const empty=document.createElement("p");empty.className="muted-note";empty.textContent="Nenhum plugin declarativo instalado neste dispositivo.";host.append(empty);return}
      plugins.sort((a,b)=>(a.name||a.id).localeCompare(b.name||b.id));
      plugins.forEach(plugin=>{
        const row=document.createElement("div");row.className="plugin-installed-row";
        const info=document.createElement("div");info.className="plugin-installed-info";
        const title=document.createElement("strong");title.textContent=plugin.name||plugin.id;
        const meta=document.createElement("small");meta.textContent=(plugin.id||"") +" · v"+(plugin.version||"?")+" · "+(plugin.type||"plugin");
        const hash=document.createElement("small");hash.className="plugin-installed-hash";hash.textContent="SHA-256: "+String(plugin.sha256||"").slice(0,16)+"…";hash.title=plugin.sha256||"";
        info.append(title,meta,hash);
        const state=document.createElement("span");state.className="plugin-state planned";state.textContent=plugin.enabled?"Ativo":"Instalado · desativado";
        const toggle=document.createElement("button");toggle.type="button";toggle.className="soft-button";toggle.textContent=plugin.enabled?"Desativar":"Ativar";
        toggle.addEventListener("click",async()=>{toggle.disabled=true;try{const action=plugin.enabled?"disable":"enable";const result=await fetch(API+"/plugins/"+encodeURIComponent(plugin.id)+"/"+action,{method:"POST",signal:AbortSignal.timeout(10000)});const body=await result.json().catch(()=>({}));if(!result.ok)throw new Error(body.detail||"Nao foi possivel alterar o estado do plugin.");$("plugin-source-status").textContent=plugin.name+ (body.enabled?" ativado na biblioteca declarativa.":" desativado.");host.dataset.loaded="false";await refreshInstalledPlugins();await renderPlugins()}catch(error){$("plugin-source-status").textContent=error.message;toggle.disabled=false}});
        const remove=document.createElement("button");remove.type="button";remove.className="soft-button";remove.textContent="Remover";remove.disabled=Boolean(plugin.enabled);
        remove.addEventListener("click",async()=>{
          if(!window.confirm("Remover todas as versões de "+(plugin.name||plugin.id)+" deste dispositivo?"))return;
          remove.disabled=true;
          try{const result=await fetch(API+"/plugins/"+encodeURIComponent(plugin.id),{method:"DELETE",signal:AbortSignal.timeout(10000)});const body=await result.json().catch(()=>({}));if(!result.ok)throw new Error(body.detail||"Falha ao remover plugin.");$("plugin-source-status").textContent="Plugin removido: "+(plugin.name||plugin.id);await refreshInstalledPlugins()}
          catch(error){$("plugin-source-status").textContent=error.message;remove.disabled=false}
        });
        row.append(info,state,toggle,remove);host.append(row);
      });
    }catch(error){host.replaceChildren();const message=document.createElement("p");message.className="muted-note";message.textContent="Registro local indisponível: "+error.message;host.append(message)}
    finally{host.dataset.loading="false";host.dataset.loaded="true"}
  }
  async function importPluginPackage(file){
    if(!file)return;
    const status=$("plugin-source-status");
    if(file.size>20*1024*1024){status.textContent="O ZIP excede o limite de 20 MB.";return}
    status.textContent="Validando manifesto, arquivos, permissões e integridade do pacote…";
    try{
      const validationResponse=await fetch(API+"/plugins/validate",{method:"POST",headers:{"Content-Type":"application/zip"},body:file,signal:AbortSignal.timeout(30000)});
      const validation=await validationResponse.json().catch(()=>({}));
      if(!validationResponse.ok)throw new Error(validation.detail||"Pacote rejeitado pela validação.");
      const summary="Pacote validado: "+validation.name+" ("+validation.id+" v"+validation.version+").\n\nTipo: "+validation.type+"\nArquivos: "+validation.files+"\nSHA-256: "+validation.sha256+"\n\nNenhum código executável será executado. Instalar agora, mantendo-o desativado?";
      if(!window.confirm(summary)){status.textContent="Importação cancelada. Nenhum arquivo foi instalado.";return}
      status.textContent="Instalando pacote validado…";
      const installResponse=await fetch(API+"/plugins/install",{method:"POST",headers:{"Content-Type":"application/zip"},body:file,signal:AbortSignal.timeout(30000)});
      const installed=await installResponse.json().catch(()=>({}));
      if(!installResponse.ok)throw new Error(installed.detail||"Falha ao instalar o pacote.");
      status.textContent="Instalado com segurança: "+installed.name+" v"+installed.version+". Permanece desativado.";
      await refreshInstalledPlugins();
    }catch(error){status.textContent="Não foi possível importar o pacote: "+error.message}
    finally{$("plugin-package").value=""}
  }
  const SETUP_KEY="myra-first-run-setup-v1";
  let setupStatus=null;
  function setupLog(message){const el=$("setup-log");if(el)el.textContent=message}
  async function refreshSetupStatus(){
    try{
      const r=await fetch(API+"/setup/status",{cache:"no-store",signal:AbortSignal.timeout(5000)});
      if(!r.ok)throw new Error("Não foi possível consultar o ambiente.");
      setupStatus=await r.json();
      $("setup-core-status").textContent=setupStatus.core?"Instalado e pronto":"Não encontrado";
      $("setup-vision-status").textContent=setupStatus.vision_ready?"Todos os módulos instalados":Object.entries(setupStatus.vision||{}).filter(([,v])=>v).map(([k])=>k).join(", ")||"Ainda não ativado";
      $("setup-model-status").textContent=setupStatus.ollama_installed?(setupStatus.models?.length?setupStatus.models.join(", "):"Ollama instalado; nenhum modelo detectado"):"Ollama não instalado";
      const done=Number(Boolean(setupStatus.core))+Number(Boolean(setupStatus.vision_ready))+Number(Boolean(setupStatus.models?.length))+1;
      $("setup-progress-count").textContent=done+" / 4";
      $("setup-progress-label").textContent=done>=4?"Ambiente pronto": "Você pode configurar os recursos opcionais agora ou depois";
      $("setup-vision").checked=Boolean(setupStatus.vision_ready)||$("setup-vision").checked;
      return setupStatus;
    }catch(e){setupLog("O backend ainda não respondeu. Inicie a MYRA novamente ou tente atualizar esta tela. "+e.message);return null}
  }
  async function runSetup(){
    const finish=$("setup-finish"),saveButton=$("setup-save");finish.disabled=true;saveButton.disabled=true;
    try{
      const prefs={vision:$("setup-vision").checked,ollama:$("setup-ollama").checked,model:$("setup-model").value,updatedAt:Date.now()};
      save("myra-setup-preferences-v1",prefs);
      if(prefs.vision&&!(setupStatus?.vision_ready)){
        setupLog("Instalando PyTorch CPU, OpenCV, ONNX Runtime, RapidOCR e Ultralytics a partir dos pacotes incluídos…");
        const r=await fetch(API+"/setup/vision",{method:"POST",signal:AbortSignal.timeout(1800000)});const data=await r.json().catch(()=>({}));
        if(!r.ok)throw new Error(data.detail||"Falha ao ativar visão/ML.");
        setupLog("Visão computacional ativada. "+(data.message||""));
      }
      if(prefs.ollama){
        if(!setupStatus?.ollama_installed){
          setupLog("Instalando Ollama pelo Windows Package Manager. Isso pode levar alguns minutos…");
          const r=await fetch(API+"/setup/ollama",{method:"POST",signal:AbortSignal.timeout(900000)});const data=await r.json().catch(()=>({}));
          if(!r.ok)throw new Error(data.detail||"Não foi possível instalar Ollama.");
          setupLog(data.message||"Ollama instalado.");
          await new Promise(resolve=>setTimeout(resolve,5000));
        }
        const modelAlreadyInstalled=Array.isArray(setupStatus?.models)&&setupStatus.models.some(name=>String(name).toLowerCase()===prefs.model.toLowerCase());
        if(!modelAlreadyInstalled){
          setupLog("Baixando "+prefs.model+". O download depende da sua conexão e pode levar alguns minutos…");
          const r=await fetch(API+"/setup/model",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:prefs.model}),signal:AbortSignal.timeout(3600000)});
          const data=await r.json().catch(()=>({}));
          if(!r.ok)throw new Error(data.detail||"Falha ao baixar o modelo.");
          setupLog(data.message||"Modelo pronto.");
        }else{
          setupLog("Modelo "+prefs.model+" já está instalado. Nenhum download necessário.");
        }
        await refreshModels();
      }
      save(SETUP_KEY,{completed:true,completedAt:Date.now(),preferences:prefs});
      setupLog("Configuração concluída. Seu workspace MYRA está pronto.");
      await refreshSetupStatus();
      showView("chat");
    }catch(e){setupLog("Não foi possível concluir esta etapa: "+e.message+" Você pode corrigir a opção e tentar novamente.");}
    finally{finish.disabled=false;saveButton.disabled=false}
  }
  function initSetup(){
    const prefs=load("myra-setup-preferences-v1",{});
    $("setup-vision").checked=prefs.vision??false;
    $("setup-ollama").checked=prefs.ollama??false;
    if(prefs.model)$("setup-model").value=prefs.model;
    $("setup-finish").addEventListener("click",()=>withButtonLoader($("setup-finish"),runSetup));
    $("setup-save").addEventListener("click",()=>withButtonLoader($("setup-save"),async()=>{save("myra-setup-preferences-v1",{vision:$("setup-vision").checked,ollama:$("setup-ollama").checked,model:$("setup-model").value,updatedAt:Date.now()});setupLog("Preferências salvas neste perfil. Nenhum pacote foi baixado.")}));
    $("setup-skip").addEventListener("click",()=>{save(SETUP_KEY,{completed:true,deferred:true,completedAt:Date.now()});setupLog("Etapas adiadas. Você poderá voltar a esta aba quando quiser.");showView("chat")});
    refreshSetupStatus();
  }
  async function improvePrompt(){
    const input=$("message-input"),draft=input.value.trim(),button=$("improve-prompt");
    if(!draft){input.focus();button.title="Escreva primeiro o que deseja pedir à MYRA.";return}
    button.disabled=true;button.textContent="Aprimorando…";
    try{
      const r=await fetch(API+"/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"myra-agent",stream:false,messages:[{role:"system",content:"Você é um especialista sênior em engenharia de prompts. Reescreva o pedido do usuário para ficar claro, específico, completo e executável. Preserve a intenção e as restrições; acrescente critérios de sucesso, formato esperado e perguntas apenas quando indispensáveis. Não execute o pedido, não invente requisitos. Retorne somente o prompt aprimorado em português brasileiro."},{role:"user",content:draft}]}),signal:AbortSignal.timeout(180000)});
      const data=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(data.detail||"O modelo local não respondeu.");
      const improved=data?.choices?.[0]?.message?.content?.trim();
      if(!improved)throw new Error("A resposta do melhorador veio vazia.");
      input.value=improved;resizeInput();input.focus();button.title="Prompt aprimorado. Revise antes de enviar.";setupLog("Prompt aprimorado. Revise o texto antes de enviar.");
    }catch(e){button.title="Não foi possível melhorar: "+e.message;setupLog("Melhorador de prompts: "+e.message)}
    finally{button.disabled=false;button.textContent="✦ Melhorar prompt"}
  }
  function showView(name){document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id==="view-"+name));document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name));const names={chat:"Chat",activity:"Atividades",tools:"Ferramentas",settings:"Configurações",projects:"Projetos",code:"Code Studio",preview:"Pré-visualização",integrations:"Integrações",credentials:"Credenciais",plugins:"Biblioteca de plugins",autonomy:"Autonomia",models:"Modelos",widget:"Widget Studio",setup:"Primeiros passos"};names.runtime="Servidores e Docker";$("top-context").textContent=names[name]||"MYRA";if(name==="code"||name==="preview")renderPreview();if(name==="projects")renderProjects();if(name==="autonomy")refreshCognitiveConsole();if(name==="models")refreshModels();if(name==="integrations"){refreshGitHub();refreshApiIntegrations()}if(name==="credentials")window.refreshMyraCredentials?.();if(name==="plugins")renderPlugins();if(name==="runtime")refreshRuntime();if(name==="setup")refreshSetupStatus()}
  const PLATFORM_ICONS={
    github:'<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3-.3 6.1-1.5 6.1-6.7a5.2 5.2 0 0 0-1.4-3.6 4.8 4.8 0 0 0-.1-3.6s-1.1-.3-3.7 1.4a13 13 0 0 0-6.8 0C5.6.3 4.5.6 4.5.6a4.8 4.8 0 0 0-.1 3.6A5.2 5.2 0 0 0 3 7.8c0 5.2 3.1 6.4 6.1 6.7a3.4 3.4 0 0 0-.9 2.6V22"/>',
    tools:'<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4L15 12l-3-3z"/>',
    cpu:'<rect x="5" y="5" width="14" height="14" rx="2"/><path d="M9 9h6v6H9zM9 1v4m6-4v4M9 19v4m6-4v4M1 9h4m-4 6h4m14-6h4m-4 6h4"/>',
    plug:'<path d="M8 2v6m8-6v6M6 8h12v3a6 6 0 0 1-6 6v5m-6-14H6"/>',
    folder:'<path d="M3 7a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    browser:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M7 6.5h.01M10 6.5h.01"/>',
    files:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8m-8 4h8"/>',
    desktop:'<rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8m-4-4v4"/>',
    vision:'<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    search:'<circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/>',
    play:'<path d="m8 5 12 7-12 7z"/>',
    settings:'<circle cx="12" cy="12" r="3"/><path d="m19.4 15 1.2 1-1.5 2.6-1.5-.5a8 8 0 0 1-1.6.9l-.3 1.6H8.3L8 19a8 8 0 0 1-1.6-.9l-1.5.5-1.5-2.6 1.2-1a8 8 0 0 1 0-1.9l-1.2-1 1.5-2.6 1.5.5A8 8 0 0 1 8 9.1l.3-1.6h7.4l.3 1.6a8 8 0 0 1 1.6.9l1.5-.5 1.5 2.6-1.2 1a8 8 0 0 1 0 1.9z"/>',
    chat:'<path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5 9 9 0 0 1-4-.9L3 21l1.9-5.5a9 9 0 0 1-.9-4A8.5 8.5 0 0 1 12.5 3h.5a8.5 8.5 0 0 1 8 8z"/>',
    code:'<path d="m8 8-4 4 4 4m8-8 4 4-4 4m-2-12-4 16"/>',
    sparkles:'<path d="m12 3 1.9 5.8L20 11l-6.1 2.2L12 19l-1.9-5.8L4 11l6.1-2.2L12 3zM19 14l1.1 2.9L23 18l-2.9 1.1L19 22l-1.1-2.9L15 18l2.9-1.1L19 14z"/>'
  };
  function iconSvg(name){return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">'+(PLATFORM_ICONS[name]||PLATFORM_ICONS.sparkles)+'</svg>';}
  function renderPlatformIcons(){
    const integrationNames=["github","tools","cpu","plug","folder"];
    document.querySelectorAll(".integration-card .integration-icon").forEach((el,i)=>{el.innerHTML=iconSvg(integrationNames[i]||"sparkles");});
    const toolNames=["browser","files","desktop","vision","search","play"];
    document.querySelectorAll(".tool-tile b").forEach((el,i)=>{el.innerHTML=iconSvg(toolNames[i]||"sparkles");});
    document.querySelectorAll(".suggestion span").forEach((el,i)=>{el.innerHTML=iconSvg(["sparkles","folder","code"][i]||"sparkles");});
    document.querySelectorAll(".resource-icon").forEach((el,i)=>{el.innerHTML=iconSvg(["tools","cpu","browser"][i]||"sparkles");});
    const modelIcon=document.querySelector(".model-current-icon");if(modelIcon)modelIcon.innerHTML=iconSvg("cpu");
    const settings=$("settings-button");if(settings)settings.innerHTML=iconSvg("settings");
  }
  function setBusy(v){busy=Boolean(v);const indicator=$("typing");if(indicator){indicator.hidden=!busy;indicator.style.display=busy?"flex":"none";indicator.setAttribute("aria-hidden",String(!busy));} $("send-button").disabled=!$("message-input").value.trim();$("message-input").disabled=false;$("mode-toggle").disabled=false;$("message-input").placeholder=busy?"MYRA trabalhando - envie a proxima mensagem para a fila...":(executionMode?"Descreva o que a MYRA deve executar...":"O que vamos construir hoje?")}
  async function setChatActivity(active){try{const r=await fetch(API+"/chat_activity",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({active:Boolean(active)})});if(!r.ok)throw new Error("HTTP "+r.status)}catch(e){console.warn("[WIDGET CHAT ACTIVITY]",e)}}
  let widgetVisible=load("myra-widget-visible",true)!==false;
  function updateWidgetVisibilityButton(){const b=$("widget-visibility-toggle");if(!b)return;b.setAttribute("aria-pressed",String(widgetVisible));b.setAttribute("aria-label",widgetVisible?"Ocultar widget":"Mostrar widget");b.title=widgetVisible?"Ocultar widget":"Mostrar widget";b.innerHTML=widgetVisible?'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.4-6 9.5-6 9.5 6 9.5 6-3.4 6-9.5 6-9.5-6-9.5-6Z" fill="none" stroke="currentColor" stroke-width="1.7"/><circle cx="12" cy="12" r="2.8" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>':'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 6.2A10.8 10.8 0 0 1 12 6c6.1 0 9.5 6 9.5 6a16 16 0 0 1-3 3.6M6.2 6.3C3.8 8 2.5 12 2.5 12s3.4 6 9.5 6c1 0 1.9-.2 2.7-.5" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>'; }
  async function applyWidgetVisibility(visible){const invoke=window.__TAURI__?.core?.invoke;if(!invoke)throw new Error("Controle nativo disponível apenas no aplicativo MYRA.");try{const actual=await invoke("set_widget_visible",{visible});widgetVisible=actual!==false;localStorage.setItem("myra-widget-visible",String(widgetVisible));updateWidgetVisibilityButton();return widgetVisible}catch(error){updateWidgetVisibilityButton();console.error("[WIDGET VISIBILITY]",error);throw error}}
  async function toggleWidgetVisibility(){try{const invoke=window.__TAURI__?.core?.invoke;const actual=invoke?await invoke("get_widget_visible"):widgetVisible;await applyWidgetVisibility(!actual)}catch(error){const b=$("widget-visibility-toggle");if(b)b.title="Não foi possível alterar o widget: "+error.message}}
  async function syncNativeWidgetVisibility(){try{const invoke=window.__TAURI__?.core?.invoke;if(invoke){widgetVisible=!!(await invoke("get_widget_visible"));localStorage.setItem("myra-widget-visible",String(widgetVisible));updateWidgetVisibilityButton()}}catch(_){}}
  let globalLoaderDepth=0;
  function showGlobalLoader(button){
    const overlay=$("myra-global-loader");if(!overlay)return;
    const title=$("myra-loader-title"),detail=$("myra-loader-detail");
    const label=String(button?.textContent||"").trim();
    if(title)title.textContent=/voz/i.test(label)?"Salvando configurações de voz…":/runtime|configura/i.test(label)?"Salvando configurações…":/aplicar|widget/i.test(label)?"Atualizando widget…":"Processando solicitação…";
    if(detail)detail.textContent="Aguarde. A MYRA está trabalhando localmente.";
    globalLoaderDepth++;overlay.hidden=false;document.body.classList.add("has-global-loader");
  }
  function hideGlobalLoader(){
    globalLoaderDepth=Math.max(0,globalLoaderDepth-1);
    if(!globalLoaderDepth){const overlay=$("myra-global-loader");if(overlay)overlay.hidden=true;document.body.classList.remove("has-global-loader");}
  }
  async function withButtonLoader(button,action){
    if(button)button.disabled=true;
    showGlobalLoader(button);
    const started=Date.now();
    try{return await action();}
    finally{
      const remaining=Math.max(0,280-(Date.now()-started));
      if(remaining)await new Promise(resolve=>setTimeout(resolve,remaining));
      hideGlobalLoader();if(button)button.disabled=false;
    }
  }
  let messageQueue = load(QUEUE_KEY, []);
  // Mensagens pendentes de uma sessão anterior nunca são executadas silenciosamente.
  let queueNeedsResume = messageQueue.length > 0;
  function renderQueue(){
    save(QUEUE_KEY, messageQueue);
    const panel=$("message-queue"); if(!panel)return;
    panel.replaceChildren(); panel.hidden=!messageQueue.length;
    if(!messageQueue.length){queueNeedsResume=false;return}
    const head=document.createElement("div");head.className="queue-heading";
    const label=document.createElement("span");label.textContent="FILA DE MENSAGENS · "+messageQueue.length+" aguardando";head.append(label);
    if(queueNeedsResume){
      const resume=document.createElement("button");resume.type="button";resume.className="queue-resume-btn";
      resume.textContent="Retomar fila";resume.addEventListener("click",()=>{queueNeedsResume=false;renderQueue();processQueue()});head.append(resume);
    }
    panel.append(head);
    messageQueue.forEach((item,index)=>{const row=document.createElement("div");row.className="queue-item";const label=document.createElement("span");label.textContent=(index+1)+". "+(item.displayContent||item.content);const mode=document.createElement("small");mode.textContent=item.taskMode?"TAREFA":"CHAT";const remove=document.createElement("button");remove.type="button";remove.textContent="×";remove.title="Remover da fila";remove.addEventListener("click",()=>{messageQueue.splice(index,1);renderQueue()});row.append(label,mode,remove);panel.append(row)});
  }
  function isExplicitActionRequest(text){
    const value=String(text||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase();
    // Ordens imperativas claras devem acionar o executor mesmo no modo Auto.
    return /^(?:(?:por favor|please),?\s+)?(?:(?:voce\s+)?(?:pode|poderia)\s+)?(?:abra|abre|abrir|acesse|acessa|visite|visitar|inicie|iniciar|execute|executar|pesquise|pesquisar|procure|procurar|busque|buscar|consulte|consultar|verifique|verificar|confira|conferir|leia|ler|clique|clicar|digite|digitar|baixe|baixar|envie|enviar|instale|instalar|crie|criar|salve|salvar|edite|editar|organize|organizar|exclua|excluir|apague|apagar|capture|capturar|tire|tirar|open|launch|go to|search|find|check|read|click|type|download|send|install|create|save|edit|delete)\s+(?:(?:o|a|os|as|no|na|the)\s+)?[a-z0-9]/i.test(value);
  }
  function isExplicitImageEditRequest(text){
    const value=String(text||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase();
    return /\b(edite|editar|modifique|modificar|altere|alterar|remova|remover|apague|apagar|troque|trocar|substitua|substituir|mude|mudar|deixe|deixar|coloque|colocar|adicione|adicionar|aumente|aumentar|reduza|reduzir|clareie|clarear|escureca|escurecer|corrija|corrigir|recorte|recortar|melhore|melhorar|restaure|restaurar|retocar|retoque|transforme|transformar|remove|replace|change|edit|retouch|restore|enhance|crop|erase|recolor|upscale|add|put|change the|make it|make the|turn it)\b/.test(value);
  }
  function isExplicitImageGenerationRequest(text){
    const value=String(text||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase();
    return /^(?:(?:por favor|please),?\s+)?(?:(?:crie|criar|gere|gerar|produza|produzir|desenhe|desenhar|faca|fazer|create|generate|draw|make)\s+)(?:(?:uma?|the)\s+)?(?:imagem|foto|ilustracao|image|picture|illustration)\b/.test(value)
      || /^(?:imagem|foto|ilustracao)\s+(?:de|do|da|sobre)\s+/.test(value);
  }
  function sendMessage(raw){if(imageGenerationBusy||imageEditBusy)return;
    const displayContent=String(raw||"").trim();if(!displayContent)return;
    if(!pendingImages.length && isExplicitImageGenerationRequest(displayContent)){
      const input=$("message-input");if(input)input.value=displayContent;
      generateImage();return;
    }
    if(pendingImages.length && isExplicitImageEditRequest(displayContent)){
      const input=$("message-input");if(input)input.value=displayContent;
      editImage();return;
    }
    if(!load(SETUP_KEY,{}).completed){
      save(SETUP_KEY,{completed:true,deferred:true,completedAt:Date.now(),reason:"chat-started-before-optional-setup"});
      setupLog("Configuração opcional adiada. Você já pode conversar com a MYRA e configurar recursos adicionais depois.");
    }
    let content=displayContent;
    const instructions={code:"Atue como engenheira de software sênior. Planeje a solução, produza código completo e executável, valide acessibilidade, segurança, responsividade e testes. Não entregue apenas snippets quando o pedido exigir um projeto.",research:"Pesquise fontes externas atuais e confiáveis antes de responder. Compare fontes, cite links e separe fatos verificados de hipóteses.",design:"Atue como designer de produto e frontend sênior. Defina hierarquia visual, tipografia, espaçamento, responsividade, estados vazios e microinterações.",review:"Faça uma revisão crítica de nível sênior: procure bugs, riscos de segurança, acessibilidade, desempenho, casos extremos e testes ausentes."};
    if(activeSkills.size){const guidance=[...activeSkills].map(key=>instructions[key]).filter(Boolean).join("\n\n");content="[MODO DE TRABALHO ATIVADO]\n"+guidance+"\n\n[PEDIDO]\n"+content}
    activeSkills.clear();document.querySelectorAll(".skill-chip").forEach(b=>b.classList.remove("active"));
    const images=pendingImages.splice(0),documents=pendingDocuments.splice(0);const documentContext=documents.length?"\n\n[DOCUMENTOS ANEXADOS — texto extraído para análise]\n"+documents.map(d=>"--- "+d.filename+" ("+d.format+") ---\n"+d.text).join("\n\n"):"";const contextualContent=content+documentContext;const apiContent=images.length?[{type:"text",text:contextualContent},...images.map(url=>({type:"image_url",image_url:{url}}))]:contextualContent;const visibleContent=displayContent+(documents.length?"\n\n📎 "+documents.map(d=>d.filename).join(", "):"");messageQueue.push({content:apiContent,displayContent:visibleContent,taskMode:(executionMode||isExplicitActionRequest(displayContent))&&!images.length,conversationId:activeId,agentId:activeConversation()?.agentId||$("chat-agent")?.value||"general",createdAt:Date.now()});
    renderPendingImages();$("message-input").value="";resizeInput();renderQueue();const bar=$("metal-prompt-bar");bar.classList.remove("is-sending");void bar.offsetWidth;bar.classList.add("is-sending");setTimeout(()=>bar.classList.remove("is-sending"),800);
    if(!busy&&!queueNeedsResume)processQueue();
  }

  function readImageFile(file){return new Promise((resolve,reject)=>{if(!file.type.startsWith("image/")&&!/\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)){reject(new Error("Formato de imagem inválido."));return}const reader=new FileReader();reader.onerror=()=>reject(new Error("Falha ao ler imagem."));reader.onload=()=>{const img=new Image();img.onload=()=>{const max=1800,scale=Math.min(1,max/Math.max(img.width,img.height)),canvas=document.createElement("canvas");canvas.width=Math.max(1,Math.round(img.width*scale));canvas.height=Math.max(1,Math.round(img.height*scale));canvas.getContext("2d").drawImage(img,0,0,canvas.width,canvas.height);resolve(canvas.toDataURL("image/jpeg",0.84))};img.onerror=()=>reject(new Error("Imagem inv?lida."));img.src=reader.result};reader.readAsDataURL(file)})}
  function setComposerStatus(message){const status=$("composer-status");if(!status)return;status.textContent=message||"";status.hidden=!message}
  async function attachImages(files){for(const file of files){try{pendingImages.push(await readImageFile(file))}catch(e){setComposerStatus(e.message)}}renderPendingImages()}
  async function attachDocuments(files){
    for(const file of files){
      if(file.type.startsWith("image/")||/\\.(png|jpe?g|webp|gif|bmp)$/i.test(file.name)){await attachImages([file]);continue}
      setComposerStatus("Lendo "+file.name+"…");
      try{
        const response=await fetch(API+"/chat/attachments/"+encodeURIComponent(file.name),{method:"POST",headers:{"Content-Type":file.type||"application/octet-stream"},body:file,signal:AbortSignal.timeout(120000)});
        const data=await response.json().catch(()=>({}));
        if(!response.ok)throw new Error(data.detail||"Falha ao ler o documento.");
        pendingDocuments.push({filename:data.filename,format:data.format,text:data.text,saved_file:data.saved_file});
        setComposerStatus(file.name+" lido. Documento pronto para anexar à mensagem.");
      }catch(error){setComposerStatus("Não foi possível ler "+file.name+": "+error.message)}
    }
    renderPendingImages();
  }
  function renderPendingImages(){let host=$("pending-image-list");if(!host){host=document.createElement("div");host.id="pending-image-list";host.className="pending-image-list";$("message-input").parentElement.insertBefore(host,$("message-input"))}host.replaceChildren();pendingImages.forEach((url,index)=>{const wrap=document.createElement("span"),img=document.createElement("img"),remove=document.createElement("button");img.src=url;img.alt="Imagem a enviar";remove.type="button";remove.textContent="×";remove.title="Remover imagem";remove.setAttribute("aria-label","Remover imagem");remove.addEventListener("click",()=>{pendingImages.splice(index,1);renderPendingImages()});wrap.append(img,remove);host.append(wrap)});pendingDocuments.forEach((doc,index)=>{const wrap=document.createElement("span"),chip=document.createElement("small"),remove=document.createElement("button");wrap.className="pending-document-chip";chip.textContent="📄 "+doc.filename;remove.type="button";remove.textContent="×";remove.title="Remover documento";remove.addEventListener("click",()=>{pendingDocuments.splice(index,1);renderPendingImages()});wrap.append(chip,remove);host.append(wrap)});const editButton=$("edit-image");if(editButton)editButton.disabled=!pendingImages.length}
  async function editImage(){if(imageEditBusy)return;const prompt=$("message-input").value.trim(),source=pendingImages[0];if(!source){setComposerStatus("Anexe uma foto antes de solicitar a edição.");return}if(!prompt){$("message-input").focus();setComposerStatus("Descreva o que deseja mudar na foto.");return}const button=$("edit-image");imageEditBusy=true;button.disabled=true;button.textContent="Editando…";setComposerStatus("Editando sua foto localmente. A composição original será preservada tanto quanto possível.");try{const r=await fetch(API+"/images/edit",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({prompt,image_data_url:source,include_data_url:false}),signal:AbortSignal.timeout(900000)});const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.detail||data.message||"Não foi possível editar a foto.");const c=activeConversation(),userContent=[{type:"text",text:prompt},{type:"image_url",image_url:{url:source}}];c.messages.push({role:"user",content:userContent});const msg={role:"assistant",content:"Foto editada localmente: "+(data.filename||"imagem editada"),image:data.image_url||data.data_url};c.messages.push(msg);c.updatedAt=Date.now();if(activeId===c.id){appendMessage("user",userContent);appendMessage("assistant",msg.content);const img=document.createElement("img");img.className="chat-image-attachment generated-image";img.alt="Foto editada pela MYRA";img.src=msg.image;$("messages").lastElementChild.querySelector(".message-content").append(img)}save(STORAGE_KEY,conversations.slice(0,60));pendingImages.shift();renderPendingImages();$("message-input").value="";resizeInput();setComposerStatus("Edição concluída. A foto original permanece no histórico da conversa.");}catch(e){setComposerStatus("Falha na edição: "+e.message)}finally{imageEditBusy=false;button.disabled=!pendingImages.length;button.textContent="✎ Editar foto"}}
  function appendImageGenerationProgress(){
    const row=document.createElement("div");row.className="message assistant image-generation-message";
    const body=document.createElement("div");body.className="message-content";
    const label=document.createElement("div");label.className="message-label";label.textContent="MYRA";
    const head=document.createElement("div");head.className="image-generation-progress-head";
    const spinner=document.createElement("span");spinner.className="image-generation-spinner";spinner.setAttribute("aria-hidden","true");
    const title=document.createElement("strong");title.textContent="Gerando imagem";head.append(spinner,title);
    const detail=document.createElement("p");detail.className="image-generation-progress-detail";detail.textContent="Preparando o gerador local…";
    const caption=document.createElement("small");caption.textContent="Componente de geração de imagem";
    const pre=document.createElement("pre");pre.className="image-generation-command";const code=document.createElement("code");code.textContent='npx shadcn@latest add "https://21st.dev/r/starc007/image-generation"';pre.append(code);
    body.append(label,head,detail,caption,pre);row.append(body);$("messages").append(row);$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight;
    return {update(message,state="running"){detail.textContent=message;row.dataset.state=state;title.textContent=state==="done"?"Imagem pronta":state==="error"?"Falha na geração":"Gerando imagem";spinner.hidden=state!=="running";}};
  }
  function resolveImagePrompt(prompt){
    const value=String(prompt||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase();
    const generic=/^(?:(?:por favor|agora)\s+)?(?:crie|criar|gere|gerar|desenhe|desenhar|faca|fazer|produza|produzir|create|generate|draw|make)\s+(?:(?:a|uma|essa|esta|the)\s+)?(?:imagem|foto|ilustracao|image|picture|illustration|ela|isso)(?:\s+agora)?[.!?]*$/.test(value);
    if(!generic)return prompt;
    const messages=activeConversation()?.messages||[];
    const lastAssistant=[...messages].reverse().find(m=>m?.role==="assistant"&&typeof m.content==="string"&&m.content.trim());
    if(lastAssistant){
      const content=lastAssistant.content;
      const described=content.match(/(?:Imagine|Imagine a|Imagine um|Imagine uma)\s+([\s\S]*?)(?=\n\s*(?:Se voce quiser|Se quiser|Posso continuar|If you want)|$)/i);
      const candidate=(described?.[1]||content).replace(/(?:Desculpe,? mas como uma assistente de texto[\s\S]*$|Se voce quiser[\s\S]*$)/i,"").trim();
      if(candidate.length>=35&&!/nao posso criar imagens|nao posso gerar imagens|como uma assistente de texto/i.test(candidate)){
        return "Create a photorealistic image based on this fictional character description from the previous chat. Preserve the described appearance and action: "+candidate;
      }
    }
    const priorUser=[...messages].reverse().find(m=>m?.role==="user"&&typeof m.content==="string"&&/\b(?:imagem|foto|ilustracao|image|picture)\b/i.test(m.content));
    if(priorUser)return priorUser.content;
    return prompt;
  }
  async function generateImage(){if(imageGenerationBusy)return;
    const input=$("message-input"),prompt=resolveImagePrompt(input.value.trim()),button=$("generate-image");
    if(!prompt){input.focus();setComposerStatus("Descreva a imagem que deseja gerar.");return}
    if(!online){setComposerStatus("A API local da MYRA está offline. Verifique o serviço antes de gerar.");return}
    imageGenerationBusy=true;button.disabled=true;$("send-button").disabled=true;button.textContent="Gerando…";const progress=appendImageGenerationProgress();progress.update("Verificando o ComfyUI local e preparando a fila de geração.");setComposerStatus("Preparando o gerador local…");
    try{
      const health=await fetch(API+"/images/status",{cache:"no-store",signal:AbortSignal.timeout(10000)});
      const status=await health.json().catch(()=>({}));
      if(!health.ok||!status.available)throw new Error(status.message||"ComfyUI não está disponível. Abra Servidores e Docker e verifique o serviço de imagens.");
      progress.update("O ComfyUI está processando a imagem local em 512 × 768. Isso pode levar alguns minutos.");setComposerStatus("Gerando imagem local em 512 × 768. Isso pode levar alguns minutos; mantenha a MYRA aberta.");
      const r=await fetch(API+"/images/generate",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({prompt,provider:"comfyui",width:512,height:768,steps:25,include_data_url:false}),
        signal:AbortSignal.timeout(900000),cache:"no-store"
      });
      const data=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(typeof data.detail==="string"?data.detail:(data.detail?.message||data.message||("HTTP "+r.status)));
      const imageUrl=data.image_url||data.data_url;
      if(!imageUrl)throw new Error("O gerador terminou, mas a API não retornou o endereço da imagem.");
      progress.update("Imagem concluída. Carregando o arquivo de saída na conversa.", "done");setComposerStatus("Imagem pronta. Carregando o resultado na conversa…");
      const img=document.createElement("img");img.className="chat-image-attachment generated-image";img.alt="Imagem gerada pela MYRA";img.loading="eager";
      img.src=imageUrl;
      await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error("A imagem foi gerada, mas a interface não conseguiu carregá-la. Verifique o endpoint local /images/files."));});
      const c=activeConversation();
      if(!c)throw new Error("Não há conversa ativa para salvar a imagem.");
      const msg={role:"assistant",content:"Imagem gerada localmente: "+(data.filename||"imagem"),image:imageUrl};
      c.messages.push(msg);c.updatedAt=Date.now();
      if(activeId===c.id){appendMessage("assistant",msg.content);$("messages").lastElementChild.querySelector(".message-content").append(img,createImageDownloadButton(imageUrl,data.filename||"myra-image.png"));$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight}
      save(STORAGE_KEY,conversations.slice(0,60));input.value="";resizeInput();
      setComposerStatus("Imagem gerada e exibida na conversa. Processamento local concluído.");
    }catch(e){
      console.error("[MYRA IMAGE GENERATION]",e);
      progress?.update("Falha ao gerar imagem: "+(e?.message||String(e))+". Seu prompt foi mantido; tente novamente após corrigir o serviço.", "error");setComposerStatus("Falha ao gerar imagem: "+(e?.message||String(e))+". Seu prompt foi mantido; tente novamente após corrigir o serviço.");
    }finally{imageGenerationBusy=false;button.disabled=false;button.textContent="✧ Gerar imagem";resizeInput()}
  }

  async function startVoiceInput(){if(voiceStarting||voiceTranscriptionBusy)return;
    const button=$("voice-input");
    if(mediaRecorder && mediaRecorder.state==="recording"){voiceLoopActive=false;mediaRecorder.stop();button.classList.remove("recording");button.title="Processando ?udio localmente";if(voiceAudio)voiceAudio.pause();window.speechSynthesis?.cancel();return}
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){setComposerStatus("Grava\u00e7\u00e3o de \u00e1udio n\u00e3o dispon\u00edvel neste ambiente.");return}
    if(voiceAudio&&!voiceAudio.paused){voiceAudio.pause();voiceAudio.currentTime=0}
    try{
      voiceStarting=true;const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});voiceStarting=false;
      recordedChunks=[];voiceLoopActive=liveVoiceMode||!!voicePrefs().continuous;const mime=MediaRecorder.isTypeSupported("audio/webm;codecs=opus")?"audio/webm;codecs=opus":"audio/webm";
      mediaRecorder=new MediaRecorder(stream,{mimeType:mime});
      mediaRecorder.ondataavailable=e=>{if(e.data?.size)recordedChunks.push(e.data)};
      mediaRecorder.onerror=e=>{setComposerStatus("Falha na grava\u00e7\u00e3o: "+(e.error?.message||"erro desconhecido"));stream.getTracks().forEach(t=>t.stop())};
      mediaRecorder.onstop=async()=>{
        stream.getTracks().forEach(t=>t.stop());if(liveVadFrame)cancelAnimationFrame(liveVadFrame);liveVadFrame=0;if(liveVadContext){try{await liveVadContext.close()}catch(_){}liveVadContext=null;}button.classList.remove("recording");button.title="Ditado local com Whisper";
        const blob=new Blob(recordedChunks,{type:mime});recordedChunks=[];
        if(!blob.size){setComposerStatus("Nenhum ?udio foi capturado.");return}
        setComposerStatus("Transcrevendo com o Whisper local...");voiceTranscriptionBusy=true;button.disabled=true;
        try{const r=await fetch(API+"/voice/transcribe",{method:"POST",headers:{"Content-Type":mime},body:blob,signal:AbortSignal.timeout(180000)});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha na transcri\u00e7\u00e3o local.");
          const input=$("message-input");input.value=(input.value.trim()?input.value.trim()+" ":"")+(d.text||"");resizeInput();input.focus();setComposerStatus(d.text?"Transcri\u00e7\u00e3o local conclu\u00edda.":"Nenhuma fala reconhecida.");if(d.text&&(voicePrefs().auto_send||liveVoiceMode)){speakNextResponse=true;sendMessage(input.value);input.value="";resizeInput()}
        }catch(e){setComposerStatus("Voz local indispon\u00edvel: "+e.message)}finally{voiceTranscriptionBusy=false;button.disabled=false}
      };
      mediaRecorder.start();button.classList.add("recording");button.title="Gravando — toque para finalizar";setComposerStatus("Ouvindo. Toque novamente para finalizar a grava\u00e7\u00e3o.");
    }catch(e){voiceStarting=false;setComposerStatus("N\u00e3o foi poss\u00edvel acessar o microfone: "+e.message)}
  }
  function setWakeIndicator(state,label){const el=$("wake-indicator");if(el){el.dataset.state=state;const b=el.querySelector("b");if(b)b.textContent=label;}const top=$("top-wake-toggle");if(top){const active=state==="listening"||state==="activated"||state==="processing";top.dataset.state=state;top.setAttribute("aria-pressed",String(active));top.textContent=active?"Hey MYRA · ATIVA":"Hey MYRA";top.title=label;}}
  async function persistWakePreference(enabled){try{const r=await fetch(API+"/runtime/config",{cache:"no-store"});const cfg=await r.json();cfg.voice={...(cfg.voice||{}),wake_word:!!enabled};const saved=await fetch(API+"/runtime/config",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({config:cfg})});if(!saved.ok)throw new Error("Não foi possível salvar a preferência de ativação.");runtimeConfig=await saved.json()}catch(e){console.warn("[MYRA WAKE CONFIG]",e)}}
  async function stopWakeWord(persist=false){
    wakeActive=false;wakeArmed=false;wakeBusy=false;wakeAbortController?.abort();wakeAbortController=null;
    if(wakeFrame)cancelAnimationFrame(wakeFrame);wakeFrame=0;
    try{if(wakeRecorder&&wakeRecorder.state!=="inactive")wakeRecorder.stop()}catch(_){}
    wakeRecorder=null;wakeChunks=[];
    if(wakeStream)wakeStream.getTracks().forEach(t=>t.stop());wakeStream=null;
    if(wakeContext){try{await wakeContext.close()}catch(_){}}wakeContext=null;wakeAnalyser=null;
    const b=$("voice-wake-toggle");if(b){b.textContent="Ativar Hey MYRA";b.classList.remove("recording")}if($("voice-wake-word"))$("voice-wake-word").checked=false;
    const status=$("voice-runtime-status");if(status)status.textContent="Hey MYRA desativado. Microfone liberado.";setWakeIndicator("off","HEY MYRA DESLIGADO");
  }
  function playWakeActivationChime(){
    try{
      const AudioCtx=window.AudioContext||window.webkitAudioContext;if(!AudioCtx)return;
      const ctx=new AudioCtx();const now=ctx.currentTime;
      // Dois tons ascendentes: confirmação curta, audível e diferente da voz da MYRA.
      [[660,0],[990,0.13]].forEach(([frequency,delay])=>{
        const oscillator=ctx.createOscillator(),gain=ctx.createGain();
        oscillator.type="sine";oscillator.frequency.setValueAtTime(frequency,now+delay);
        gain.gain.setValueAtTime(0.0001,now+delay);
        gain.gain.exponentialRampToValueAtTime(0.055,now+delay+0.018);
        gain.gain.exponentialRampToValueAtTime(0.0001,now+delay+0.19);
        oscillator.connect(gain);gain.connect(ctx.destination);
        oscillator.start(now+delay);oscillator.stop(now+delay+0.20);
      });
      setTimeout(()=>ctx.close().catch(()=>{}),450);
    }catch(error){console.debug("[MYRA WAKE CHIME]",error)}
  }  async function transcribeWakeSegment(blob){
    if(!blob?.size||wakeBusy||!wakeActive)return;wakeBusy=true;const controller=new AbortController();wakeAbortController=controller;
    setWakeIndicator("processing",wakeArmed?"RECONHECENDO COMANDO":"RECONHECENDO PALAVRA-CHAVE");
    try{
      const mime=blob.type||"audio/webm";const signal=AbortSignal.any?AbortSignal.any([controller.signal,AbortSignal.timeout(45000)]):controller.signal;const r=await fetch(API+"/voice/transcribe",{method:"POST",headers:{"Content-Type":mime},body:blob,signal});
      const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha no reconhecimento local.");
      const transcript=String(d.text||"").trim();if(!transcript){setWakeIndicator(wakeArmed?"activated":"listening",wakeArmed?"MYRA ATIVADA · FALE AGORA":"HEY MYRA · ESCUTANDO");return;}
      const normalized=transcript.normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/[^a-z0-9 ]/g," ").replace(/\s+/g," ").trim();
      const phrase=/\b(?:hey|ei|e ai|oi|ola)\s+(?:myra|mira|maira|mayra|myrah)\b/;
      const match=normalized.match(phrase);
      if(!wakeArmed){
        if(!match){setWakeIndicator("listening","HEY MYRA · ESCUTANDO");return;}
        wakeArmed=true;setWakeIndicator("activated","MYRA ATIVADA · FALE AGORA");showView("chat");$("message-input")?.focus();
        const originalWake=transcript.match(/\b(?:hey|ei|e aí|oi|olá)\s+(?:myra|mira|maira|mayra|myrah)\b/i);const remainder=originalWake?transcript.slice(originalWake.index+originalWake[0].length).replace(/^[,.:;!?\s]+/,"").trim():"";
        const status=$("voice-runtime-status");if(status)status.textContent="MYRA ativada. Aguardando seu comando...";
        playWakeActivationChime();
        if(remainder.length>2){const input=$("message-input");input.value=remainder;resizeInput();wakeArmed=false;speakNextResponse=true;sendMessage(remainder);input.value="";resizeInput();setWakeIndicator("listening","HEY MYRA · ESCUTANDO")}
        return;
      }
      wakeArmed=false;setWakeIndicator("listening","COMANDO RECONHECIDO");
      const input=$("message-input");input.value=transcript;resizeInput();
      if(voicePrefs().auto_send!==false){speakNextResponse=true;sendMessage(transcript);input.value="";resizeInput();setWakeIndicator("listening","HEY MYRA · ESCUTANDO")}
      else {input.focus();const status=$("voice-runtime-status");if(status)status.textContent="Comando reconhecido e inserido no chat. Pressione Enviar.";setWakeIndicator("activated","COMANDO PRONTO · ENVIAR")}
    }catch(e){if(e.name!=="AbortError"){console.warn("[MYRA WAKE]",e);const status=$("voice-runtime-status");if(status)status.textContent="Reconhecimento local: "+e.message;setWakeIndicator("error","FALHA NO RECONHECIMENTO")}}
    finally{if(wakeAbortController===controller){wakeBusy=false;wakeAbortController=null}}
  }
  async function startWakeWord(){
    if(wakeActive){await stopWakeWord();return}
    if(!navigator.mediaDevices?.getUserMedia||!window.MediaRecorder){setWakeIndicator("error","MICROFONE INDISPONÍVEL");setComposerStatus("Microfone contínuo não disponível neste ambiente.");return}
    try{
      wakeStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true}});
      const C=window.AudioContext||window.webkitAudioContext;wakeContext=new C();await wakeContext.resume();const source=wakeContext.createMediaStreamSource(wakeStream);wakeAnalyser=wakeContext.createAnalyser();wakeAnalyser.fftSize=1024;source.connect(wakeAnalyser);
      wakeActive=true;wakeArmed=false;wakeLastVoice=0;wakeRecorder=null;setWakeIndicator("listening","HEY MYRA · ESCUTANDO");
      const button=$("voice-wake-toggle");if(button){button.textContent="Desativar Hey MYRA";button.classList.add("recording")}
      const status=$("voice-runtime-status");if(status)status.textContent="Escutando localmente por Hey MYRA. Diga: Hey MYRA.";if($("voice-wake-word"))$("voice-wake-word").checked=true;
      const data=new Uint8Array(wakeAnalyser.fftSize);
      const tick=()=>{
        if(!wakeActive)return;
        if(voiceAudio&&!voiceAudio.paused){wakeFrame=requestAnimationFrame(tick);return;}
        wakeAnalyser.getByteTimeDomainData(data);let sum=0;for(let i=0;i<data.length;i++){const v=(data[i]-128)/128;sum+=v*v}const rms=Math.sqrt(sum/data.length);const now=performance.now();
        if(rms>.0045){wakeLastVoice=now;if(!wakeRecorder&&!wakeBusy){wakeChunks=[];const mime=MediaRecorder.isTypeSupported("audio/webm;codecs=opus")?"audio/webm;codecs=opus":"audio/webm";wakeRecorder=new MediaRecorder(wakeStream,{mimeType:mime});wakeRecorder.ondataavailable=e=>{if(e.data?.size)wakeChunks.push(e.data)};wakeRecorder.onstop=()=>{const blob=new Blob(wakeChunks,{type:mime});wakeChunks=[];wakeRecorder=null;transcribeWakeSegment(blob)};wakeStartedAt=now;wakeRecorder.start()}}
        if(wakeRecorder&&wakeRecorder.state==="recording"&&((now-wakeLastVoice>1100&&wakeLastVoice>wakeStartedAt)||(now-wakeStartedAt>8000))){wakeRecorder.stop()}
        wakeFrame=requestAnimationFrame(tick);
      };wakeFrame=requestAnimationFrame(tick);
    }catch(e){await stopWakeWord(false);setWakeIndicator("error","ERRO NO MICROFONE");const status=$("voice-runtime-status");if(status)status.textContent="Falha ao ativar Hey MYRA: "+e.message;setComposerStatus("Não foi possível ativar Hey MYRA: "+e.message)}
  }
  function detectSpeechLanguage(text){
    const value=String(text||"").toLowerCase();
    const hasPtMarks=/[\u00e1\u00e0\u00e2\u00e3\u00e9\u00ea\u00ed\u00f3\u00f4\u00f5\u00fa\u00e7]/i.test(value);
    const pt=(value.match(/\b(ol[aá]|oi|obrigad[oa]|voc[eê]|n[aã]o|tamb[eé]m|est[aá]|s[aã]o|a[cç][aã]o|porque|ent[aã]o|isso|essa|esse|sobre|aqui|agora|vamos|fazer|tenho|tem|para|com|uma|mais|como|pode|posso|seu|sua|pela|pelo|das|dos)\b/g)||[]).length;
    const en=(value.match(/\b(the|and|you|your|how|what|when|where|why|can|could|would|should|will|have|has|with|from|this|that|there|here|hello|thanks|please|because|about|into|for|are|was|were|is|not|yes|no|today|tomorrow)\b/g)||[]).length;
    return hasPtMarks||pt>en?"pt-br":"en-us";
  }
  async function speakText(value){
    const text=String(value||"").replace(/```[\s\S]*?```/g,"bloco de c?digo").replace(/[#*_`>]/g,"").trim();if(!text)return;
    const prefs=voicePrefs();const configured=prefs.tts_language||"auto";const language=configured!=="auto"?configured:detectSpeechLanguage(text);
    const voice=language==="pt-br"?(prefs.pt_voice||"pf_dora"):language==="en-gb"?(prefs.en_gb_voice||"bf_emma"):(prefs.en_voice||"af_sarah");
    try{const r=await fetch(API+"/voice/speak",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({text:text.slice(0,12000),language,voice}),signal:AbortSignal.timeout(180000)});if(r.ok){const blob=await r.blob();if(voiceAudio){voiceAudio.pause();URL.revokeObjectURL(voiceAudio.src)}voiceAudio=new Audio(URL.createObjectURL(blob));voiceAudio.onplay=syncVoiceStopVisibility;voiceAudio.onpause=syncVoiceStopVisibility;voiceAudio.onended=()=>{voiceReadBusy=false;syncVoiceStopVisibility();if(liveVoiceMode&&voiceLoopActive)setTimeout(startVoiceInput,500)};await voiceAudio.play();syncVoiceStopVisibility();return}const d=await r.json().catch(()=>({}));throw new Error(d.detail||"Motor Kokoro local indispon\u00edvel")}
    catch(e){console.warn("[MYRA VOICE] Kokoro local indispon\u00edvel",e)}
    // Local OS voice fallback only; no hosted speech or recognition service is used.
    if("speechSynthesis" in window){window.speechSynthesis.cancel();const u=new SpeechSynthesisUtterance(text);u.lang=language==="pt-br"?"pt-BR":language==="en-gb"?"en-GB":"en-US";u.onstart=syncVoiceStopVisibility;u.onend=()=>{voiceReadBusy=false;syncVoiceStopVisibility();if(liveVoiceMode&&voiceLoopActive)setTimeout(startVoiceInput,500)};window.speechSynthesis.speak(u);syncVoiceStopVisibility()}else{voiceReadBusy=false}
  }
  function syncVoiceStopVisibility(){const playing=Boolean((voiceAudio&&!voiceAudio.paused&&!voiceAudio.ended)||("speechSynthesis" in window&&window.speechSynthesis.speaking));const button=$("voice-stop");if(button)button.hidden=!playing}
  function readLastAnswer(){if(voiceReadBusy)return;voiceReadBusy=true;const c=activeConversation(),last=[...(c?.messages||[])].reverse().find(m=>m.role==="assistant");if(!last){voiceReadBusy=false;setComposerStatus("Ainda n\u00e3o h\u00e1 resposta para ler.");return}speakText(last.content)}
  function stopMyraSpeech(){voiceReadBusy=false;liveVoiceMode=false;voiceLoopActive=false;if(voiceAudio){voiceAudio.pause();voiceAudio.currentTime=0}if("speechSynthesis" in window)window.speechSynthesis.cancel();syncVoiceStopVisibility();if(mediaRecorder&&mediaRecorder.state==="recording"){try{mediaRecorder.stop()}catch(_){}}const b=$("voice-live-toggle");if(b){b.setAttribute("aria-pressed","false");b.classList.remove("is-live");b.title="Ativar modo de fala ao vivo";}setComposerStatus("Fala interrompida. Modo ao vivo desativado.");}
  async function toggleLiveVoice(){if(liveVoiceMode){stopMyraSpeech();return}liveVoiceMode=true;voiceLoopActive=true;const b=$("voice-live-toggle");if(b){b.setAttribute("aria-pressed","true");b.classList.add("is-live");b.title="Desativar modo de fala ao vivo";}try{await startVoiceInput()}catch(e){stopMyraSpeech();setComposerStatus("N\u00e3o foi poss\u00edvel iniciar o modo ao vivo: "+e.message)}}
  function voicePrefs(){return runtimeConfig?.voice||{auto_speak:false}}
  async function refreshVoiceStatus(){try{const [r,c]=await Promise.all([fetch(API+"/voice/status",{cache:"no-store"}),fetch(API+"/runtime/config",{cache:"no-store"})]);const d=await r.json(),cfg=await c.json();runtimeConfig=cfg;const status=$("voice-runtime-status");if(status){const stt=d.stt?.package_installed&&d.stt?.model_configured?"Whisper small pronto":"Whisper n\u00e3o configurado";const tts=d.tts?.package_installed&&d.tts?.model_configured?"Kokoro pronto (offline)":"Kokoro incompleto";status.textContent=stt+" | "+tts+" | processamento local"}
      const v=cfg.voice||{};if(v.wake_word&&!wakeActive)setTimeout(()=>{if(!wakeActive)startWakeWord()},800);if($("voice-language"))$("voice-language").value=v.stt_language||"pt";if($("voice-model-path"))$("voice-model-path").value=v.stt_model_path||"";if($("voice-tts-language"))$("voice-tts-language").value=v.tts_language||"auto";if($("voice-pt-voice"))$("voice-pt-voice").value=v.pt_voice||"pf_dora";if($("voice-en-voice"))$("voice-en-voice").value=v.en_voice||"af_sarah";if($("voice-en-gb-voice"))$("voice-en-gb-voice").value=v.en_gb_voice||"bf_emma";if($("voice-speed"))$("voice-speed").value=String(v.tts_speed||1.0);if($("voice-auto-speak"))$("voice-auto-speak").checked=!!v.auto_speak;if($("voice-auto-send"))$("voice-auto-send").checked=v.auto_send!==false;if($("voice-continuous"))$("voice-continuous").checked=!!v.continuous;if($("voice-wake-word"))$("voice-wake-word").checked=!!v.wake_word;
    }catch(e){const el=$("voice-runtime-status");if(el)el.textContent="N\u00e3o foi poss\u00edvel consultar os motores locais: "+e.message}}
  async function saveVoiceSettings(){try{const r=await fetch(API+"/runtime/config");runtimeConfig=await r.json();runtimeConfig.voice={...(runtimeConfig.voice||{}),stt_language:$("voice-language").value,stt_model_path:$("voice-model-path").value.trim(),tts_engine:"kokoro",tts_language:$("voice-tts-language").value,pt_voice:$("voice-pt-voice").value,en_voice:$("voice-en-voice").value,en_gb_voice:$("voice-en-gb-voice").value,tts_speed:Number($("voice-speed").value),auto_speak:$("voice-auto-speak").checked,auto_send:$("voice-auto-send").checked,continuous:$("voice-continuous").checked,wake_word:$("voice-wake-word").checked};const saved=await fetch(API+"/runtime/config",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({config:runtimeConfig})});const d=await saved.json().catch(()=>({}));if(!saved.ok)throw new Error(d.detail||"Falha ao salvar");runtimeConfig=d;$("voice-runtime-status").textContent="Configura\u00e7\u00f5es de voz salvas localmente.";if(d.voice?.wake_word&&!wakeActive)await startWakeWord();else if(!d.voice?.wake_word&&wakeActive)await stopWakeWord();await refreshVoiceStatus()}catch(e){$("voice-runtime-status").textContent="Erro: "+e.message}}

  async function refreshRuntime(){
    const host=$("runtime-containers");if(!host)return;host.textContent="Consultando Docker e servi\u00e7os locais...";
    try{const [sr,cr]=await Promise.all([fetch(API+"/runtime/status",{cache:"no-store"}),fetch(API+"/runtime/config",{cache:"no-store"})]);const status=await sr.json(),cfg=await cr.json();runtimeConfig=cfg;
      $("docker-state").textContent=status.docker?.available?"DISPON\u00cdVEL":status.docker?.installed?"SEM ENGINE":"N\u00c3O INSTALADO";$("docker-version").textContent=status.docker?.available?"Docker "+status.docker.version:"Docker n\u00e3o conectado";$("docker-detail").textContent=status.docker?.error||"Docker \u00e9 opcional; servi\u00e7os locais nativos continuam dispon\u00edveis.";
      $("runtime-mode").value=cfg.mode||"native";$("offline-first").checked=cfg.offline_first!==false;$("external-providers").checked=!!cfg.providers?.external_enabled;
      host.replaceChildren();const items=status.docker?.containers||[];if(!items.length){const p=document.createElement("p");p.textContent=status.docker?.available?"Nenhum container MYRA em execu\u00e7\u00e3o ou instalado.":"Docker Engine indispon\u00edvel. Voc\u00ea pode continuar usando a instala\u00e7\u00e3o nativa.";host.append(p)}items.forEach(item=>{const row=document.createElement("div");row.className="runtime-item";const info=document.createElement("div"),name=document.createElement("b"),meta=document.createElement("small"),actions=document.createElement("div");name.textContent=item.name;meta.textContent=(item.image||"")+" ? "+(item.status||item.state||"");actions.className="runtime-item-actions";info.append(name,meta);row.append(info,actions);["start","restart","stop"].forEach(action=>{const b=document.createElement("button");b.className="soft-button";b.textContent=action==="start"?"Iniciar":action==="restart"?"Reiniciar":"Parar";b.addEventListener("click",()=>runtimeAction(item.name.includes("searxng")?"searxng":"ollama",action));actions.append(b)});host.append(row)});
      const servers=$("runtime-servers");servers.replaceChildren();Object.entries(cfg.servers||{}).forEach(([name,item])=>{const label=document.createElement("label");label.className="runtime-server";const title=document.createElement("span");title.textContent=name.toUpperCase();const input=document.createElement("input");input.dataset.server=name;input.value=item.url||"";input.setAttribute("aria-label","URL "+name);const check=document.createElement("input");check.type="checkbox";check.dataset.serverEnabled=name;check.checked=!!item.enabled;const probe=document.createElement("button");probe.type="button";probe.className="soft-button runtime-probe";probe.textContent="Testar";probe.addEventListener("click",async()=>{probe.disabled=true;probe.textContent="...";try{const pr=await fetch(`${API}/runtime/probe/${name}`,{method:"POST"});const pd=await pr.json().catch(()=>({}));probe.textContent=pd.reachable?"Online":"Offline";probe.title=pd.detail||pd.status_code||""}catch(e){probe.textContent="Erro";probe.title=e.message}finally{probe.disabled=false}});label.append(title,input,check,probe);servers.append(label)});
      const channels=$("runtime-channels");channels.replaceChildren();Object.entries(cfg.channels||{}).forEach(([name,enabled])=>{const label=document.createElement("label");label.className="runtime-channel";const cb=document.createElement("input");cb.type="checkbox";cb.dataset.channel=name;cb.checked=!!enabled;const span=document.createElement("span");span.textContent=name.replace(/_/g," ");label.append(cb,span);channels.append(label)});
      await refreshVoiceStatus();
    }catch(e){host.textContent="Falha ao consultar infraestrutura local: "+e.message}
  }
  async function runtimeAction(service,action){try{const r=await fetch(`${API}/runtime/service/${service}/${action}`,{method:"POST"});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Docker action failed");$("runtime-save-status").textContent=`${service}: ${action} solicitado.`;await refreshRuntime()}catch(e){$("runtime-save-status").textContent="Docker: "+e.message}}
  async function saveRuntimeConfig(){try{const cfg=runtimeConfig||await (await fetch(API+"/runtime/config")).json();cfg.mode=$("runtime-mode").value;cfg.offline_first=$("offline-first").checked;cfg.providers={...(cfg.providers||{}),external_enabled:$("external-providers").checked};document.querySelectorAll("[data-server]").forEach(input=>{const n=input.dataset.server;cfg.servers[n]={...(cfg.servers[n]||{}),url:input.value.trim()}});document.querySelectorAll("[data-server-enabled]").forEach(input=>{const n=input.dataset.serverEnabled;cfg.servers[n].enabled=input.checked});document.querySelectorAll("[data-channel]").forEach(input=>cfg.channels[input.dataset.channel]=input.checked);const r=await fetch(API+"/runtime/config",{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({config:cfg})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha ao salvar");runtimeConfig=d;$("runtime-save-status").textContent="Configura\u00e7\u00e3o salva no perfil local da MYRA."}catch(e){$("runtime-save-status").textContent="Erro: "+e.message}}
  async function refreshToolApproval(){
    try{
      const response=await fetch(API+"/confirmation_status",{cache:"no-store",signal:AbortSignal.timeout(2500)});
      if(!response.ok)return;
      const approval=await response.json();if(!approval.pending)return;
      const host=$("messages");if(!host)return;
      const key=String(approval.timestamp||"")+"|"+String(approval.acao||"");
      if(host.querySelector(`[data-approval-key="${CSS.escape(key)}"]`))return;
      const card=document.createElement("article");card.className="tool-approval-card";card.dataset.approvalKey=key;
      const heading=document.createElement("strong");heading.textContent="Ação requer sua aprovação";
      const action=document.createElement("b");action.textContent=approval.acao||"Ação protegida";
      const detail=document.createElement("p");detail.textContent=approval.detalhes||"A MYRA solicitou autorização antes de continuar.";
      const expiry=document.createElement("small");expiry.textContent="Expira em "+Math.ceil((approval.expires_in||0)/60)+" min. Nenhuma ação será executada sem sua aprovação.";
      const controls=document.createElement("div");controls.className="tool-approval-actions";
      const approve=document.createElement("button");approve.type="button";approve.className="primary-button";approve.textContent="Aprovar e executar";
      const cancel=document.createElement("button");cancel.type="button";cancel.className="soft-button";cancel.textContent="Cancelar";
      const status=document.createElement("p");status.className="tool-approval-status";status.setAttribute("role","status");
      const supported=["email_delete","delete_file","move_file","email_reply","email_send"].includes(approval.acao_pendente);
      approve.disabled=!supported;
      if(!supported){status.textContent="Esta ação ainda não possui execução de aprovação conectada."}
      approve.addEventListener("click",async()=>{approve.disabled=true;cancel.disabled=true;status.textContent="Executando ação aprovada…";try{const r=await fetch(API+"/confirm_and_execute",{method:"POST",signal:AbortSignal.timeout(120000)});const d=await r.json().catch(()=>({}));if(!r.ok||d.status==="erro")throw new Error(d.detail||d.result||"Falha ao executar");status.textContent=d.result||"Ação aprovada e executada.";card.dataset.approvalComplete="true"}catch(e){status.textContent="Não foi possível concluir: "+e.message;approve.disabled=false;cancel.disabled=false}});
      cancel.addEventListener("click",async()=>{approve.disabled=true;cancel.disabled=true;try{const r=await fetch(API+"/cancel_confirmation",{method:"POST"});const d=await r.json().catch(()=>({}));status.textContent=d.result||"Ação cancelada.";card.dataset.approvalComplete="true"}catch(e){status.textContent="Falha ao cancelar: "+e.message;approve.disabled=false;cancel.disabled=false}});
      controls.append(approve,cancel);card.append(heading,action,detail,expiry,controls,status);host.append(card);$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight;
    }catch(_){}
  }
  async function waitForTaskCompletion(){
    const started=Date.now();
    while(Date.now()-started<30*60*1000){
      await new Promise(resolve=>setTimeout(resolve,1100));
      await refreshToolApproval();
      try{const r=await fetch(API+"/task_status",{cache:"no-store"});if(!r.ok)continue;const s=await r.json();if(s.state!=="running")return s;}catch(_){}
    }
    return {state:"timeout",resultado:"A tarefa continua sem confirma\u00e7\u00e3o ap\u00f3s 30 minutos. Consulte Atividades."};
  }
  function resolveDirectWebUrl(text){
    const value=String(text||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim().toLowerCase().replace(/[.!?]+$/,"");
    const match=value.match(/^(?:(?:por favor|please),?\s+)?(?:abra|abre|acesse|acessa|visite|open|launch|go to)\s+(?:(?:o|a|no|na|the)\s+)?(.+)$/i);
    if(!match)return null;
    const target=match[1].trim();
    const sites={
      "youtube":{url:"https://www.youtube.com",label:"YouTube"},
      "gmail":{url:"https://mail.google.com",label:"Gmail"},
      "google":{url:"https://www.google.com",label:"Google"},
      "google drive":{url:"https://drive.google.com",label:"Google Drive"},
      "google calendar":{url:"https://calendar.google.com",label:"Google Calendar"},
      "whatsapp web":{url:"https://web.whatsapp.com",label:"WhatsApp Web"},
      "github":{url:"https://github.com",label:"GitHub"},
      "instagram":{url:"https://www.instagram.com",label:"Instagram"},
      "facebook":{url:"https://www.facebook.com",label:"Facebook"},
      "linkedin":{url:"https://www.linkedin.com",label:"LinkedIn"}
    };
    return sites[target]||null;
  }
  async function processQueue(){
    if(busy||queueNeedsResume||!messageQueue.length)return;
    const queued=messageQueue.shift(),content=queued.content,displayContent=queued.displayContent||queued.content,taskMode=queued.taskMode;
    renderQueue();
    let c=conversations.find(x=>x.id===queued.conversationId)||activeConversation();if(!c){createConversation();c=activeConversation()}
    c.messages.push({role:"user",content:content});c.updatedAt=Date.now();
    if(c.title==="Nova conversa")c.title=displayContent.slice(0,38)+(displayContent.length>38?".":"");
    if(activeId===c.id){$("welcome").hidden=true;appendMessage("user",content)}setBusy(true);
    save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();
    try{
      await setChatActivity(true);let answer;
      if(taskMode){
        const directSite=resolveDirectWebUrl(displayContent);
        if(directSite){
          let opened;
          if(window.__TAURI__?.core?.invoke)opened=await window.__TAURI__.core.invoke("open_external_url",{url:directSite.url});
          else opened=window.open(directSite.url,"_blank","noopener,noreferrer");
          if(opened?.ok===false||opened===null)throw new Error("O navegador bloqueou a abertura de "+directSite.label+".");
          answer="Abri "+directSite.label+" no navegador padrão.";
        }else{
        const previous=c.messages.slice(0,-1).slice(-6);
        const refers=/(isso|esse|essa|ele|ela|dessa|desse|continue|that|it)/i.test(content);
        const objective=refers&&previous.length?("CONTEXTO RECENTE:"+String.fromCharCode(10)+previous.map(m=>m.role+": "+m.content.slice(0,500)).join(String.fromCharCode(10))+String.fromCharCode(10,10)+"PEDIDO ATUAL:"+String.fromCharCode(10)+content):content;
        const res=await fetch(API+"/task_start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({objetivo:objective.slice(0,4000),max_passos:20})});
        const data=await res.json().catch(()=>({}));if(!res.ok)throw new Error(data.detail||data.result||"Backend HTTP "+res.status);
        const final=await waitForTaskCompletion();
        answer=final.state==="done"?(final.resultado||"Tarefa conclu?da."):final.state==="error"?(final.erro||"A tarefa falhou."):final.state==="timeout"?final.resultado:final.state==="idle"?"A tarefa foi encerrada.":("Estado da tarefa: "+final.state);
        // Tarefas continuam no chat; a aba Atividades fica acessível pela navegação, sem redirecionamento forçado.
        }
      }else{
        const res=await fetch(API+"/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"myra-agent",stream:false,metadata:{chat_id:c.id,user_id:"local-user",agent_id:queued.agentId||c.agentId||"general"},messages:c.messages.map(m=>({role:m.role,content:m.content}))}),signal:AbortSignal.timeout(180000)});
        if(!res.ok)throw new Error("Backend HTTP "+res.status+": "+(await res.text()).slice(0,160));
        const data=await res.json();answer=data?.choices?.[0]?.message?.content;
        if(typeof answer!=="string"||!answer.trim())throw new Error("A MYRA retornou uma resposta vazia.");
        answer=answer.trim();
      }
      c.messages.push({role:"assistant",content:answer});c.updatedAt=Date.now();if(activeId===c.id)appendMessage("assistant",answer);save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();if(voicePrefs().auto_speak||voicePrefs().continuous||speakNextResponse||liveVoiceMode){speakNextResponse=false;speakText(answer);}
    }catch(e){
      const failure="Não consegui concluir. "+(e?.name==="TimeoutError"?"O modelo demorou mais de 120 segundos. Verifique o modelo local e tente novamente.":(e?.message||"Verifique o backend local."));
      c.messages.push({role:"assistant",content:failure});c.updatedAt=Date.now();if(activeId===c.id)appendMessage("assistant",failure);save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();
      console.error("[MYRA CHAT]",e);
    }finally{
      await refreshToolApproval();
      await setChatActivity(false);setBusy(false);refreshTaskStatus();
      if(messageQueue.length)processQueue();else $("message-input").focus();
    }
  }
  function resizeInput(){const el=$("message-input");el.style.height="auto";el.style.height=Math.min(el.scrollHeight,130)+"px";$("send-button").disabled=!el.value.trim()}
  async function checkBackend(){try{const r=await fetch(API+"/",{cache:"no-store",signal:AbortSignal.timeout(1800)});online=r.ok}catch(_){online=false}const cls=online?"online":"offline";$("service-light").className="service-light "+cls;$("status-dot").className="status-dot "+cls;$("service-title").textContent=online?"MYRA conectada":"MYRA offline";$("service-subtitle").textContent=online?"Backend local disponível":"Backend local indisponível";$("status-text").textContent=online?"Sistema operacional":"Aguardando backend"}
  async function refreshTaskStatus(){try{const r=await fetch(API+"/task_status",{cache:"no-store",signal:AbortSignal.timeout(1800)});if(!r.ok)return;const s=await r.json(),state=s.state||"idle",paused=state==="paused"||state==="pausado"||/PAUSADO/i.test(s.passo_atual||""),active=state==="running"&&!paused;taskModelLocked=active||paused;setModelSelectionLocked(taskModelLocked);$("activity-count").textContent=active?"1":"0";$("tool-state").textContent=active?"Em execução":"Aguardando";$("activity-title").textContent=paused?"Tarefa pausada":active?"MYRA está executando":state==="error"?"A última tarefa falhou":state==="done"?"Última tarefa concluída":"Nenhuma atividade em andamento";$("activity-description").textContent=paused?"A tarefa foi salva e pode ser retomada.":active?(s.objetivo||"Tarefa em andamento."):state==="error"?(s.erro||"Execução interrompida."):state==="done"?(s.resultado||"A MYRA concluiu a tarefa."):"Ative o modo Executar tarefa no chat para delegar ações à MYRA.";$("activity-step").hidden=!active&&!paused;$("activity-step").textContent=active||paused?[s.passo_atual||"Planejando",s.passo_num?"Etapa "+s.passo_num+(s.passo_total?" de "+s.passo_total:""):""].filter(Boolean).join(" · "):"";$("activity-symbol").textContent=paused?"Ⅱ":active?"◌":state==="done"?"✓":state==="error"?"⚠":"⌁";$("activity-pause").disabled=!active;$("activity-resume").disabled=!paused;$("activity-takeover").disabled=!active&&!paused;$("activity-cancel").disabled=!active&&!paused}catch(_){}}
  async function runActivityAction(action){
    const status=$("activity-action-status");
    const buttons=["activity-pause","activity-resume","activity-takeover","activity-cancel"].map(id=>$(id)).filter(Boolean);
    buttons.forEach(b=>b.disabled=true);
    if(status)status.textContent="Executando ação...";
    try{
      if(action==="pause"){
        const r=await fetch(API+"/task_pause",{method:"POST",signal:AbortSignal.timeout(5000)});
        const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||d.result||"Não foi possível pausar a tarefa.");
        if(status)status.textContent=d.result||"Pausa solicitada. A MYRA vai parar no próximo ponto seguro.";
      }else if(action==="resume"){
        let taskId="";
        try{const sr=await fetch(API+"/task_status",{cache:"no-store"});if(sr.ok){const s=await sr.json();if(s.state==="paused"||s.state==="pausado"||/PAUSADO/i.test(s.passo_atual||""))taskId=s.task_id||s.id||"";}}catch(_){}
        if(!taskId){
          const pr=await fetch(API+"/task_pendentes?limite=10",{cache:"no-store"});
          const pd=await pr.json().catch(()=>({}));const pending=(pd.tasks||[]).find(t=>t&&["pausado","interrompido"].includes(String(t.estado||"").toLowerCase())&&(t.task_id||t.id));
          taskId=pending?.task_id||pending?.id||"";
        }
        if(!taskId)throw new Error("Não há tarefa pausada disponível para retomar.");
        const r=await fetch(API+"/task_resume",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task_id:taskId}),signal:AbortSignal.timeout(8000)});
        const d=await r.json().catch(()=>({}));if(!r.ok||d.status==="erro")throw new Error(d.detail||d.result||"Não foi possível retomar a tarefa.");
        if(status)status.textContent=d.result||"Retomada solicitada.";
      }else if(action==="cancel"){
        if(!confirm("Deseja realmente cancelar a tarefa atual?"))return;
        let result;
        if(window.__TAURI__?.core?.invoke)result=await window.__TAURI__.core.invoke("cancel_task");
        else{const r=await fetch(API+"/task_cancel",{method:"POST",signal:AbortSignal.timeout(5000)});result=await r.json().catch(()=>({}));if(!r.ok)throw new Error(result.detail||"Não foi possível cancelar.");}
        if(status)status.textContent=result?.result||"Cancelamento solicitado.";
      }else if(action==="takeover"){
        if(!window.__TAURI__?.core?.invoke)throw new Error("Assumir o navegador exige a versão desktop do MYRA.");
        const result=await window.__TAURI__.core.invoke("focus_chrome_window");
        if(result?.ok===false)throw new Error(result.error||"Nenhuma janela do Chrome foi encontrada.");
        if(status)status.textContent="Janela do Chrome trazida para primeiro plano.";
      }
      await refreshTaskStatus();
    }catch(error){
      if(status)status.textContent="Falha: "+(error?.message||String(error));
    }finally{await refreshTaskStatus();buttons.forEach(b=>{if(!b.disabled)b.disabled=false;});}
  }
  async function refreshModels(){const list=$("model-list");if(!list)return;list.innerHTML='<div class="model-empty">Consultando Ollama...</div>';try{const r=await fetch(API+"/models/local",{cache:"no-store",signal:AbortSignal.timeout(3000)});if(!r.ok)throw new Error("Endpoint de modelos indisponível");const data=await r.json();const models=data.models||[];selectedModel=data.selected||"";$("model-count").textContent=models.length+" INSTALADOS";$("current-model").textContent=selectedModel||"Não selecionado";$("activity-model").textContent=selectedModel||"—";["quick-model","settings-model"].forEach(id=>{const sel=$(id);if(!sel)return;sel.replaceChildren();models.forEach(m=>{const o=document.createElement("option");o.value=m.name;o.textContent=m.name;sel.appendChild(o)});if(selectedModel)sel.value=selectedModel});list.replaceChildren();if(!models.length){list.innerHTML='<div class="model-empty">Nenhum modelo local encontrado. Instale um modelo pelo Ollama e atualize.</div>';return}models.forEach(m=>{const row=document.createElement("div");row.className="model-row"+(m.name===selectedModel?" active":"");const info=document.createElement("div");info.className="model-row-icon";info.innerHTML=iconSvg("cpu");const details=document.createElement("div");details.className="model-row-info";const name=document.createElement("b");name.textContent=m.name;const sub=document.createElement("small");sub.textContent=(m.parameter_size||"Modelo local")+" · "+(m.quantization_level||"Ollama");details.append(name,sub);const btn=document.createElement("button");btn.textContent=m.name===selectedModel?"Em uso":"Selecionar";btn.disabled=m.name===selectedModel;btn.addEventListener("click",()=>{stageModelSelection(m.name);$("model-settings-status").textContent="Modelo selecionado como rascunho. Clique em Salvar modelo para aplicar."});row.append(info,details,btn);list.append(row)})}catch(e){list.innerHTML='<div class="model-empty">Não foi possível listar os modelos. '+escapeText(e.message)+'</div>'}}
  function escapeText(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
  function setModelSelectionLocked(locked){taskModelLocked=Boolean(locked);["quick-model","settings-model","model-settings-save","top-model-save"].forEach(id=>{const el=$(id);if(el)el.disabled=taskModelLocked});if(taskModelLocked){if($("quick-model"))$("quick-model").value=selectedModel;if($("settings-model"))$("settings-model").value=selectedModel;$("model-settings-status").textContent="Modelo bloqueado: aguarde a tarefa atual terminar."}}
  function stageModelSelection(name){if(taskModelLocked){setModelSelectionLocked(true);return}$("settings-model").value=name;$("quick-model").value=name;$("model-settings-status").textContent="Alteração pendente. Clique em Salvar modelo.";}
  async function selectModel(name){if(!name)return;if(taskModelLocked){setModelSelectionLocked(true);showModal("Modelo bloqueado","A MYRA só poderá trocar o modelo depois que a tarefa atual terminar.","");return;}return withButtonLoader(null,async()=>{try{const r=await fetch(API+"/models/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:name})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Não foi possível alterar o modelo");selectedModel=name;$("current-model").textContent=name;$("model-settings-status").textContent="Modelo salvo e ativado.";await refreshModels()}catch(e){showModal("Não foi possível trocar o modelo",e.message,"")}})}
  function renderProjects(){const grid=$("project-grid");if(!grid)return;grid.replaceChildren();const q=($("project-search").value||"").toLowerCase();projects.filter(p=>p.name.toLowerCase().includes(q)).forEach(p=>{const card=document.createElement("article");card.className="project-card";card.innerHTML='<div class="project-icon">' + iconSvg("folder") + '</div><strong></strong><p></p><small></small>';card.querySelector("strong").textContent=p.name;card.querySelector("p").textContent=p.description||"Projeto local MYRA";card.querySelector("small").textContent="ATUALIZADO "+new Date(p.updatedAt).toLocaleDateString("pt-BR");card.addEventListener("click",()=>{showView("code")});grid.append(card)});if(!grid.children.length){const empty=document.createElement("div");empty.className="model-empty";empty.textContent="Nenhum projeto salvo ainda. Crie um projeto para começar.";grid.append(empty)}}
  function newProject(){const name=prompt("Nome do projeto:");if(!name||!name.trim())return;projects.unshift({id:"project-"+Date.now(),name:name.trim(),description:"Projeto criado no workspace MYRA",updatedAt:Date.now()});save(PROJECT_KEY,projects);renderProjects()}
  function renderFiles(){const list=$("file-list");list.replaceChildren();Object.keys(codeFiles).forEach(name=>{const b=document.createElement("button");b.className="file-entry"+(name===activeFile?" active":"");const ext=name.split(".").pop().toLowerCase();const image=codeFiles[name]?.lang==="IMAGE";b.innerHTML="<span>"+(image?"▧":ext==="html"?"◇":ext==="css"?"#":"JS")+"</span>"+escapeText(name);b.addEventListener("click",()=>{storeActiveCode();activeFile=name;loadActiveCode();renderFiles()});list.append(b)})}
  function storeActiveCode(){if(codeFiles[activeFile]&&codeFiles[activeFile].lang!=="IMAGE")codeFiles[activeFile].content=$("code-editor").value;save(CODE_KEY,codeFiles)}
  function loadActiveCode(){const file=codeFiles[activeFile];$("editor-filename").textContent=activeFile;$("editor-lang").textContent=file?.lang||"TEXT";$("code-editor").value=file?.lang==="IMAGE"?"Imagem importada. Ela será disponibilizada no preview quando o HTML usar o nome "+activeFile+".":(file?.content||"");$("code-editor").readOnly=file?.lang==="IMAGE";$("editor-status").textContent=file?.lang==="IMAGE"?"Asset visual":"Pronto"}
  function buildPreview(){storeActiveCode();let html=codeFiles["index.html"]?.content||"<main><h1>MYRA Preview</h1></main>";const css=Object.entries(codeFiles).filter(([name,file])=>name.toLowerCase().endsWith(".css")&&file.lang!=="IMAGE").map(([,file])=>file.content).join("\n"),jsCode=Object.entries(codeFiles).filter(([name,file])=>name.toLowerCase().endsWith(".js")&&file.lang!=="IMAGE").map(([,file])=>file.content).join("\n");const parser=new DOMParser(),doc=parser.parseFromString(html,"text/html");Object.entries(codeFiles).forEach(([name,file])=>{if(file.lang==="IMAGE"){doc.querySelectorAll("img").forEach(img=>{const src=img.getAttribute("src")||"";if(src===name||src.endsWith("/"+name))img.src=file.content})}});html="<!doctype html>"+doc.documentElement.outerHTML;const style="<style>"+css.replace(/<\/style/gi,"<\\/style")+"</style>";const script="<script>"+jsCode.replace(/<\/script/gi,"<\\/script")+"<"+"/script>";if(/<\/head>/i.test(html))html=html.replace(/<\/head>/i,style+"</head>");else html=style+html;if(jsCode){if(/<\/body>/i.test(html))html=html.replace(/<\/body>/i,script+"</body>");else html+=script}return html}
  function renderPreview(){const src=buildPreview();const a=$("preview-frame"),b=$("full-preview-frame");if(a)a.srcdoc=src;if(b)b.srcdoc=src}
  function addCodeFile(){const name=prompt("Nome do arquivo (ex.: app.js):");if(!name||!name.trim())return;const clean=name.trim().replace(/[^\w.-]/g,"-");if(codeFiles[clean])return;const ext=clean.split(".").pop().toLowerCase(),lang=ext==="html"?"HTML":ext==="css"?"CSS":ext==="js"?"JS":"TEXT";codeFiles[clean]={lang,content:""};storeActiveCode();activeFile=clean;renderFiles();loadActiveCode()}
  async function downloadCode(){storeActiveCode();const file=codeFiles[activeFile],content=file?.content||"",blob=file?.lang==="IMAGE"?await (await fetch(content)).blob():new Blob([content],{type:"text/plain;charset=utf-8"}),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=activeFile;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  function importCode(file){if(!file)return;const name=file.name,ext=name.split(".").pop().toLowerCase(),isImage=["png","jpg","jpeg","webp","gif","svg"].includes(ext);if(isImage&&(file.size>3*1024*1024||Object.values(codeFiles).filter(f=>f.lang==="IMAGE").reduce((sum,f)=>sum+Math.floor((f.content||"").length*0.75),0)+file.size>3.5*1024*1024)){showModal("Limite de imagens","O limite total de imagens no Code Studio é 3,5 MB para preservar o armazenamento local.","");return}const reader=new FileReader();reader.onload=()=>{codeFiles[name]={lang:isImage?"IMAGE":ext==="html"?"HTML":ext==="css"?"CSS":ext==="js"?"JS":"TEXT",content:String(reader.result||"")};activeFile=name;save(CODE_KEY,codeFiles);renderFiles();loadActiveCode();renderPreview()};if(isImage)reader.readAsDataURL(file);else reader.readAsText(file)}
  function showModal(title,description,kind){
    $("modal-title").textContent=title;$("modal-description").textContent=description;$("modal-body").replaceChildren();
    const box=document.createElement("div");
    if(kind==="github"){
      box.innerHTML='<div class="modal-field"><label>Repositorio conectado</label><input id="modal-github-repo" readonly></div><div class="modal-field"><label>Autenticacao</label><input id="modal-github-auth" readonly></div><p class="notice">Fetch, pull e push sao operacoes reais. Pull e bloqueado quando ha alteracoes locais pendentes. Push envia apenas commits ja criados; nenhum commit automatico e feito.</p>';
      box.querySelector("#modal-github-repo").value=$("github-repo-name")?.textContent||"Repositorio nao identificado";
      const authState=$("github-state")?.textContent||"NAO VERIFICADO";
      box.querySelector("#modal-github-auth").value=authState==="CONECTADO"?"GitHub CLI autenticado nesta maquina":"GitHub CLI sem autenticacao confirmada: "+authState;
      $("modal-confirm").textContent="Abrir repositorio";
      $("modal-confirm").onclick=async()=>{try{await window.__TAURI__.core.invoke("open_external_url",{url:"https://github.com/BielDominic/myra-agent"});closeModal()}catch(e){alert("Não foi possível abrir o GitHub: "+e)}};
    }else if(kind==="api"){
      const field=(labelText,placeholder,type="text")=>{const wrap=document.createElement("label");wrap.className="modal-field";const label=document.createElement("span");label.textContent=labelText;const input=document.createElement("input");input.type=type;input.placeholder=placeholder;wrap.append(label,input);box.append(wrap);return input};
      const name=field("Nome da integração","Ex.: API de clima");
      const url=field("URL HTTPS pública","https://api.example.com/health","url");
      const token=field("Bearer token (opcional, usado apenas no teste)","Token temporário","password");
      const result=document.createElement("p");result.className="notice";result.textContent="A MYRA testa uma chamada GET real. O token não é salvo; apenas o nome e a URL ficam armazenados localmente. Por segurança, apenas hosts HTTPS públicos são aceitos.";box.append(result);
      const saved=document.createElement("div");saved.className="github-changes";saved.textContent="Carregando integrações salvas...";box.append(saved);
      fetch(API+"/integrations/apis",{cache:"no-store"}).then(r=>r.json()).then(d=>{saved.textContent=(d.integrations||[]).map(x=>x.name+" — "+x.url).join(String.fromCharCode(10))||"Nenhuma API cadastrada ainda."}).catch(()=>{saved.textContent="Não foi possível listar APIs salvas."});
      const test=document.createElement("button");test.type="button";test.className="soft-button";test.textContent="Testar conexão";test.addEventListener("click",async()=>{if(!url.value.trim()){result.textContent="Informe a URL HTTPS.";return}test.disabled=true;result.textContent="Testando endpoint...";try{const r=await fetch(API+"/integrations/apis/test",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({url:url.value.trim(),bearer_token:token.value})});const d=await r.json();result.textContent=d.ok?"Conexão confirmada — HTTP "+d.status+" — "+(d.content_type||"resposta recebida"):"Falha no teste — "+(d.status||"sem status")+" — "+(d.error||d.preview||"verifique a URL e a autenticação");}catch(e){result.textContent="Não foi possível testar: "+e.message}finally{test.disabled=false}});box.append(test);
      $("modal-confirm").textContent="Salvar API";$("modal-confirm").onclick=async()=>{if(!name.value.trim()||!url.value.trim()){result.textContent="Preencha o nome e a URL.";return}try{const r=await fetch(API+"/integrations/apis",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name.value.trim(),url:url.value.trim()})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Falha ao salvar");result.textContent="API salva neste dispositivo. Teste a conexão antes de utilizá-la.";saved.textContent=(d.integrations||[]).map(x=>x.name+" — "+x.url).join(String.fromCharCode(10));token.value="";refreshApiIntegrations();}catch(e){result.textContent=e.message}};
    }else if(kind==="delete-history"){
      box.textContent="A exclusão remove somente as conversas selecionadas deste dispositivo. A biblioteca de plugins, os plugins instalados e seus arquivos permanecem intactos.";
      $("modal-confirm").textContent="Confirmar exclusão";$("modal-confirm").onclick=closeModal;
    }else{
      box.textContent="Este recurso ainda não possui uma ação configurada.";
      $("modal-confirm").textContent="Fechar";$("modal-confirm").onclick=closeModal;
    }
    $("modal-body").append(box);$("modal-backdrop").hidden=false;
  }
  function closeModal(){$("modal-backdrop").hidden=true}
  async function refreshApiIntegrations(){const state=$("api-state");if(!state)return;try{const r=await fetch(API+"/integrations/apis",{cache:"no-store"});if(!r.ok)throw new Error("API indisponível");const d=await r.json();const n=(d.integrations||[]).length;state.textContent=n?(n+" cadastrada(s)"):"Nenhuma cadastrada";}catch(_){state.textContent="Offline"}}
  async function refreshGitHub(){
    const state=$("github-state");if(!state)return;
    state.textContent="VERIFICANDO";state.className="live-label";
    try{
      const r=await fetch(API+"/workspace/status",{cache:"no-store",signal:AbortSignal.timeout(5000)});
      if(!r.ok)throw new Error("Backend nao respondeu ao status do workspace");
      const d=await r.json(),repo=d.repository||{},url=repo.url||"https://github.com/BielDominic/myra-agent";
      $("github-repo-name").textContent=repo.nameWithOwner||"BielDominic/myra-agent";
      $("github-open").href=url;
      $("github-repo-meta").textContent=(d.github_authenticated?"GitHub autenticado":"GitHub CLI sem autenticacao")+" | branch "+(d.branch||"desconhecida")+" | "+(d.dirty?"alteracoes locais pendentes":"arvore limpa");
      state.textContent=d.github_authenticated?"CONECTADO":"SEM AUTENTICA\u00c7\u00c3O";state.className=d.github_authenticated?"live-label":"coming-state";
      $("github-changes").textContent=(d.changes||[]).length?(d.changes||[]).slice(0,15).join(String.fromCharCode(10)):"Nenhuma altera\u00e7\u00e3o local detectada.";
      $("github-fetch").disabled=!d.github_authenticated;
      $("github-pull").disabled=!d.github_authenticated||Boolean(d.dirty);
      $("github-push").disabled=!d.github_authenticated||Boolean(d.dirty);
    }catch(e){state.textContent="OFFLINE";$("github-repo-meta").textContent=e.message;$("github-changes").textContent="N\u00e3o foi poss\u00edvel consultar o backend."}
  }
  async function githubSync(action){
    const labels={fetch:"Buscar atualizacoes do remoto?",pull:"Atualizar o c?digo local? O pull s? ser? permitido com a arvore limpa.",push:"Enviar os commits locais ao repositorio GitHub?"};
    if(!confirm(labels[action]))return;
    try{
      const r=await fetch(API+"/github/sync",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action})});
      const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha na operacao Git");
      alert((action.toUpperCase()+" concluido.\n")+(d.output||""));
      await refreshGitHub();
    }catch(e){alert("GitHub: "+e.message);await refreshGitHub()}
  }
  async function exportWorkspace(){
    try{
      const response=await fetch(API+"/workspace/export",{cache:"no-store"});
      if(!response.ok)throw new Error("O backend n\u00e3o conseguiu gerar o pacote.");
      const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
      a.href=url;a.download="myra-agent-workspace.zip";document.body.append(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),2000);
    }catch(error){alert("N\u00e3o foi poss\u00edvel baixar o projeto: "+error.message)}
  }
  let settingsDraft = {};
  function markSettingsPending(kind){
    const status=$(kind==="general"?"general-settings-status":"appearance-settings-status");
    if(status)status.textContent="Alterações pendentes. Clique em Salvar para gravar.";
  }
  function saveSettingsDraft(kind){
    settingsDraft={...settingsDraft,theme:$("theme-setting").value,density:$("density-setting").value,animations:$("animations-setting").checked};
    save(PREF_KEY,settingsDraft);
    const status=$(kind==="general"?"general-settings-status":"appearance-settings-status");
    if(status)status.textContent="Preferências salvas neste dispositivo.";
    syncTopThemeToggle();
  }
  function initSettings(){
    const prefs=load(PREF_KEY,{});
    settingsDraft={theme:prefs.theme||"dark",density:prefs.density||"comfortable",accent:prefs.accent||"purple",animations:prefs.animations!==false};
    $("theme-setting").value=settingsDraft.theme;
    $("density-setting").value=settingsDraft.density;
    $("animations-setting").checked=settingsDraft.animations;
    document.body.dataset.theme=settingsDraft.theme;
    document.body.dataset.density=settingsDraft.density;
    document.body.classList.toggle("no-motion",!settingsDraft.animations);
    applyAccent(settingsDraft.accent);
    $("theme-setting").addEventListener("change",e=>{settingsDraft.theme=e.target.value;document.body.dataset.theme=e.target.value;syncTopThemeToggle();markSettingsPending("appearance")});
    $("density-setting").addEventListener("change",e=>{settingsDraft.density=e.target.value;document.body.dataset.density=e.target.value;markSettingsPending("appearance")});
    document.querySelectorAll("[data-accent]").forEach(b=>b.addEventListener("click",()=>{settingsDraft.accent=b.dataset.accent;applyAccent(b.dataset.accent);markSettingsPending("appearance")}));
    $("animations-setting").addEventListener("change",e=>{settingsDraft.animations=e.target.checked;document.body.classList.toggle("no-motion",!e.target.checked);markSettingsPending("general")});
    $("general-settings-save").addEventListener("click",()=>saveSettingsDraft("general"));
    $("appearance-settings-save").addEventListener("click",()=>saveSettingsDraft("appearance"));
    document.querySelectorAll("[data-settings-tab]").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll("[data-settings-tab]").forEach(x=>x.classList.toggle("selected",x===b));document.querySelectorAll("[data-settings-panel]").forEach(p=>p.classList.toggle("active",p.dataset.settingsPanel===b.dataset.settingsTab))}));
  }
  function syncTopThemeToggle(){const t=$("top-theme-toggle");if(t)t.checked=document.body.dataset.theme!=="light";}
  function applyTopTheme(){const theme=$("top-theme-toggle")?.checked?"dark":"light";document.body.dataset.theme=theme;settingsDraft.theme=theme;const setting=$("theme-setting");if(setting)setting.value=theme;markSettingsPending("appearance");}
  const WIDGET_CONFIG_KEY="myra-widget-config-v1";
  const WIDGET_DEFAULTS={opacity:100,width:360,height:280};
  function widgetConfig(){return {...WIDGET_DEFAULTS,...load(WIDGET_CONFIG_KEY,{})};}
  function widgetDraft(){return {opacity:Number($("widget-opacity").value),width:Number($("widget-width").value),height:Number($("widget-height").value)};}
  function updateWidgetLabels(c){$("widget-opacity-value").textContent=c.opacity+"%";$("widget-width-value").textContent=c.width+" px";$("widget-height-value").textContent=c.height+" px";}
  function renderWidgetConfig(c=widgetConfig()){
    $("widget-opacity").value=c.opacity??100;$("widget-width").value=c.width??360;$("widget-height").value=c.height??280;updateWidgetLabels(c);
  }
  const widgetSyncChannel=typeof BroadcastChannel!=="undefined"?new BroadcastChannel("myra-widget-sync"):null;
  function publishWidgetConfig(c){try{widgetSyncChannel?.postMessage({type:"config",config:c})}catch(e){console.warn("[WIDGET SYNC]",e)}}
  function applyWidgetConfig(){
    const c={...widgetDraft(),updatedAt:Date.now()};save(WIDGET_CONFIG_KEY,c);publishWidgetConfig(c);
    $("widget-save-status").textContent="Configurações salvas e enviadas ao widget real.";
    $("widget-save-status").dataset.state="saved";
  }
  function initWidgetSettings(){
    ["widget-opacity","widget-width","widget-height"].forEach(id=>$(id)?.addEventListener("input",()=>{updateWidgetLabels(widgetDraft());$("widget-save-status").textContent="Alterações pendentes. Salve para atualizar o widget.";$("widget-save-status").dataset.state="pending";}));
    $("widget-settings-save")?.addEventListener("click",()=>withButtonLoader($("widget-settings-save"),async()=>applyWidgetConfig()));
    $("widget-reset")?.addEventListener("click",()=>{renderWidgetConfig(WIDGET_DEFAULTS);$("widget-save-status").textContent="Padrões restaurados no formulário. Salve para aplicar.";$("widget-save-status").dataset.state="pending";});
    renderWidgetConfig();
  }
  function applyAccent(accent){const root=document.documentElement;if(accent==="blue"){root.style.setProperty("--purple","#3b82f6");root.style.setProperty("--cyan","#22d3ee")}else if(accent==="green"){root.style.setProperty("--purple","#10b981");root.style.setProperty("--cyan","#67e8f9")}else{root.style.setProperty("--purple","#8b5cf6");root.style.setProperty("--cyan","#06b6d4")}document.querySelectorAll("[data-accent]").forEach(b=>b.classList.toggle("selected",b.dataset.accent===accent))}
  $("activity-pause").addEventListener("click",()=>runActivityAction("pause"));
  $("activity-resume").addEventListener("click",()=>runActivityAction("resume"));
  $("activity-takeover").addEventListener("click",()=>runActivityAction("takeover"));
  $("activity-cancel").addEventListener("click",()=>runActivityAction("cancel"));
  $("prompt-tools-toggle").addEventListener("click",()=>{const panel=$("composer-tools"),open=panel.hidden;panel.hidden=!open;$("prompt-tools-toggle").setAttribute("aria-expanded",String(open));$("prompt-tools-toggle").classList.toggle("active",open)});
  const metalBar=$("metal-prompt-bar");
  const fileDragTargets=[metalBar,$("composer-wrap")].filter(Boolean);
  const hasDraggedFiles=e=>Array.from(e.dataTransfer?.types||[]).includes("Files")||!!e.dataTransfer?.files?.length;
  window.addEventListener("dragenter",e=>{if(hasDraggedFiles(e)){e.preventDefault();metalBar.classList.add("is-file-drop")}},true);
  window.addEventListener("dragover",e=>{if(hasDraggedFiles(e)){e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect="copy";metalBar.classList.add("is-file-drop")}},true);
  window.addEventListener("dragleave",e=>{if(!e.relatedTarget||!document.documentElement.contains(e.relatedTarget))metalBar.classList.remove("is-file-drop")},true);
  window.addEventListener("drop",e=>{if(!hasDraggedFiles(e))return;const target=e.target;if(!target?.closest?.("#metal-prompt-bar,.composer-wrap"))return;e.preventDefault();e.stopPropagation();metalBar.classList.remove("is-file-drop");const files=Array.from(e.dataTransfer?.files||[]);if(files.length)attachDocuments(files)},true);
  metalBar.addEventListener("pointermove",e=>{
    const r=metalBar.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top;
    metalBar.style.setProperty("--metal-angle",Math.round(Math.atan2(y-r.height/2,x-r.width/2)*180/Math.PI+180)+"deg");
    metalBar.querySelectorAll(".metal-chip").forEach(chip=>{const c=chip.getBoundingClientRect();chip.style.setProperty("--chip-x",Math.max(0,Math.min(100,(e.clientX-c.left)/c.width*100))+"%");chip.style.setProperty("--chip-y",Math.max(0,Math.min(100,(e.clientY-c.top)/c.height*100))+"%")});
  });

  $("sidebar-collapse-toggle")?.addEventListener("click",()=>{const collapsed=!$("sidebar").classList.contains("sidebar-collapsed");$("sidebar").classList.toggle("sidebar-collapsed",collapsed);localStorage.setItem("myra-sidebar-collapsed-v1",String(collapsed));const button=$("sidebar-collapse-toggle");button?.setAttribute("aria-label",collapsed?"Expandir barra lateral":"Recolher barra lateral");button.title=collapsed?"Expandir barra lateral":"Recolher barra lateral"});
  $("top-wake-toggle")?.addEventListener("click",startWakeWord);
  $("widget-visibility-toggle").addEventListener("click",toggleWidgetVisibility);$("top-theme-toggle").addEventListener("change",applyTopTheme);syncNativeWidgetVisibility().then(syncTopThemeToggle);
  $("new-chat").addEventListener("click",()=>{createConversation();showView("chat");$("message-input").focus()});$("send-button").addEventListener("click",()=>sendMessage($("message-input").value));$("message-input").addEventListener("input",resizeInput);$("message-input").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage($("message-input").value)}});
  $("mode-toggle").addEventListener("click",()=>{executionMode=!executionMode;const b=$("mode-toggle");b.classList.toggle("is-execution",executionMode);b.setAttribute("aria-pressed",String(executionMode));b.innerHTML=executionMode?"<span>⚡</span> Tarefa":"<span>◈</span> Auto";$("message-input").placeholder=executionMode?"Descreva o que a MYRA deve executar...":"O que vamos construir hoje?"});
  document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));document.addEventListener("click",async e=>{const a=e.target.closest("a[href]");if(!a)return;const href=a.href;if(!(href.startsWith("http://")||href.startsWith("https://")))return;e.preventDefault();try{if(window.__TAURI__?.core?.invoke)await window.__TAURI__.core.invoke("open_external_url",{url:href});else window.open(href,"_blank","noopener,noreferrer")}catch(err){console.error("[EXTERNAL LINK]",err);alert("Não foi possível abrir o link: "+err)}});document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>sendMessage(b.dataset.prompt)));$("settings-button").addEventListener("click",()=>showView("settings"));updateWidgetVisibilityButton();applyWidgetVisibility(widgetVisible).catch(()=>{});
  $("history-search").addEventListener("input",e=>{historyFilter=e.target.value.trim().toLocaleLowerCase();renderSidebar()});
  $("select-history").addEventListener("click",()=>{historySelectionMode=!historySelectionMode;if(!historySelectionMode)selectedConversationIds.clear();renderSidebar()});
  $("clear-history").addEventListener("click",()=>{historySelectionMode=true;renderSidebar()});
  $("select-all-history").addEventListener("change",e=>{if(e.target.checked)conversations.forEach(c=>selectedConversationIds.add(c.id));else selectedConversationIds.clear();renderSidebar()});
  $("delete-selected-history").addEventListener("click",()=>deleteConversations([...selectedConversationIds]));
  $("voice-input").addEventListener("click",startVoiceInput);$("voice-stop").addEventListener("click",stopMyraSpeech);$("voice-live-toggle").addEventListener("click",toggleLiveVoice);$("voice-wake-toggle")?.addEventListener("click",startWakeWord);window.addEventListener("beforeunload",()=>{if(wakeStream)wakeStream.getTracks().forEach(t=>t.stop())});$("voice-save")?.addEventListener("click",()=>withButtonLoader($("voice-save"),saveVoiceSettings));$("runtime-refresh")?.addEventListener("click",refreshRuntime);$("runtime-save")?.addEventListener("click",()=>withButtonLoader($("runtime-save"),saveRuntimeConfig));document.querySelectorAll("[data-runtime-service]").forEach(b=>b.addEventListener("click",()=>runtimeAction(b.dataset.runtimeService,b.dataset.runtimeAction)));
  $("chat-agent").addEventListener("change",()=>{const c=activeConversation();if(c){c.agentId=$("chat-agent").value;save(STORAGE_KEY,conversations.slice(0,60))}});
  const routineRunChannel=typeof BroadcastChannel!=="undefined"?new BroadcastChannel("myra-routine-run"):null;
  routineRunChannel?.addEventListener("message",event=>{
    const objective=String(event.data?.objective||"").trim();
    if(event.data?.type!=="run-routine"||!objective)return;
    showView("chat");
    $("message-input").value=objective;
    sendMessage(objective);
  });
  $("attach-files").addEventListener("click",()=>$("chat-files").click());$("attach-files-main")?.addEventListener("click",()=>$("chat-files").click());$("chat-files").addEventListener("change",e=>{attachDocuments([...e.target.files]);e.target.value=""});
  $("attach-image").addEventListener("click",()=>$("chat-image-files").click());
  $("chat-image-files").addEventListener("change",e=>{attachImages([...e.target.files]);e.target.value=""});
  $("edit-image").addEventListener("click",editImage);
  $("generate-image").addEventListener("click",generateImage);$("voice-read").addEventListener("click",readLastAnswer);$("improve-prompt").addEventListener("click",improvePrompt);
  document.querySelectorAll(".skill-chip").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.skill;if(activeSkills.has(key)){activeSkills.delete(key);button.classList.remove("active")}else{activeSkills.add(key);button.classList.add("active")}}));
  const pluginCreateToggle=$("plugin-create-toggle"),pluginEditor=$("plugin-editor"),pluginDraftType=$("plugin-draft-type"),pluginDraftHint=$("plugin-editor-hint");const loadPluginDraft=()=>{try{const d=JSON.parse(localStorage.getItem("myra-plugin-draft-v1")||"{}");$("plugin-draft-name").value=d.name||"";$("plugin-draft-description").value=d.description||"";pluginDraftType.value=d.type||"tool";$("plugin-draft-code").value=d.code||""}catch{}};pluginCreateToggle?.addEventListener("click",()=>{pluginEditor.hidden=!pluginEditor.hidden;pluginCreateToggle.textContent=pluginEditor.hidden?"+ Criar meu plugin":"− Fechar editor";if(!pluginEditor.hidden)loadPluginDraft()});$("plugin-draft-cancel")?.addEventListener("click",()=>{pluginEditor.hidden=true;pluginCreateToggle.textContent="+ Criar meu plugin"});pluginDraftType?.addEventListener("change",()=>{pluginDraftHint.textContent=pluginDraftType.value==="tool"?"Ferramentas Python são executadas em contêiner Docker sem rede, com sistema de arquivos somente leitura e limites de recursos. Use def run(args): e retorne dados JSON.":"Skills e Prompts são instruções locais; ferramentas de código usam o tipo Ferramenta Python."});$("plugin-draft-save")?.addEventListener("click",async()=>{const name=$("plugin-draft-name").value.trim(),description=$("plugin-draft-description").value.trim(),type=pluginDraftType.value,code=$("plugin-draft-code").value,status=$("plugin-draft-status"),save=$("plugin-draft-save");if(!name||!code.trim()){status.textContent="Informe um nome e escreva o conteúdo antes de salvar.";return}if(type!=="tool"){localStorage.setItem("myra-plugin-draft-v1",JSON.stringify({name,description,type,code,updatedAt:new Date().toISOString()}));status.textContent="Rascunho local salvo. Para Skills e Prompts, use um pacote ZIP MYRA validado para instalar.";return}if(!description){status.textContent="Informe também uma descrição da ferramenta.";return}const toolName=name.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"").slice(0,48);save.disabled=true;status.textContent="Validando e instalando o plugin...";try{const response=await fetch(API+"/plugins/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,description,tool_name:toolName,code}),signal:AbortSignal.timeout(30000)});const result=await response.json().catch(()=>({}));if(!response.ok)throw new Error(result.detail||"Falha ao criar o plugin.");const enabled=await fetch(API+"/plugins/"+encodeURIComponent(result.id)+"/enable",{method:"POST",signal:AbortSignal.timeout(15000)});const state=await enabled.json().catch(()=>({}));if(!enabled.ok)throw new Error(state.detail||"Plugin instalado, mas não foi possível ativá-lo.");status.textContent="Plugin instalado e ativado. Ferramenta "+toolName+" registrada no planejador; execução isolada pelo Docker.";localStorage.removeItem("myra-plugin-draft-v1");$("plugin-installed-list").dataset.loaded="false";await refreshInstalledPlugins();await renderPlugins()}catch(error){status.textContent=error.message}finally{save.disabled=false}});$("plugin-search").addEventListener("input",renderPlugins);$("plugin-category").addEventListener("change",renderPlugins);$("plugin-package-select").addEventListener("click",()=>$("plugin-package").click());$("plugin-package").addEventListener("change",e=>importPluginPackage(e.target.files?.[0]));$("plugin-refresh").addEventListener("click",()=>{$("plugin-installed-list").dataset.loaded="false";refreshInstalledPlugins()});
  $("github-refresh").addEventListener("click",refreshGitHub);$("github-fetch").addEventListener("click",()=>githubSync("fetch"));$("github-pull").addEventListener("click",()=>githubSync("pull"));$("github-push").addEventListener("click",()=>githubSync("push"));$("github-export").addEventListener("click",exportWorkspace);
  $("new-project").addEventListener("click",newProject);$("project-search").addEventListener("input",renderProjects);$("code-editor").addEventListener("input",()=>{storeActiveCode();$("editor-status").textContent="Alterações locais";clearTimeout(previewTimer);previewTimer=setTimeout(renderPreview,220)});$("run-preview").addEventListener("click",()=>{renderPreview();$("editor-status").textContent="Preview atualizado"});$("refresh-preview").addEventListener("click",renderPreview);$("expand-preview").addEventListener("click",()=>showView("preview"));$("preview-to-code").addEventListener("click",()=>showView("code"));$("add-file").addEventListener("click",addCodeFile);$("download-code").addEventListener("click",downloadCode);$("import-code").addEventListener("click",()=>$("code-file").click());$("code-file").addEventListener("change",e=>{Array.from(e.target.files||[]).forEach(importCode);e.target.value=""});$("workbench").addEventListener("dragover",e=>{e.preventDefault();$("workbench").classList.add("is-dragging")});$("workbench").addEventListener("dragleave",e=>{if(!e.relatedTarget||!$("workbench").contains(e.relatedTarget))$("workbench").classList.remove("is-dragging")});$("workbench").addEventListener("drop",e=>{e.preventDefault();$("workbench").classList.remove("is-dragging");Array.from(e.dataTransfer?.files||[]).forEach(importCode)});$("refresh-models").addEventListener("click",refreshModels);$("quick-model").addEventListener("change",e=>stageModelSelection(e.target.value));$("settings-model").addEventListener("change",e=>stageModelSelection(e.target.value));$("model-settings-save").addEventListener("click",()=>selectModel($("settings-model").value));$("top-model-save").addEventListener("click",()=>selectModel($("quick-model").value));
  document.querySelectorAll("[data-integration]").forEach(b=>b.addEventListener("click",()=>{const k=b.dataset.integration;showModal(k==="github"?"GitHub":k==="api"?"Adicionar API":"Arquitetura de plugins",k==="github"?"O repositório privado conectado usa a autenticação GitHub CLI desta máquina. Fetch, pull e push são executados pelo Git local.":k==="api"?"Cadastre um endpoint HTTPS público e teste uma chamada GET real. Tokens são temporários e não ficam armazenados.":"Expansão modular da MYRA.",k)}));
  $("modal-close").addEventListener("click",closeModal);$("modal-cancel").addEventListener("click",closeModal);$("modal-backdrop").addEventListener("click",e=>{if(e.target===$("modal-backdrop"))closeModal()});
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();createConversation();showView("chat");$("message-input").focus()}if(e.key==="Escape"&&!busy){closeModal();showView("chat")}});
  function githubProjectPath(){return String($("github-project-path")?.value||localStorage.getItem(GITHUB_PROJECT_PATH_KEY)||"").trim()}
  async function refreshGitHub(){
    const state=$("github-state");if(!state)return;const path=githubProjectPath();
    if(!path){state.textContent="AGUARDANDO PROJETO";state.className="coming-state";$("github-repo-name").textContent="Nenhum projeto selecionado";$("github-repo-meta").textContent="Informe a pasta local de um dos seus projetos Git."; $("github-changes").textContent="A integração não acessará o repositório da MYRA.";["github-fetch","github-pull","github-push","github-export"].forEach(k=>$(k).disabled=true);$("github-open").href="#";return}
    state.textContent="VERIFICANDO";state.className="live-label";
    try{const r=await fetch(API+"/workspace/status?repo_path="+encodeURIComponent(path),{cache:"no-store",signal:AbortSignal.timeout(8000)});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Não foi possível abrir o projeto informado.");const repo=d.repository||{},url=repo.url||d.remote||"";$("github-repo-name").textContent=repo.nameWithOwner||url||d.root;$("github-open").href=url.startsWith("http")?url:"#";$("github-repo-meta").textContent=(d.github_authenticated?"GitHub autenticado":"GitHub CLI sem autenticação")+" | "+d.root+" | branch "+(d.branch||"desconhecida")+" | "+(d.dirty?"alterações locais pendentes":"árvore limpa");state.textContent=d.github_authenticated?"CONECTADO":"REPOSITÓRIO LOCAL";state.className=d.github_authenticated?"live-label":"coming-state";$("github-changes").textContent=(d.changes||[]).slice(0,15).join("\n")||"Nenhuma alteração local detectada.";$("github-fetch").disabled=!d.github_authenticated;$("github-pull").disabled=!d.github_authenticated||Boolean(d.dirty);$("github-push").disabled=!d.github_authenticated;$("github-export").disabled=false}
    catch(e){state.textContent="ERRO";state.className="coming-state";$("github-repo-name").textContent="Projeto não identificado";$("github-repo-meta").textContent=e.message;$("github-changes").textContent="Verifique o caminho e se a pasta contém um repositório Git.";["github-fetch","github-pull","github-push","github-export"].forEach(k=>$(k).disabled=true);$("github-open").href="#"}
  }
  async function githubSync(action){const path=githubProjectPath();if(!path){alert("Informe primeiro a pasta do seu projeto Git.");return}const labels={fetch:"Buscar atualizações do remoto deste projeto?",pull:"Atualizar o código deste projeto? Pull só será permitido com a árvore limpa.",push:"Enviar os commits deste projeto ao GitHub?"};if(!confirm(labels[action]))return;try{const r=await fetch(API+"/github/sync",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action,repo_path:path})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Falha na operação Git");alert(action.toUpperCase()+" concluído em "+d.root+".\n"+(d.output||""));await refreshGitHub()}catch(e){alert("GitHub: "+e.message);await refreshGitHub()}}
  async function exportWorkspace(){const path=githubProjectPath();if(!path){alert("Informe primeiro a pasta do seu projeto.");return}try{const r=await fetch(API+"/workspace/export?repo_path="+encodeURIComponent(path),{cache:"no-store"});if(!r.ok){const d=await r.json().catch(()=>({}));throw new Error(d.detail||"Falha ao exportar")}const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="meu-projeto-workspace.zip";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000)}catch(e){alert("Não foi possível baixar o projeto: "+e.message)}}
  const githubPathInput=$("github-project-path");if(githubPathInput){githubPathInput.value=localStorage.getItem(GITHUB_PROJECT_PATH_KEY)||"";githubPathInput.addEventListener("change",()=>{localStorage.setItem(GITHUB_PROJECT_PATH_KEY,githubPathInput.value.trim());refreshGitHub()});}
  renderPlatformIcons();initAvatarSettings();initSetup();refreshVoiceStatus();setChatActivity(false);setBusy(false);if(!conversations.length)createConversation(false);renderSidebar();renderMessages();renderFiles();loadActiveCode();initSettings();renderProjects();checkBackend();refreshTaskStatus();refreshModels();renderPreview();refreshGitHub();refreshApiIntegrations();renderQueue();initWidgetSettings();initCognitiveConsole();renderPlugins();// First-run setup is optional: never hide chat or image tools behind it. The user can open Setup from the sidebar at any time.
  setInterval(checkBackend,10000);setInterval(refreshTaskStatus,750);if(messageQueue.length){queueNeedsResume=true;renderQueue();}
})();
  function initAvatarSettings(){
    const key="myra-avatar-settings-v1",defaults={avatar:"eye",style:"animated",color:"#7C6AF6",eyeColor:"#09090B",c1:"#7C6AF6",c2:"#7DD3C7",c3:"#E8B4D4"};
    const ids={avatar:"desktop-avatar-model",style:"desktop-avatar-style",color:"desktop-avatar-color",eyeColor:"desktop-avatar-eye-color",c1:"desktop-avatar-c1",c2:"desktop-avatar-c2",c3:"desktop-avatar-c3"};
    const controls=Object.fromEntries(Object.entries(ids).map(([k,id])=>[k,document.getElementById(id)]));
    const read=()=>{try{const cfg={...defaults,...JSON.parse(localStorage.getItem(key)||"{}")};if(cfg.avatar==="orb")cfg.avatar="eye";return cfg}catch(_){return {...defaults}}};
    const current=()=>Object.fromEntries(Object.keys(defaults).map(k=>[k,controls[k]?.value||defaults[k]]));
    const apply=cfg=>{Object.entries(controls).forEach(([k,el])=>{if(el)el.value=cfg[k]||defaults[k]});window.MyraUI?.applyAvatarConfig?.(cfg)};
    const persist=()=>{const cfg=current();localStorage.setItem(key,JSON.stringify(cfg));apply(cfg);try{const ch=new BroadcastChannel("myra-avatar-sync");ch.postMessage({type:"avatar-config",config:cfg});ch.close()}catch(_){};const status=document.getElementById("desktop-avatar-status");if(status)status.textContent="Avatar salvo e sincronizado com o widget."};
    apply(read());
    Object.values(controls).forEach(el=>{el?.addEventListener("input",()=>{apply(current());const status=document.getElementById("desktop-avatar-status");if(status)status.textContent="Alterações pendentes. Clique em Salvar avatar."});el?.addEventListener("change",()=>{apply(current());const status=document.getElementById("desktop-avatar-status");if(status)status.textContent="Alterações pendentes. Clique em Salvar avatar."})});
    document.getElementById("desktop-avatar-save")?.addEventListener("click",persist);
    document.getElementById("desktop-avatar-reset")?.addEventListener("click",()=>{apply({...defaults});const status=document.getElementById("desktop-avatar-status");if(status)status.textContent="Padrões no formulário. Clique em Salvar avatar para aplicar."});
    window.addEventListener("storage",e=>{if(e.key===key)apply(read())});
  }

  const API="http://127.0.0.1:8000";
  const $=id=>document.getElementById(id);
  async function refreshCognitiveConsole(){
    const status=$("cognitive-memory-status");
    try{
      const [s,t,q]=await Promise.all([
        fetch(API+"/cognitive/status",{cache:"no-store"}).then(r=>r.json()),
        fetch(API+"/cognitive/traces/summary?days=30",{cache:"no-store"}).then(r=>r.json()),
        fetch(API+"/cognitive/schedules",{cache:"no-store"}).then(r=>r.json())
      ]);
      $("cognitive-memory-count").textContent=s.memory_documents??"—";
      $("cognitive-tool-count").textContent=t.tool_calls??"0";
      $("cognitive-success-rate").textContent=t.success_rate==null?"—":Math.round(t.success_rate*100)+"%";
      $("cognitive-schedule-count").textContent=(q.schedules||[]).length;
      $("cognitive-tool-metrics").replaceChildren();
      (t.tools||[]).forEach(item=>{
        const row=document.createElement("div");row.className="cognitive-result-row";
        const title=document.createElement("b");title.textContent=item.tool||"Ferramenta";
        const detail=document.createElement("small");detail.textContent=item.calls+" chamadas · "+Math.round((item.success_rate||0)*100)+"% sucesso · "+Math.round(item.avg_latency_ms||0)+" ms";
        row.append(title,detail);$("cognitive-tool-metrics").appendChild(row);
      });
      if(!(t.tools||[]).length)$("cognitive-tool-metrics").textContent="Ainda não há chamadas registradas.";
      renderCognitiveSchedules(q.schedules||[]);
      if(status)status.textContent="Memória "+(s.embedding_model?"vetorial + FTS5":"FTS5")+" · banco local ativo.";
    }catch(error){if(status)status.textContent="Não foi possível consultar o Cognitive Core: "+error.message}
  }
  function renderCognitiveSchedules(items){
    const list=$("cognitive-schedule-list");list.replaceChildren();
    if(!items.length){list.textContent="Nenhum agente contínuo agendado.";return}
    items.forEach(item=>{
      const row=document.createElement("div");row.className="cognitive-schedule-row";
      const info=document.createElement("div");info.className="cognitive-schedule-info";
      const name=document.createElement("b");name.textContent=item.name;
      const prompt=document.createElement("small");prompt.textContent=item.prompt;
      const meta=document.createElement("small");meta.textContent="A cada "+Math.round(item.interval_seconds/60)+" min · "+(item.enabled?"Ativo":"Pausado")+" · Última execução: "+(item.last_status||"ainda não executado");
      info.append(name,prompt,meta);
      const actions=document.createElement("div");actions.className="cognitive-schedule-actions";
      const toggle=document.createElement("button");toggle.className="soft-button";toggle.type="button";toggle.textContent=item.enabled?"Pausar":"Retomar";
      toggle.addEventListener("click",async()=>{toggle.disabled=true;try{const r=await fetch(API+"/cognitive/schedules/"+encodeURIComponent(item.id)+"/toggle",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({enabled:!item.enabled})});if(!r.ok)throw new Error("Falha ao alterar agendamento");await refreshCognitiveConsole()}catch(e){$("cognitive-schedule-status").textContent=e.message}finally{toggle.disabled=false}});
      const history=document.createElement("button");history.className="soft-button";history.type="button";history.textContent="Histórico";history.addEventListener("click",async()=>{history.disabled=true;try{const response=await fetch(API+"/cognitive/schedules/"+encodeURIComponent(item.id)+"/runs");const data=await response.json();if(!response.ok)throw new Error("Falha ao consultar histórico");info.querySelectorAll(".cognitive-run-history").forEach(el=>el.remove());(data.runs||[]).forEach(run=>{const line=document.createElement("small");line.className="cognitive-run-history";line.textContent=new Date(run.started_at*1000).toLocaleString()+" · "+run.status+" · "+String(run.result||"").slice(0,180);info.appendChild(line)});if(!(data.runs||[]).length){const line=document.createElement("small");line.className="cognitive-run-history";line.textContent="Nenhuma execução registrada.";info.appendChild(line)}}catch(e){$("cognitive-schedule-status").textContent=e.message}finally{history.disabled=false}});
      const remove=document.createElement("button");remove.className="soft-button danger-button";remove.type="button";remove.textContent="Excluir";
      remove.addEventListener("click",async()=>{if(!confirm("Excluir este agente contínuo?"))return;remove.disabled=true;try{const r=await fetch(API+"/cognitive/schedules/"+encodeURIComponent(item.id),{method:"DELETE"});if(!r.ok)throw new Error("Falha ao excluir");await refreshCognitiveConsole()}catch(e){$("cognitive-schedule-status").textContent=e.message}finally{remove.disabled=false}});
      actions.append(toggle,history,remove);row.append(info,actions);list.appendChild(row);
    });
  }
  function initCognitiveConsole(){
    const $=id=>document.getElementById(id);
    $("cognitive-refresh")?.addEventListener("click",refreshCognitiveConsole);
    $("cognitive-search-button")?.addEventListener("click",async()=>{
      const query=$("cognitive-query").value.trim(),out=$("cognitive-search-results");out.textContent="Buscando...";
      if(!query){out.textContent="Digite algo para pesquisar.";return}
      try{const r=await fetch(API+"/cognitive/memory/search",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({query,limit:8})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Busca falhou");out.replaceChildren();(d.results||[]).forEach(item=>{const row=document.createElement("div");row.className="cognitive-result-row";const b=document.createElement("b");b.textContent=item.title;const small=document.createElement("small");small.textContent=item.source+" · "+item.retrieval;const p=document.createElement("p");p.textContent=item.snippet;row.append(b,small,p);out.appendChild(row)});if(!d.results?.length)out.textContent="Nenhuma memória relevante encontrada."}catch(e){out.textContent=e.message}
    });
    $("cognitive-index-button")?.addEventListener("click",async()=>{
      const path=$("cognitive-index-path").value.trim(),status=$("cognitive-memory-status"),button=$("cognitive-index-button");
      if(!path){status.textContent="Informe um caminho do workspace ou repositório configurado.";return}
      button.disabled=true;status.textContent="Indexando arquivos locais...";
      try{const r=await fetch(API+"/cognitive/memory/index-path",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Falha ao indexar");status.textContent=d.indexed+" arquivo(s) indexado(s). "+(d.errors?.length||0)+" erro(s).";await refreshCognitiveConsole()}catch(e){status.textContent=e.message}finally{button.disabled=false}
    });
    $("cognitive-schedule-create")?.addEventListener("click",async()=>{
      const name=$("cognitive-schedule-name").value.trim(),prompt=$("cognitive-schedule-prompt").value.trim(),interval_seconds=Number($("cognitive-schedule-interval").value),status=$("cognitive-schedule-status"),button=$("cognitive-schedule-create");
      button.disabled=true;status.textContent="Salvando agendamento...";
      try{const r=await fetch(API+"/cognitive/schedules",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name,prompt,interval_seconds})});const d=await r.json();if(!r.ok)throw new Error(d.detail||"Falha ao criar agendamento");$("cognitive-schedule-name").value="";$("cognitive-schedule-prompt").value="";status.textContent="Agendamento salvo localmente. Primeira execução após o intervalo escolhido.";await refreshCognitiveConsole()}catch(e){status.textContent=e.message}finally{button.disabled=false}
    });
  }

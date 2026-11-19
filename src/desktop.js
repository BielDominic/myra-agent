(() => {
  const API = "http://127.0.0.1:8000";
  const STORAGE_KEY = "myra-desktop-conversations-v2";
  const CODE_KEY = "myra-code-studio-v1";
  const PROJECT_KEY = "myra-projects-v1";
  const PREF_KEY = "myra-desktop-prefs-v1";
  const QUEUE_KEY = "myra-desktop-message-queue-v1";
  const PLUGIN_REQUESTS_KEY = "myra-plugin-source-requests-v1";
  let pluginRequests = load(PLUGIN_REQUESTS_KEY, []);
  const $ = id => document.getElementById(id);
  let conversations = load(STORAGE_KEY, []);
  let projects = load(PROJECT_KEY, []);
  let activeId = conversations[0]?.id || null;
  let busy = false, online = false, executionMode = false, selectedModel = "";
  let historySelectionMode = false;
  const selectedConversationIds = new Set();
  const activeSkills = new Set();
  let speechRecognition = null;
  let codeFiles = load(CODE_KEY, null) || {
    "index.html": {lang:"HTML",content:'<!doctype html>\n<html lang="pt-BR">\n<head>\n  <meta charset="utf-8">\n  <meta name="viewport" content="width=device-width,initial-scale=1">\n  <title>Meu projeto</title>\n</head>\n<body>\n  <main class="hero">\n    <span class="eyebrow">MYRA CODE STUDIO</span>\n    <h1>Olá, mundo.</h1>\n    <p>Seu próximo projeto começa aqui.</p>\n    <button onclick="document.querySelector(\'p\').textContent=\'Está funcionando!\'">Testar interação</button>\n  </main>\n</body>\n</html>'},
    "style.css": {lang:"CSS",content:'* { box-sizing: border-box; }\nbody { margin: 0; min-height: 100vh; display: grid; place-items: center; font-family: Inter, system-ui, sans-serif; background: #0d1020; color: #f5f3ff; }\n.hero { text-align: center; padding: 48px; }\n.eyebrow { color: #8b5cf6; letter-spacing: .18em; font-size: 11px; }\nh1 { font-size: clamp(36px, 8vw, 72px); margin: 16px 0; }\np { color: #a6a6bb; }\nbutton { border: 0; border-radius: 9px; padding: 12px 18px; background: #7c3aed; color: white; cursor: pointer; }'},
    "script.js": {lang:"JS",content:'console.log("MYRA sandbox ready");'}
  };
  let activeFile = "index.html", previewTimer = null;
  function load(key, fallback) { try { const v = JSON.parse(localStorage.getItem(key)); return v ?? fallback; } catch (_) { return fallback; } }
  function save(key, value) { try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { console.warn("[MYRA] storage",e); } }
  function activeConversation(){return conversations.find(x=>x.id===activeId)}
  function createConversation(render=true){const item={id:"chat-"+Date.now()+"-"+Math.random().toString(36).slice(2,7),title:"Nova conversa",messages:[],updatedAt:Date.now()};conversations.unshift(item);activeId=item.id;if(render){save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();renderMessages()}return item.id}
  function renderSidebar(){
    const list=$("conversation-list");list.replaceChildren();
    conversations.slice(0,60).forEach(item=>{
      const row=document.createElement("div");row.className="conversation-row-wrap"+(item.id===activeId?" active":"");
      if(historySelectionMode){const check=document.createElement("input");check.type="checkbox";check.className="conversation-select";check.checked=selectedConversationIds.has(item.id);check.setAttribute("aria-label","Selecionar "+(item.title||"conversa"));check.addEventListener("change",()=>{check.checked?selectedConversationIds.add(item.id):selectedConversationIds.delete(item.id);updateHistoryBulk()});row.append(check)}
      const b=document.createElement("button");b.type="button";b.className="conversation-row"+(item.id===activeId?" active":"");b.innerHTML="<i>◈</i><span></span>";b.querySelector("span").textContent=item.title||"Nova conversa";
      b.addEventListener("click",()=>{if(historySelectionMode){selectedConversationIds.has(item.id)?selectedConversationIds.delete(item.id):selectedConversationIds.add(item.id);renderSidebar();return}activeId=item.id;renderSidebar();renderMessages();showView("chat")});
      row.append(b);
      const del=document.createElement("button");del.type="button";del.className="conversation-delete";del.textContent="×";del.title="Excluir esta conversa";del.setAttribute("aria-label","Excluir conversa");del.addEventListener("click",e=>{e.stopPropagation();deleteConversations([item.id])});row.append(del);list.append(row);
    });
    $("select-history").setAttribute("aria-pressed",String(historySelectionMode));$("history-bulk").hidden=!historySelectionMode;updateHistoryBulk();
  }
  function updateHistoryBulk(){const count=selectedConversationIds.size;$("history-selected-count").textContent=count+" selecionada(s)";$("delete-selected-history").disabled=count===0;$("select-all-history").checked=conversations.length>0&&conversations.every(c=>selectedConversationIds.has(c.id))}
  function deleteConversations(ids){
    const targets=conversations.filter(c=>ids.includes(c.id));if(!targets.length)return;
    const count=targets.length;showModal("Excluir conversas",count===1?"Esta conversa será removida deste dispositivo.":"As "+count+" conversas selecionadas serão removidas deste dispositivo.","delete-history");
    $("modal-confirm").textContent=count===1?"Excluir conversa":"Excluir "+count+" conversas";
    $("modal-confirm").onclick=()=>{conversations=conversations.filter(c=>!ids.includes(c.id));ids.forEach(id=>selectedConversationIds.delete(id));if(!conversations.some(c=>c.id===activeId))activeId=conversations[0]?.id||null;if(!conversations.length)createConversation(false);save(STORAGE_KEY,conversations.slice(0,60));closeModal();renderSidebar();renderMessages()};
  }
  function renderMessages(){const c=activeConversation(),box=$("messages");box.replaceChildren();const empty=!c||!c.messages.length;$("welcome").hidden=!empty;if(!empty)c.messages.forEach(m=>appendMessage(m.role,m.content,false));$("chat-scroll").scrollTop=$("chat-scroll").scrollHeight}
  function appendMessage(role,content,scroll=true){
    const row=document.createElement("div");row.className="message "+(role==="user"?"user":"assistant");
    const avatar=document.createElement("div");avatar.className="message-avatar";avatar.textContent=role==="user"?"M":"MY";
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
    if(role==="user"){text.textContent=display;body.append(text)}else{renderAssistantContent(body,display)}
    row.append(avatar,body);$("messages").appendChild(row);
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
        control=document.createElement("select");const empty=document.createElement("option");empty.value="";empty.textContent="Selecione uma op??o";control.append(empty);
        q.options.slice(0,12).forEach(value=>{const opt=document.createElement("option");opt.value=String(value);opt.textContent=String(value);control.append(opt)});
      }else{control=document.createElement("input");control.type="text";control.placeholder=q.placeholder||"Digite sua resposta"; }
      control.dataset.questionId=q.id||("q"+index);control.dataset.questionLabel=q.label||("Pergunta "+(index+1));control.required=q.required!==false;wrap.append(control);card.append(wrap);
    });
    const submit=document.createElement("button");submit.type="submit";submit.className="primary-button";submit.textContent="Enviar respostas";card.append(submit);
    card.addEventListener("submit",event=>{event.preventDefault();const answers=[];let valid=true;card.querySelectorAll("[data-question-id]").forEach(control=>{if(control.required&&!control.value.trim())valid=false;answers.push(control.dataset.questionLabel+": "+(control.value.trim()||"N?o informado"))});if(!valid){card.querySelector("[data-question-id]:invalid")?.focus();return}card.querySelectorAll("input,select,button").forEach(el=>el.disabled=true);sendMessage("Respostas ao question?rio da MYRA:"+String.fromCharCode(10)+answers.join(String.fromCharCode(10)));});
    parent.append(card);
  }
  function renderPlugins(){
    const catalog=[
      {id:"web-research",name:"Web Research",type:"Tool",category:"research",state:"Nativo",description:"Busca externa, leitura de páginas, comparação de fontes e citações.",url:"https://docs.openwebui.com/features/extensibility/plugin/tools/"},
      {id:"browser-agent",name:"BrowserAgent",type:"Tool",category:"research",state:"Nativo",description:"Navegação, leitura e interação com páginas usando a bridge existente da MYRA.",url:"https://github.com/BielDominic/myra-agent"},
      {id:"myra-local-pipe",name:"MYRA Local · Memória + Tarefas",type:"Agent",category:"memory",state:"Nativo",description:"Camada local de continuidade por conversa, separação entre intenção de chat e tarefas e integração com o executor.",url:"https://github.com/BielDominic/myra-agent"},
      {id:"senior-code-review",name:"Senior Code Review",type:"Skill",category:"development",state:"Planejado",description:"Revisão de segurança, testes, desempenho, arquitetura e manutenção.",url:"https://github.com/continuedev/continue"},
      {id:"frontend-design",name:"Frontend Design",type:"Skill",category:"design",state:"Planejado",description:"Design system, responsividade, acessibilidade e microinterações.",url:"https://github.com/All-Hands-AI/OpenHands"},
      {id:"aider",name:"Aider Coding Agent",type:"Referência",category:"development",state:"Avaliar",description:"Referência de fluxo de engenharia com alterações de código e validação.",url:"https://github.com/Aider-AI/aider"},
      {id:"openhands",name:"OpenHands",type:"Referência",category:"development",state:"Avaliar",description:"Referência de agente de engenharia de software e execução de tarefas.",url:"https://github.com/All-Hands-AI/OpenHands"},
      {id:"whisper",name:"Whisper / whisper.cpp",type:"Provider STT",category:"voice",state:"Planejado",description:"Reconhecimento de voz local e transcrição de áudio.",url:"https://github.com/ggml-org/whisper.cpp"},
      {id:"piper",name:"Piper TTS",type:"Provider TTS",category:"voice",state:"Planejado",description:"Síntese de voz neural local com modelos de voz selecionáveis.",url:"https://github.com/rhasspy/piper"},
      {id:"context-memory",name:"Context Engine",type:"Filter",category:"memory",state:"Planejado",description:"Resumo de conversas longas, memória de projeto e recuperação contextual.",url:"https://docs.openwebui.com/features/extensibility/"}
    ];
    const host=$("plugin-grid");if(!host)return;host.replaceChildren();
    const query=($("plugin-search").value||"").toLowerCase(),category=$("plugin-category").value;
    catalog.filter(p=>(category==="all"||p.category===category)&&[p.name,p.description,p.type].join(" ").toLowerCase().includes(query)).forEach(p=>{
      const card=document.createElement("article");card.className="plugin-card";
      const top=document.createElement("div");top.className="plugin-card-top";const type=document.createElement("span");type.textContent=p.type;const state=document.createElement("span");state.className="plugin-state "+(p.state==="Nativo"?"native":"planned");state.textContent=p.state;top.append(type,state);
      const name=document.createElement("h3");name.textContent=p.name;const desc=document.createElement("p");desc.textContent=p.description;
      const actions=document.createElement("div");actions.className="plugin-card-actions";const link=document.createElement("a");link.href=p.url;link.target="_blank";link.rel="noreferrer";link.textContent="Ver fonte ↗";actions.append(link);
      const request=document.createElement("button");request.type="button";request.className="soft-button";request.textContent="Solicitar avaliação";request.addEventListener("click",()=>{pluginRequests.push({id:p.id,name:p.name,url:p.url,createdAt:Date.now(),status:"pending-review"});save(PLUGIN_REQUESTS_KEY,pluginRequests);renderPluginRequests();$("plugin-source-status").textContent=p.name+" adicionado à fila de avaliação local.";});actions.append(request);
      card.append(top,name,desc,actions);host.append(card);
    });
    renderPluginRequests();
  }
  function renderPluginRequests(){
    const host=$("plugin-submitted-list");if(!host)return;host.replaceChildren();
    pluginRequests.forEach((item,index)=>{const row=document.createElement("div");row.className="plugin-request-row";const label=document.createElement("span");label.textContent=(item.name||item.url)+" · Aguardando análise";const remove=document.createElement("button");remove.type="button";remove.textContent="Remover";remove.addEventListener("click",()=>{pluginRequests.splice(index,1);save(PLUGIN_REQUESTS_KEY,pluginRequests);renderPluginRequests()});row.append(label,remove);host.append(row)});
  }
  function addPluginSource(){
    const input=$("plugin-source-url"),value=String(input.value||"").trim();if(!value)return;
    let url;try{url=new URL(value)}catch(_){$("plugin-source-status").textContent="Informe uma URL HTTPS ou Git válida.";return}
    if(url.protocol!=="https:"||!(/github\.com$|gitlab\.com$|codeberg\.org$/.test(url.hostname))){$("plugin-source-status").textContent="Por segurança, nesta etapa só aceitamos fontes Git HTTPS conhecidas (GitHub, GitLab ou Codeberg).";return}
    if(pluginRequests.some(p=>p.url===url.href)){$("plugin-source-status").textContent="Essa fonte já está na fila de avaliação.";return}
    pluginRequests.unshift({id:"custom-"+Date.now(),name:url.pathname.split("/").filter(Boolean).slice(0,2).join("/"),url:url.href,createdAt:Date.now(),status:"pending-review"});
    save(PLUGIN_REQUESTS_KEY,pluginRequests);input.value="";$("plugin-source-status").textContent="Fonte adicionada à fila. A MYRA ainda não executou nem instalou esse código.";renderPluginRequests();
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
        setupLog("Baixando "+prefs.model+". O download depende da sua conexão e pode levar alguns minutos…");
        const r=await fetch(API+"/setup/model",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:prefs.model}),signal:AbortSignal.timeout(3600000)});
        const data=await r.json().catch(()=>({}));
        if(!r.ok)throw new Error(data.detail||"Falha ao baixar o modelo.");
        setupLog(data.message||"Modelo pronto.");
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
    $("setup-finish").addEventListener("click",runSetup);
    $("setup-save").addEventListener("click",()=>{save("myra-setup-preferences-v1",{vision:$("setup-vision").checked,ollama:$("setup-ollama").checked,model:$("setup-model").value,updatedAt:Date.now()});setupLog("Preferências salvas neste perfil. Nenhum pacote foi baixado.")});
    $("setup-skip").addEventListener("click",()=>{save(SETUP_KEY,{completed:true,deferred:true,completedAt:Date.now()});setupLog("Etapas adiadas. Você poderá voltar a esta aba quando quiser.");showView("chat")});
    refreshSetupStatus();
  }
  async function improvePrompt(){
    const input=$("message-input"),draft=input.value.trim(),button=$("improve-prompt");
    if(!draft){input.focus();button.title="Escreva primeiro o que deseja pedir à MYRA.";return}
    button.disabled=true;button.textContent="Aprimorando…";
    try{
      const r=await fetch(API+"/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"myra-agent",stream:false,messages:[{role:"system",content:"Você é um especialista sênior em engenharia de prompts. Reescreva o pedido do usuário para ficar claro, específico, completo e executável. Preserve a intenção e as restrições; acrescente critérios de sucesso, formato esperado e perguntas apenas quando indispensáveis. Não execute o pedido, não invente requisitos. Retorne somente o prompt aprimorado em português brasileiro."},{role:"user",content:draft}]}),signal:AbortSignal.timeout(120000)});
      const data=await r.json().catch(()=>({}));
      if(!r.ok)throw new Error(data.detail||"O modelo local não respondeu.");
      const improved=data?.choices?.[0]?.message?.content?.trim();
      if(!improved)throw new Error("A resposta do melhorador veio vazia.");
      input.value=improved;resizeInput();input.focus();button.title="Prompt aprimorado. Revise antes de enviar.";setupLog("Prompt aprimorado. Revise o texto antes de enviar.");
    }catch(e){button.title="Não foi possível melhorar: "+e.message;setupLog("Melhorador de prompts: "+e.message)}
    finally{button.disabled=false;button.textContent="✦ Melhorar prompt"}
  }
  function showView(name){document.querySelectorAll(".view").forEach(v=>v.classList.toggle("active",v.id==="view-"+name));document.querySelectorAll(".nav-item").forEach(b=>b.classList.toggle("active",b.dataset.view===name));const names={chat:"Conversas",activity:"Atividades",tools:"Ferramentas",settings:"Configurações",projects:"Projetos",code:"Code Studio",preview:"Pré-visualização",integrations:"Integrações",plugins:"Biblioteca de plugins",models:"Modelos",widget:"Widget Studio",setup:"Primeiros passos"};$("top-context").textContent=names[name]||"MYRA";if(name==="code"||name==="preview")renderPreview();if(name==="projects")renderProjects();if(name==="models")refreshModels();if(name==="integrations"){refreshGitHub();refreshApiIntegrations()}if(name==="plugins")renderPlugins();if(name==="setup")refreshSetupStatus()}
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
  async function setChatActivity(active){try{await fetch(API+"/chat_activity",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({active:Boolean(active)})})}catch(_){}}
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
  function sendMessage(raw){
    if(!load(SETUP_KEY,{}).completed){showView("setup");setupLog("Conclua ou adie os primeiros passos antes de iniciar uma conversa.");return}
    const displayContent=String(raw||"").trim();if(!displayContent)return;let content=displayContent;
    const instructions={code:"Atue como engenheira de software sênior. Planeje a solução, produza código completo e executável, valide acessibilidade, segurança, responsividade e testes. Não entregue apenas snippets quando o pedido exigir um projeto.",research:"Pesquise fontes externas atuais e confiáveis antes de responder. Compare fontes, cite links e separe fatos verificados de hipóteses.",design:"Atue como designer de produto e frontend sênior. Defina hierarquia visual, tipografia, espaçamento, responsividade, estados vazios e microinterações.",review:"Faça uma revisão crítica de nível sênior: procure bugs, riscos de segurança, acessibilidade, desempenho, casos extremos e testes ausentes."};
    if(activeSkills.size){const guidance=[...activeSkills].map(key=>instructions[key]).filter(Boolean).join("\n\n");content="[MODO DE TRABALHO ATIVADO]\n"+guidance+"\n\n[PEDIDO]\n"+content}
    activeSkills.clear();document.querySelectorAll(".skill-chip").forEach(b=>b.classList.remove("active"));
    messageQueue.push({content,displayContent,taskMode:executionMode,conversationId:activeId,createdAt:Date.now()});
    $("message-input").value="";resizeInput();renderQueue();
    if(!busy&&!queueNeedsResume)processQueue();
  }
  function startVoiceInput(){
    const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){$("voice-input").title="Reconhecimento de voz não disponível neste Chromium.";return}
    if(speechRecognition){speechRecognition.stop();speechRecognition=null;$("voice-input").classList.remove("recording");return}
    speechRecognition=new SR();speechRecognition.lang="pt-BR";speechRecognition.continuous=false;speechRecognition.interimResults=true;
    speechRecognition.onresult=e=>{let transcript="";for(let i=e.resultIndex;i<e.results.length;i++)transcript+=e.results[i][0].transcript;$("message-input").value=transcript;resizeInput()};
    speechRecognition.onerror=e=>{$("voice-input").title="Falha no reconhecimento: "+e.error};
    speechRecognition.onend=()=>{$("voice-input").classList.remove("recording");speechRecognition=null};
    $("voice-input").classList.add("recording");speechRecognition.start();
  }
  function readLastAnswer(){
    const c=activeConversation(),last=[...(c?.messages||[])].reverse().find(m=>m.role==="assistant");
    if(!last){$("voice-read").title="Ainda não há resposta para ler.";return}
    if(!("speechSynthesis" in window)){ $("voice-read").title="Síntese de voz não disponível neste Chromium.";return}
    window.speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(String(last.content||"").replace(/\x60{3}[\s\S]*?\x60{3}/g,"bloco de código"));utterance.lang="pt-BR";window.speechSynthesis.speak(utterance);
  }
  async function waitForTaskCompletion(){
    const started=Date.now();
    while(Date.now()-started<30*60*1000){
      await new Promise(resolve=>setTimeout(resolve,1100));
      try{const r=await fetch(API+"/task_status",{cache:"no-store"});if(!r.ok)continue;const s=await r.json();if(s.state!=="running")return s;}catch(_){}
    }
    return {state:"timeout",resultado:"A tarefa continua sem confirma??o ap?s 30 minutos. Consulte Atividades."};
  }
  async function processQueue(){
    if(busy||queueNeedsResume||!messageQueue.length)return;
    const queued=messageQueue.shift(),content=queued.content,displayContent=queued.displayContent||queued.content,taskMode=queued.taskMode;
    renderQueue();
    let c=conversations.find(x=>x.id===queued.conversationId)||activeConversation();if(!c){createConversation();c=activeConversation()}
    c.messages.push({role:"user",content:displayContent});c.updatedAt=Date.now();
    if(c.title==="Nova conversa")c.title=displayContent.slice(0,38)+(displayContent.length>38?".":"");
    if(activeId===c.id){$("welcome").hidden=true;appendMessage("user",displayContent)}setBusy(true);
    save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();
    try{
      await setChatActivity(true);let answer;
      if(taskMode){
        const previous=c.messages.slice(0,-1).slice(-6);
        const refers=/(isso|esse|essa|ele|ela|dessa|desse|continue|that|it)/i.test(content);
        const objective=refers&&previous.length?("CONTEXTO RECENTE:"+String.fromCharCode(10)+previous.map(m=>m.role+": "+m.content.slice(0,500)).join(String.fromCharCode(10))+String.fromCharCode(10,10)+"PEDIDO ATUAL:"+String.fromCharCode(10)+content):content;
        const res=await fetch(API+"/task_start",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({objetivo:objective.slice(0,4000),max_passos:20})});
        const data=await res.json().catch(()=>({}));if(!res.ok)throw new Error(data.detail||data.result||"Backend HTTP "+res.status);
        const final=await waitForTaskCompletion();
        answer=final.state==="done"?(final.resultado||"Tarefa conclu?da."):final.state==="error"?(final.erro||"A tarefa falhou."):final.state==="timeout"?final.resultado:final.state==="idle"?"A tarefa foi encerrada.":("Estado da tarefa: "+final.state);
        showView("activity");
      }else{
        const res=await fetch(API+"/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:"myra-agent",stream:false,metadata:{chat_id:c.id,user_id:"local-user"},messages:c.messages.map(m=>({role:m.role,content:m.content}))}),signal:AbortSignal.timeout(120000)});
        if(!res.ok)throw new Error("Backend HTTP "+res.status+": "+(await res.text()).slice(0,160));
        const data=await res.json();answer=data?.choices?.[0]?.message?.content;
        if(typeof answer!=="string"||!answer.trim())throw new Error("A MYRA retornou uma resposta vazia.");
        answer=answer.trim();
      }
      c.messages.push({role:"assistant",content:answer});c.updatedAt=Date.now();if(activeId===c.id)appendMessage("assistant",answer);save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();
    }catch(e){
      const failure="Não consegui concluir. "+(e?.name==="TimeoutError"?"O modelo demorou mais de 120 segundos. Verifique o modelo local e tente novamente.":(e?.message||"Verifique o backend local."));
      c.messages.push({role:"assistant",content:failure});c.updatedAt=Date.now();if(activeId===c.id)appendMessage("assistant",failure);save(STORAGE_KEY,conversations.slice(0,60));renderSidebar();
      console.error("[MYRA CHAT]",e);
    }finally{
      await setChatActivity(false);setBusy(false);refreshTaskStatus();
      if(messageQueue.length)processQueue();else $("message-input").focus();
    }
  }
  function resizeInput(){const el=$("message-input");el.style.height="auto";el.style.height=Math.min(el.scrollHeight,130)+"px";$("send-button").disabled=!el.value.trim()}
  async function checkBackend(){try{const r=await fetch(API+"/",{cache:"no-store",signal:AbortSignal.timeout(1800)});online=r.ok}catch(_){online=false}const cls=online?"online":"offline";$("service-light").className="service-light "+cls;$("status-dot").className="status-dot "+cls;$("service-title").textContent=online?"MYRA conectada":"MYRA offline";$("service-subtitle").textContent=online?"Backend local disponível":"Backend local indisponível";$("status-text").textContent=online?"Sistema operacional":"Aguardando backend"}
  async function refreshTaskStatus(){try{const r=await fetch(API+"/task_status",{cache:"no-store",signal:AbortSignal.timeout(1800)});if(!r.ok)return;const s=await r.json(),state=s.state||"idle",paused=state==="paused"||state==="pausado"||/PAUSADO/i.test(s.passo_atual||""),active=state==="running"&&!paused;$("activity-count").textContent=active?"1":"0";$("tool-state").textContent=active?"Em execução":"Aguardando";$("activity-title").textContent=paused?"Tarefa pausada":active?"MYRA está executando":state==="error"?"A última tarefa falhou":state==="done"?"Última tarefa concluída":"Nenhuma atividade em andamento";$("activity-description").textContent=paused?"A tarefa foi salva e pode ser retomada.":active?(s.objetivo||"Tarefa em andamento."):state==="error"?(s.erro||"Execução interrompida."):state==="done"?(s.resultado||"A MYRA concluiu a tarefa."):"Ative o modo Executar tarefa no chat para delegar ações à MYRA.";$("activity-step").hidden=!active&&!paused;$("activity-step").textContent=active||paused?[s.passo_atual||"Planejando",s.passo_num?"Etapa "+s.passo_num+(s.passo_total?" de "+s.passo_total:""):""].filter(Boolean).join(" · "):"";$("activity-symbol").textContent=paused?"Ⅱ":active?"◌":state==="done"?"✓":state==="error"?"⚠":"⌁";$("activity-pause").disabled=!active;$("activity-resume").disabled=!paused;$("activity-takeover").disabled=!active&&!paused;$("activity-cancel").disabled=!active&&!paused}catch(_){}}
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
  async function refreshModels(){const list=$("model-list");if(!list)return;list.innerHTML='<div class="model-empty">Consultando Ollama...</div>';try{const r=await fetch(API+"/models/local",{cache:"no-store",signal:AbortSignal.timeout(3000)});if(!r.ok)throw new Error("Endpoint de modelos indisponível");const data=await r.json();const models=data.models||[];selectedModel=data.selected||"";$("model-count").textContent=models.length+" INSTALADOS";$("current-model").textContent=selectedModel||"Não selecionado";$("activity-model").textContent=selectedModel||"—";["quick-model","settings-model"].forEach(id=>{const sel=$(id);if(!sel)return;sel.replaceChildren();models.forEach(m=>{const o=document.createElement("option");o.value=m.name;o.textContent=m.name;sel.appendChild(o)});if(selectedModel)sel.value=selectedModel});list.replaceChildren();if(!models.length){list.innerHTML='<div class="model-empty">Nenhum modelo local encontrado. Instale um modelo pelo Ollama e atualize.</div>';return}models.forEach(m=>{const row=document.createElement("div");row.className="model-row"+(m.name===selectedModel?" active":"");const info=document.createElement("div");info.className="model-row-icon";info.innerHTML=iconSvg("cpu");const details=document.createElement("div");details.className="model-row-info";const name=document.createElement("b");name.textContent=m.name;const sub=document.createElement("small");sub.textContent=(m.parameter_size||"Modelo local")+" · "+(m.quantization_level||"Ollama");details.append(name,sub);const btn=document.createElement("button");btn.textContent=m.name===selectedModel?"Em uso":"Usar modelo";btn.addEventListener("click",()=>selectModel(m.name));row.append(info,details,btn);list.append(row)})}catch(e){list.innerHTML='<div class="model-empty">Não foi possível listar os modelos. '+escapeText(e.message)+'</div>'}}
  function escapeText(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]))}
  async function selectModel(name){try{const r=await fetch(API+"/models/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({model:name})});const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||"Não foi possível alterar o modelo");selectedModel=name;$("current-model").textContent=name;await refreshModels()}catch(e){showModal("Não foi possível trocar o modelo",e.message,"")}}
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
    }else{
      box.textContent="Plugins externos ainda nao sao executados pelo nucleo da MYRA. Nenhum plugin sera marcado como conectado ate existir instalacao, permissao e isolamento reais.";
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
      state.textContent=d.github_authenticated?"CONECTADO":"SEM AUTENTICA??O";state.className=d.github_authenticated?"live-label":"coming-state";
      $("github-changes").textContent=(d.changes||[]).length?(d.changes||[]).slice(0,15).join(String.fromCharCode(10)):"Nenhuma altera??o local detectada.";
      $("github-fetch").disabled=!d.github_authenticated;
      $("github-pull").disabled=!d.github_authenticated||Boolean(d.dirty);
      $("github-push").disabled=!d.github_authenticated||Boolean(d.dirty);
    }catch(e){state.textContent="OFFLINE";$("github-repo-meta").textContent=e.message;$("github-changes").textContent="N?o foi poss?vel consultar o backend."}
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
      if(!response.ok)throw new Error("O backend n?o conseguiu gerar o pacote.");
      const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");
      a.href=url;a.download="myra-agent-workspace.zip";document.body.append(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),2000);
    }catch(error){alert("N?o foi poss?vel baixar o projeto: "+error.message)}
  }
  function initSettings(){const prefs=load(PREF_KEY,{});if(prefs.theme){$("theme-setting").value=prefs.theme;document.body.dataset.theme=prefs.theme}if(prefs.density){$("density-setting").value=prefs.density;document.body.dataset.density=prefs.density}if(prefs.accent)applyAccent(prefs.accent);$("theme-setting").addEventListener("change",e=>{document.body.dataset.theme=e.target.value;save(PREF_KEY,{...load(PREF_KEY,{}),theme:e.target.value})});$("density-setting").addEventListener("change",e=>{document.body.dataset.density=e.target.value;save(PREF_KEY,{...load(PREF_KEY,{}),density:e.target.value})});document.querySelectorAll("[data-accent]").forEach(b=>b.addEventListener("click",()=>{applyAccent(b.dataset.accent);save(PREF_KEY,{...load(PREF_KEY,{}),accent:b.dataset.accent})}));document.querySelectorAll("[data-settings-tab]").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll("[data-settings-tab]").forEach(x=>x.classList.toggle("selected",x===b));document.querySelectorAll("[data-settings-panel]").forEach(p=>p.classList.toggle("active",p.dataset.settingsPanel===b.dataset.settingsTab))}));$("animations-setting").addEventListener("change",e=>{document.body.classList.toggle("no-motion",!e.target.checked)})}
  const WIDGET_CONFIG_KEY="myra-widget-config-v1";
  const WIDGET_DEFAULTS={accent:"purple",opacity:100,width:360,height:280};
  function widgetConfig(){return {...WIDGET_DEFAULTS,...load(WIDGET_CONFIG_KEY,{})};}
  function widgetDraft(){
    return {accent:$("widget-accent").value,opacity:Number($("widget-opacity").value),
      width:Number($("widget-width").value),height:Number($("widget-height").value)};
  }
  function updateWidgetLabels(c){
    $("widget-opacity-value").textContent=c.opacity+"%";
    $("widget-width-value").textContent=c.width+" px";
    $("widget-height-value").textContent=c.height+" px";
  }
  function renderWidgetConfig(c=widgetConfig()){
    $("widget-accent").value=c.accent||"purple";
    $("widget-opacity").value=c.opacity??100;
    $("widget-width").value=c.width??360;
    $("widget-height").value=c.height??280;
    updateWidgetLabels(c);renderWidgetPreview();
  }
  const widgetSyncChannel=typeof BroadcastChannel!=="undefined"?new BroadcastChannel("myra-widget-sync"):null;
  function publishWidgetConfig(c){try{widgetSyncChannel?.postMessage({type:"config",config:c})}catch(e){console.warn("[WIDGET SYNC]",e)}}
  function applyWidgetConfig(){
    const c={...widgetDraft(),updatedAt:Date.now()};
    save(WIDGET_CONFIG_KEY,c);publishWidgetConfig(c);
    $("widget-save-status").textContent="Configuração salva e enviada ao widget real.";
    $("widget-save-status").dataset.state="saved";
  }
  function renderWidgetPreview(){
    const host=$("widget-preview");if(!host)return;
    const c=widgetDraft(),mode=$("widget-preview-mode")?.value||"idle",layout=$("widget-preview-layout")?.value||"panel";
    const palette={purple:["#7c3aed","#06b6d4"],blue:["#2563eb","#22d3ee"],green:["#059669","#67e8f9"]}[c.accent]||["#7c3aed","#06b6d4"];
    host.replaceChildren();host.style.setProperty("--preview-accent",palette[0]);host.style.setProperty("--preview-cyan",palette[1]);
    host.style.opacity=String(c.opacity/100);host.style.width=layout==="pill"?"260px":layout==="compact"?"300px":Math.min(c.width,480)+"px";host.style.minHeight=layout==="pill"?"auto":layout==="compact"?"150px":Math.min(c.height,420)+"px";host.style.borderRadius=layout==="pill"?"999px":layout==="compact"?"13px":"17px";
    host.className="widget-preview layout-"+layout+" "+(mode==="running"?"is-running":mode==="settings"?"is-settings":"is-idle");
    const top=document.createElement("div");top.className="widget-preview-top";
    const eye=document.createElement("span");eye.className="widget-preview-eye";eye.textContent="◉";
    const brand=document.createElement("strong");brand.textContent="MYRA";
    const status=document.createElement("span");status.className="widget-preview-status";status.textContent=mode==="running"?"EXECUTANDO":mode==="settings"?"PREFERÊNCIAS":"ONLINE";
    top.append(eye,brand,status);host.append(top);
    if(layout==="pill"){host.style.padding="9px 14px";return;}
    host.style.padding=layout==="compact"?"11px":"15px";
    const body=document.createElement("div");body.className="widget-preview-body";
    const heading=document.createElement("b");heading.textContent=mode==="running"?"Executando sua tarefa":mode==="settings"?"Configurações do widget":"Como posso ajudar?";
    const detail=document.createElement("p");detail.textContent=mode==="running"?"Pesquisando informações e verificando cada etapa…":mode==="settings"?"Aparência, comportamento e preferências locais.":"Pronta para conversar ou executar uma tarefa.";
    body.append(heading,detail);
    if(mode==="running"){
      const track=document.createElement("div");track.className="widget-preview-progress";const fill=document.createElement("i");track.append(fill);body.append(track);
      const controls=document.createElement("div");controls.className="widget-preview-controls";["Pausar","Assumir navegador","Cancelar"].forEach((label,i)=>{const b=document.createElement("span");b.textContent=label;b.className=i===2?"danger":"";controls.append(b)});body.append(controls);
    }else if(mode==="settings"){
      const setting=document.createElement("div");setting.className="widget-preview-setting";setting.textContent="Tema · Cor · Tamanho";body.append(setting);
    }else{
      const input=document.createElement("div");input.className="widget-preview-input";input.textContent="Digite uma mensagem…";body.append(input);
    }
    host.append(body);
    $("widget-save-status").dataset.state="";
  }
  function discardWidgetDraft(){
    renderWidgetConfig();$("widget-save-status").textContent="Rascunho descartado. Configuração salva restaurada.";
  }
  function initWidgetStudio(){
    ["widget-accent","widget-opacity","widget-width","widget-height"].forEach(id=>$(id)?.addEventListener("input",()=>{
      const c=widgetDraft();updateWidgetLabels(c);renderWidgetPreview();
      $("widget-save-status").textContent="Prévia atualizada. As mudanças ainda não foram salvas.";
    }));
    $("widget-preview-mode").addEventListener("change",()=>{renderWidgetPreview();$("widget-save-status").textContent="Prévia atualizada. Nada foi salvo."});
    $("widget-preview-layout").addEventListener("change",()=>{renderWidgetPreview();$("widget-save-status").textContent="Formato de prévia alterado. Nada foi salvo."});
    $("widget-apply").addEventListener("click",applyWidgetConfig);
    $("widget-discard").addEventListener("click",discardWidgetDraft);
    $("widget-reset").addEventListener("click",()=>{
      $("widget-accent").value=WIDGET_DEFAULTS.accent;$("widget-opacity").value=WIDGET_DEFAULTS.opacity;
      $("widget-width").value=WIDGET_DEFAULTS.width;$("widget-height").value=WIDGET_DEFAULTS.height;
      updateWidgetLabels(WIDGET_DEFAULTS);renderWidgetPreview();
      $("widget-save-status").textContent="Prévia com os padrões. Salve e aplique para alterar o widget real.";
    });
    renderWidgetConfig();
  }
  function applyAccent(accent){const root=document.documentElement;if(accent==="blue"){root.style.setProperty("--purple","#3b82f6");root.style.setProperty("--cyan","#22d3ee")}else if(accent==="green"){root.style.setProperty("--purple","#10b981");root.style.setProperty("--cyan","#67e8f9")}else{root.style.setProperty("--purple","#8b5cf6");root.style.setProperty("--cyan","#06b6d4")}document.querySelectorAll("[data-accent]").forEach(b=>b.classList.toggle("selected",b.dataset.accent===accent))}
  $("activity-pause").addEventListener("click",()=>runActivityAction("pause"));
  $("activity-resume").addEventListener("click",()=>runActivityAction("resume"));
  $("activity-takeover").addEventListener("click",()=>runActivityAction("takeover"));
  $("activity-cancel").addEventListener("click",()=>runActivityAction("cancel"));
  $("new-chat").addEventListener("click",()=>{createConversation();showView("chat");$("message-input").focus()});$("send-button").addEventListener("click",()=>sendMessage($("message-input").value));$("message-input").addEventListener("input",resizeInput);$("message-input").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendMessage($("message-input").value)}});
  $("mode-toggle").addEventListener("click",()=>{executionMode=!executionMode;const b=$("mode-toggle");b.classList.toggle("is-execution",executionMode);b.setAttribute("aria-pressed",String(executionMode));b.innerHTML=executionMode?"<span>⚡</span> Executar tarefa":"<span>◈</span> Conversa";$("message-input").placeholder=executionMode?"Descreva o que a MYRA deve executar...":"O que vamos construir hoje?"});
  document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));document.addEventListener("click",async e=>{const a=e.target.closest("a[href]");if(!a)return;const href=a.href;if(!(href.startsWith("http://")||href.startsWith("https://")))return;e.preventDefault();try{if(window.__TAURI__?.core?.invoke)await window.__TAURI__.core.invoke("open_external_url",{url:href});else window.open(href,"_blank","noopener,noreferrer")}catch(err){console.error("[EXTERNAL LINK]",err);alert("Não foi possível abrir o link: "+err)}});document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>sendMessage(b.dataset.prompt)));$("settings-button").addEventListener("click",()=>showView("settings"));
  $("select-history").addEventListener("click",()=>{historySelectionMode=!historySelectionMode;if(!historySelectionMode)selectedConversationIds.clear();renderSidebar()});
  $("clear-history").addEventListener("click",()=>{historySelectionMode=true;renderSidebar()});
  $("select-all-history").addEventListener("change",e=>{if(e.target.checked)conversations.forEach(c=>selectedConversationIds.add(c.id));else selectedConversationIds.clear();renderSidebar()});
  $("delete-selected-history").addEventListener("click",()=>deleteConversations([...selectedConversationIds]));
  $("voice-input").addEventListener("click",startVoiceInput);$("voice-read").addEventListener("click",readLastAnswer);$("improve-prompt").addEventListener("click",improvePrompt);
  document.querySelectorAll(".skill-chip").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.skill;if(activeSkills.has(key)){activeSkills.delete(key);button.classList.remove("active")}else{activeSkills.add(key);button.classList.add("active")}}));
  $("plugin-source-add").addEventListener("click",addPluginSource);$("plugin-search").addEventListener("input",renderPlugins);$("plugin-category").addEventListener("change",renderPlugins);
  $("github-refresh").addEventListener("click",refreshGitHub);$("github-fetch").addEventListener("click",()=>githubSync("fetch"));$("github-pull").addEventListener("click",()=>githubSync("pull"));$("github-push").addEventListener("click",()=>githubSync("push"));$("github-export").addEventListener("click",exportWorkspace);
  $("new-project").addEventListener("click",newProject);$("project-search").addEventListener("input",renderProjects);$("code-editor").addEventListener("input",()=>{storeActiveCode();$("editor-status").textContent="Alterações locais";clearTimeout(previewTimer);previewTimer=setTimeout(renderPreview,220)});$("run-preview").addEventListener("click",()=>{renderPreview();$("editor-status").textContent="Preview atualizado"});$("refresh-preview").addEventListener("click",renderPreview);$("expand-preview").addEventListener("click",()=>showView("preview"));$("preview-to-code").addEventListener("click",()=>showView("code"));$("add-file").addEventListener("click",addCodeFile);$("download-code").addEventListener("click",downloadCode);$("import-code").addEventListener("click",()=>$("code-file").click());$("code-file").addEventListener("change",e=>{Array.from(e.target.files||[]).forEach(importCode);e.target.value=""});$("workbench").addEventListener("dragover",e=>{e.preventDefault();$("workbench").classList.add("is-dragging")});$("workbench").addEventListener("dragleave",e=>{if(!e.relatedTarget||!$("workbench").contains(e.relatedTarget))$("workbench").classList.remove("is-dragging")});$("workbench").addEventListener("drop",e=>{e.preventDefault();$("workbench").classList.remove("is-dragging");Array.from(e.dataTransfer?.files||[]).forEach(importCode)});$("refresh-models").addEventListener("click",refreshModels);$("quick-model").addEventListener("change",e=>selectModel(e.target.value));$("settings-model").addEventListener("change",e=>selectModel(e.target.value));
  document.querySelectorAll("[data-integration]").forEach(b=>b.addEventListener("click",()=>{const k=b.dataset.integration;showModal(k==="github"?"GitHub":k==="api"?"Adicionar API":"Arquitetura de plugins",k==="github"?"O repositório privado conectado usa a autenticação GitHub CLI desta máquina. Fetch, pull e push são executados pelo Git local.":k==="api"?"Cadastre um endpoint HTTPS público e teste uma chamada GET real. Tokens são temporários e não ficam armazenados.":"Expansão modular da MYRA.",k)}));
  $("modal-close").addEventListener("click",closeModal);$("modal-cancel").addEventListener("click",closeModal);$("modal-backdrop").addEventListener("click",e=>{if(e.target===$("modal-backdrop"))closeModal()});
  document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();createConversation();showView("chat");$("message-input").focus()}if(e.key==="Escape"&&!busy){closeModal();showView("chat")}});
  renderPlatformIcons();initSetup();setChatActivity(false);setBusy(false);if(!conversations.length)createConversation(false);renderSidebar();renderMessages();renderFiles();loadActiveCode();initSettings();renderProjects();checkBackend();refreshTaskStatus();refreshModels();renderPreview();refreshGitHub();refreshApiIntegrations();renderQueue();initWidgetStudio();renderPlugins();if(!load(SETUP_KEY,{}).completed)showView("setup");setInterval(checkBackend,10000);setInterval(refreshTaskStatus,750);if(messageQueue.length){queueNeedsResume=true;renderQueue();}
})();
/* MYRA LiveOrb — original WebGL shader engine, adapted as a native custom element for Tauri. */
(() => {
  const VERT = "attribute vec2 a_position; void main(){ gl_Position=vec4(a_position,0.0,1.0); }";
  const FRAG = [
    "precision highp float;",
    "uniform vec2 u_resolution; uniform float u_time; uniform float u_speed; uniform vec2 u_look; uniform float u_blink; uniform float u_mode;",
    "uniform vec3 u_body; uniform vec3 u_eye; uniform vec3 u_c1; uniform vec3 u_c2; uniform vec3 u_c3;",
    "float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}",
    "float noise(vec2 p){vec2 i=floor(p),f=fract(p);float a=hash(i),b=hash(i+vec2(1.,0.)),c=hash(i+vec2(0.,1.)),d=hash(i+vec2(1.,1.));vec2 u=f*f*(3.-2.*f);return mix(a,b,u.x)+(c-a)*u.y*(1.-u.x)+(d-b)*u.x*u.y;}",
    "float fbm(vec2 p){float v=0.,a=.5;mat2 m=mat2(1.6,1.2,-1.2,1.6);for(int i=0;i<5;i++){v+=a*noise(p);p=m*p;a*=.5;}return v;}",
    "vec3 orient(vec3 p,vec2 look){float yaw=look.x*.92,pitch=-look.y*.78,cy=cos(yaw),sy=sin(yaw),cp=cos(pitch),sp=sin(pitch);vec3 q=vec3(p.x,p.y*cp-p.z*sp,p.y*sp+p.z*cp);return vec3(q.x*cy+q.z*sy,q.y,-q.x*sy+q.z*cy);}",
    "float eyeMask(vec3 n,vec3 e,vec3 right,vec3 up,float halfH,float rad){float facing=dot(n,e),x=dot(n,right)-dot(e,right),y=dot(n,up)-dot(e,up);y-=clamp(y,-halfH,halfH);float d=length(vec2(x,y))-rad,fill=1.-smoothstep(-.01,.01,d);return fill*smoothstep(.12,.32,facing);}",
    "vec3 wash(vec3 n,float t){vec2 q=n.xy*2.2+n.z*.85;vec2 w1=vec2(fbm(q*1.4+vec2(t*.22,t*.18)),fbm(q*1.4+vec2(-t*.16,t*.24)+4.1));q+=(w1-.5)*.72;float f=fbm(q*2.1+vec2(0.,t*.12)),g=fbm(q*4.6-vec2(t*.2,0.));vec3 col=mix(u_c1,u_c2,smoothstep(.28,.72,f));return mix(col,u_c3,pow(smoothstep(.42,.9,g),1.4));}",
    "void main(){vec2 uv=(gl_FragCoord.xy/u_resolution.xy)*2.-1.;float aspect=u_resolution.x/max(u_resolution.y,1.);uv.x*=aspect;float radius=.94;vec2 p=uv/radius;float r2=dot(p,p);float edge=1.-smoothstep(.985,1.012,sqrt(max(r2,0.)));if(edge<=.001){gl_FragColor=vec4(0.);return;}float z=sqrt(max(1.-r2,0.));vec3 n=normalize(vec3(p,z));vec2 look=u_look;float lm=length(look);if(lm>1.)look/=lm;vec3 right=orient(vec3(1.,0.,0.),look),up=orient(vec3(0.,1.,0.),look),eL=orient(normalize(vec3(-.32,.08,1.)),look),eR=orient(normalize(vec3(.32,.08,1.)),look);float halfH=mix(.23,.014,u_blink),rad=mix(.12,.128,u_blink);float eyes=max(eyeMask(n,eL,right,up,halfH,rad),eyeMask(n,eR,right,up,halfH,rad));vec3 body=u_mode>.5?wash(n,u_time*u_speed):u_body;vec3 col=mix(body,u_eye,clamp(eyes,0.,1.));gl_FragColor=vec4(clamp(col,0.,1.),edge);}"
  ].join("\n");
  const PALETTE = ["#7C6AF7", "#7DD3C7", "#E8B4D4"];
  const AVATAR_KEY = "myra-avatar-settings-v1";
  const DEFAULT_AVATAR = {avatar:"orb",style:"animated",color:"#7C6AF7",eyeColor:"#09090B",c1:"#7C6AF7",c2:"#7DD3C7",c3:"#E8B4D4",size:54};
  function readAvatarConfig(){try{return {...DEFAULT_AVATAR,...JSON.parse(localStorage.getItem(AVATAR_KEY)||"{}")}}catch(_){return {...DEFAULT_AVATAR}}}
  function applyAvatarConfig(config=readAvatarConfig()){
    const value={...DEFAULT_AVATAR,...config};
    document.querySelectorAll("myra-orb").forEach(orb=>{
      orb.dataset.avatarShape=value.avatar;orb.dataset.avatarStyle=value.style;orb.dataset.avatarColor=value.color;orb.dataset.avatarEyeColor=value.eyeColor;
      orb.dataset.avatarC1=value.c1;orb.dataset.avatarC2=value.c2;orb.dataset.avatarC3=value.c3;
    });
    document.documentElement.dataset.myraAvatarStyle=value.style;
    return value;
  }
  const rgb = (hex) => {
    let h = String(hex || "#ffffff").replace("#", "").trim();
    if (h.length === 3) h = h.split("").map(c => c + c).join("");
    const n = parseInt(h.padEnd(6, "0").slice(0, 6), 16);
    return Number.isFinite(n) ? [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255] : [1, 1, 1];
  };
  const darkTheme = () => {
    const root = document.documentElement;
    if (root.classList.contains("dark") || root.dataset.theme === "dark") return true;
    if (root.classList.contains("light") || root.dataset.theme === "light") return false;
    return !!window.matchMedia?.("(prefers-color-scheme: dark)").matches;
  };
  function renderStepTracker(host, status = {}, options = {}) {
    if (!host) return;
    const state = String(status.state || "idle").toLowerCase();
    const history = Array.isArray(status.historico) ? status.historico : [];
    const running = ["running", "paused", "pausado"].includes(state);
    if (!running && !["done", "error"].includes(state)) { host.hidden = true; host.replaceChildren(); return; }
    host.hidden = false;
    const current = String(status.passo_atual || (state === "done" ? "Tarefa concluída" : state === "error" ? "Tarefa interrompida" : "Preparando próxima etapa")).replace(/\s+/g, " ").trim();
    const num = Math.max(0, Number(status.passo_num) || history.length);
    const total = Math.max(0, Number(status.passo_total) || Number(status.max_passos) || 0);
    host.replaceChildren(); host.classList.toggle("step-tracker-compact", !!options.compact);
    const top = document.createElement("div"); top.className = "step-tracker-top";
    const heading = document.createElement("strong"); heading.textContent = state === "done" ? "Etapas concluídas" : state === "error" ? "Execução interrompida" : state === "paused" || state === "pausado" ? "Execução pausada" : "MYRA está trabalhando";
    const count = document.createElement("span"); count.textContent = total ? num + " / " + total : num + " etapa(s)"; top.append(heading, count);
    const bar = document.createElement("div"); bar.className = "step-tracker-bar";
    const fill = document.createElement("i"); fill.style.width = (state === "done" ? 100 : total ? Math.min(100, Math.round(num / total * 100)) : 0) + "%"; bar.append(fill);
    const list = document.createElement("ol"); list.className = "step-tracker-list";
    history.slice(-3).forEach(item => {
      const li = document.createElement("li"); li.className = "is-complete";
      const dot = document.createElement("i"), label = document.createElement("span");
      const raw = typeof item === "string" ? item : (item?.passo_atual || item?.tool || item?.name || item?.acao || item?.description || item?.resultado || JSON.stringify(item));
      label.textContent = String(raw).replace(/\s+/g, " ").trim().slice(0, 120) || "Etapa concluída"; li.append(dot, label); list.append(li);
    });
    if (running) { const li = document.createElement("li"); li.className = "is-current"; const dot = document.createElement("i"), label = document.createElement("span"); label.textContent = current.slice(0, 120); li.append(dot, label); list.append(li); }
    if (!list.children.length) { const li = document.createElement("li"); li.className = state === "done" ? "is-complete" : "is-current"; li.textContent = current; list.append(li); }
    host.append(top, bar, list);
  }
  class MyraOrb extends HTMLElement {
    connectedCallback() {
      if (this._mounted) return; this._mounted = true;
      this.setAttribute("role", "img"); this.setAttribute("aria-label", "MYRA LiveOrb");
      this.style.position = "relative"; this.style.display = "inline-block"; this.style.flex = "none";
      const size = this.dataset.size || getComputedStyle(this).width || "64px";
      this.style.width = size; this.style.height = size;
      this.innerHTML = '<div class="live-orb-fallback" aria-hidden="true"><i></i><i></i></div><canvas aria-hidden="true"></canvas>';
      const canvas = this.querySelector("canvas"), fallback = this.querySelector(".live-orb-fallback");
      const opts = { variant: this.dataset.variant || "webgl", theme: "auto", colors: PALETTE, interactive: true, blink: true };
      let gl = canvas.getContext("webgl", {alpha:true,antialias:false,depth:false,stencil:false,premultipliedAlpha:false,powerPreference:"high-performance"});
      if (!gl) { this.dataset.webgl = "fallback"; return; }
      const shader = (type, source) => { const s = gl.createShader(type); if (!s) return null; gl.shaderSource(s, source); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.error("[MYRA LiveOrb] Shader compile:", gl.getShaderInfoLog(s)); gl.deleteShader(s); return null; } return s; };
      let vs=null, fs=null, program=null, buf=null, u={};
      const initGl=()=>{
        vs=shader(gl.VERTEX_SHADER,VERT);fs=shader(gl.FRAGMENT_SHADER,FRAG);program=gl.createProgram();
        if(!vs||!fs||!program)return false;
        gl.attachShader(program,vs);gl.attachShader(program,fs);gl.linkProgram(program);
        if(!gl.getProgramParameter(program,gl.LINK_STATUS)){console.error("[MYRA LiveOrb] Program link:",gl.getProgramInfoLog(program));return false;}
        gl.useProgram(program);buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);
        gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
        const loc=gl.getAttribLocation(program,"a_position");gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
        u={};["u_resolution","u_time","u_speed","u_look","u_blink","u_mode","u_body","u_eye","u_c1","u_c2","u_c3"].forEach(k=>u[k]=gl.getUniformLocation(program,k));
        gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);return true;
      };
      if(!initGl()){this.dataset.webgl="fallback";return;}
      gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
      const look={x:0,y:.08}, target={x:0,y:.08}, glance={x:0,y:.08};
      let raf=0, dead=false, lost=false, visible=true, clock=0, last=0, pointerAt=-Infinity, nextBlink=1800+Math.random()*2400, blinkAt=-10000, nextGlance=600+Math.random()*900;
      const reduced=window.matchMedia("(prefers-reduced-motion: reduce)");
      const resize=()=>{ const r=this.getBoundingClientRect(), dpr=Math.min(devicePixelRatio||1,2); if(!r.width||!r.height)return false; const w=Math.max(1,Math.floor(r.width*dpr)),h=Math.max(1,Math.floor(r.height*dpr)); if(canvas.width===w&&canvas.height===h)return false; canvas.width=w;canvas.height=h;gl.viewport(0,0,w,h);return true; };
      const wake=()=>{if(!raf&&!dead&&!lost){last=performance.now();raf=requestAnimationFrame(tick);}};
      const draw=now=>{
        raf=0;if(dead||lost)return;
        const dt=Math.min(50,Math.max(0,now-last));last=now;
        const live=visible&&!reduced.matches&&document.visibilityState!=="hidden";if(live)clock+=dt;
        const steering=opts.interactive&&now-pointerAt<3000;
        if(!steering&&live&&clock>=nextGlance){const back=Math.random()<.3;glance.x=back?0:(Math.random()*2-1)*.8;glance.y=back?.08:(Math.random()*2-1)*.5;nextGlance=clock+900+Math.random()*2100;}
        const goal=steering?target:(reduced.matches?{x:0,y:.08}:glance),ease=live?(steering?.16:.1):1;
        look.x+=(goal.x-look.x)*ease;look.y+=(goal.y-look.y)*ease;
        if(!reduced.matches&&opts.blink&&clock>=nextBlink){blinkAt=clock;nextBlink=clock+2200+Math.random()*3800;}
        const bt=(clock-blinkAt)/1000;let b=0;if(!reduced.matches&&opts.blink){if(bt<.055)b=bt/.055;else if(bt<.1)b=1;else if(bt<.18)b=1-(bt-.1)/.08;}
        const dark=darkTheme(), style=this.dataset.avatarStyle||"animated", mode=style==="animated"?1:0;
        const body=rgb(this.dataset.avatarColor||(dark?"#F4F4F5":"#18181B"));
        const eye=rgb(this.dataset.avatarEyeColor||(dark?"#09090B":"#F4F4F5"));
        const pal=[this.dataset.avatarC1||PALETTE[0],this.dataset.avatarC2||PALETTE[1],this.dataset.avatarC3||PALETTE[2]].map(rgb);
        gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);
        gl.uniform2f(u.u_resolution,canvas.width,canvas.height);gl.uniform1f(u.u_time,reduced.matches?0:clock/1000);gl.uniform1f(u.u_speed,reduced.matches?0:.55);
        gl.uniform2f(u.u_look,look.x,look.y);gl.uniform1f(u.u_blink,b);gl.uniform1f(u.u_mode,mode);
        gl.uniform3f(u.u_body,...body);gl.uniform3f(u.u_eye,...eye);
        gl.uniform3f(u.u_c1,...(pal[0]||rgb(PALETTE[0])));gl.uniform3f(u.u_c2,...(pal[1]||rgb(PALETTE[1])));gl.uniform3f(u.u_c3,...(pal[2]||rgb(PALETTE[2])));
        gl.drawArrays(gl.TRIANGLES,0,6);
        if(live&&!dead)raf=requestAnimationFrame(tick);
      };
      const tick=now=>draw(now);
      const steer=(x,y)=>{if(!opts.interactive)return;const r=this.getBoundingClientRect();if(!r.width||!r.height)return;target.x=Math.max(-1,Math.min(1,(x-(r.left+r.width/2))/(r.width/2)));target.y=Math.max(-1,Math.min(1,(r.top+r.height/2-y)/(r.height/2)));pointerAt=performance.now();wake();};
      const onMove=e=>steer(e.clientX,e.clientY);
      // Native cursor polling feeds the same eye steering even when the cursor is
      // outside this transparent/compact Tauri window (WebView pointer events stop at its edge).
      this._trackGlobalCursor=(dx,dy)=>{const dpr=window.devicePixelRatio||1;const r=this.getBoundingClientRect();const x=window.innerWidth/2+Number(dx||0)/dpr;const y=window.innerHeight/2+Number(dy||0)/dpr;steer(x,y);};
      const onLost=e=>{e.preventDefault();lost=true;cancelAnimationFrame(raf);raf=0;canvas.style.visibility="hidden";this.dataset.webgl="lost";};
      const onRestored=()=>{if(dead)return;if(!initGl()){this.dataset.webgl="fallback";return;}lost=false;canvas.style.visibility="";this.dataset.webgl="ready";resize();wake();};
      const ro=new ResizeObserver(()=>{if(resize())wake();});ro.observe(this);
      const io=new IntersectionObserver(([entry])=>{visible=entry?.isIntersecting??true;wake();});io.observe(this);
      window.addEventListener("pointermove",onMove,{passive:true});document.addEventListener("visibilitychange",wake);
      reduced.addEventListener("change",wake);canvas.addEventListener("webglcontextlost",onLost);canvas.addEventListener("webglcontextrestored",onRestored);
      this._destroy=()=>{dead=true;cancelAnimationFrame(raf);ro.disconnect();io.disconnect();window.removeEventListener("pointermove",onMove);document.removeEventListener("visibilitychange",wake);reduced.removeEventListener("change",wake);canvas.removeEventListener("webglcontextlost",onLost);canvas.removeEventListener("webglcontextrestored",onRestored);gl.getExtension("WEBGL_lose_context")?.loseContext();};
      resize();this.dataset.webgl="ready";fallback.hidden=true;wake();
      this._setOrbState = state => { this.dataset.state=state||"idle"; };
    }
    disconnectedCallback(){this._destroy?.();this._mounted=false;}
  }
  if (!customElements.get("myra-orb")) customElements.define("myra-orb", MyraOrb);
  window.MyraUI = window.MyraUI || {}; window.MyraUI.renderStepTracker = renderStepTracker; window.MyraUI.applyAvatarConfig = applyAvatarConfig; window.MyraUI.readAvatarConfig = readAvatarConfig;
  document.addEventListener("DOMContentLoaded",()=>applyAvatarConfig());
  window.addEventListener("storage",event=>{if(event.key===AVATAR_KEY)applyAvatarConfig();});
  const avatarChannel=typeof BroadcastChannel!=="undefined"?new BroadcastChannel("myra-avatar-sync"):null;
  avatarChannel?.addEventListener("message",event=>{if(event.data?.type==="avatar-config")applyAvatarConfig(event.data.config||readAvatarConfig());});
})();
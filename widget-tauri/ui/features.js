// ============================================================
// MYRA Widget - features.js CONSOLIDADO
// Popover + Tema + Som + Compacto + DND + Fixar + Cor +
// Opacidade + Particulas + Confete + VRAM + Cursor tracking
// ============================================================

const _invoke = window.__TAURI__.core.invoke;

// ---------- Estado ----------
const state = {
    theme:   localStorage.getItem('myra-theme')   || 'dark',
    sound:   localStorage.getItem('myra-sound')   !== 'off',
    compact: localStorage.getItem('myra-compact') === 'on',
    dnd:     localStorage.getItem('myra-dnd')     === 'on',
    onTop:   localStorage.getItem('myra-ontop')   !== 'off',
    color:   localStorage.getItem('myra-color')   || '#6366f1',
};

// ---------- Tamanhos ----------
const SZ = {
    idle:     { w: 220, h: 44  },
    compact:  { w: 90,  h: 44  },
    settings: { w: 340, h: 400 },
    card:     { w: 440, h: 340 },
};

async function applyWindowSize(mode) {
    const compact = document.body.dataset.compact === 'on';
    let s;
    if (mode === 'idle')          s = compact ? SZ.compact : SZ.idle;
    else if (mode === 'settings') s = SZ.settings;
    else                          s = SZ.card;
    setTimeout(() => {
        _invoke('resize_window', { width: s.w, height: s.h }).catch(() => {});
    }, 320);
}

// ---------- Tema ----------
function applyTheme() {
    document.body.dataset.theme = state.theme;
    const btn = document.getElementById('btn-theme');
    if (btn) btn.classList.toggle('active', state.theme === 'light');
}

// ---------- Cor ----------
function shadeHex(hex, pct) {
    const n = parseInt(hex.replace('#',''), 16);
    const r = Math.min(255, ((n >> 16) & 255) + pct);
    const g = Math.min(255, ((n >> 8)  & 255) + pct);
    const b = Math.min(255, (n & 255)        + pct);
    return '#' + [r,g,b].map(v => v.toString(16).padStart(2,'0')).join('');
}
function applyColor() {
    document.documentElement.style.setProperty('--myra-accent', state.color);
    document.documentElement.style.setProperty('--myra-accent-2', shadeHex(state.color, 25));
    const input = document.getElementById('mascot-color');
    if (input) input.value = state.color;
}

// ---------- Compacto ----------
function applyCompact() {
    document.body.dataset.compact = state.compact ? 'on' : 'off';
    const btn = document.getElementById('btn-compact');
    if (btn) btn.classList.toggle('active', state.compact);
}

// ---------- DND ----------
function applyDnd() {
    const btn = document.getElementById('btn-dnd');
    if (btn) btn.classList.toggle('active', state.dnd);
}

// ---------- Sempre no topo ----------
async function applyOnTop() {
    const btn = document.getElementById('btn-top');
    if (btn) btn.classList.toggle('active', state.onTop);
    try {
        await _invoke('toggle_always_on_top', { onTop: state.onTop });
    } catch (e) { /* silencio */ }
}

// ---------- Sons ----------
let audioCtx = null;
function playSound(kind) {
    if (!state.sound || state.dnd) return;
    try {
        if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const now = audioCtx.currentTime;
        const notes = {
            pop:   [{ f: 660, t: 0.00, d: 0.10 }],
            chime: [{ f: 523, t: 0.00, d: 0.15 }, { f: 784, t: 0.12, d: 0.20 }],
            error: [{ f: 220, t: 0.00, d: 0.20 }, { f: 165, t: 0.15, d: 0.25 }],
        }[kind] || [];
        notes.forEach(n => {
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.type = 'sine';
            osc.frequency.value = n.f;
            gain.gain.setValueAtTime(0.0001, now + n.t);
            gain.gain.exponentialRampToValueAtTime(0.15, now + n.t + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + n.t + n.d);
            osc.connect(gain); gain.connect(audioCtx.destination);
            osc.start(now + n.t);
            osc.stop(now + n.t + n.d + 0.02);
        });
    } catch (e) { /* silencio */ }
}

// ---------- Confete ----------
function fireConfetti() {
    if (state.dnd) return;
    const layer = document.getElementById('confetti-layer');
    if (!layer) return;
    const colors = [state.color, '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];
    for (let i = 0; i < 40; i++) {
        const p = document.createElement('div');
        p.className = 'confetti-piece';
        p.style.left = Math.random() * 100 + '%';
        p.style.top  = '-10px';
        p.style.background = colors[i % colors.length];
        p.style.animationDuration = (1.2 + Math.random() * 1.2) + 's';
        p.style.animationDelay = (Math.random() * 0.3) + 's';
        p.style.transform = 'rotate(' + (Math.random()*360) + 'deg)';
        layer.appendChild(p);
        setTimeout(() => p.remove(), 3000);
    }
}

// ---------- Particulas ----------
const particles = {
    canvas: null, ctx: null, list: [],
    init() {
        this.canvas = document.getElementById('particles');
        if (!this.canvas) return;
        this.ctx = this.canvas.getContext('2d');
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.loop();
    },
    resize() {
        if (!this.canvas) return;
        this.canvas.width  = window.innerWidth;
        this.canvas.height = window.innerHeight;
    },
    burst() {
        if (state.dnd) return;
        const cx = window.innerWidth / 2;
        const cy = window.innerHeight / 2;
        for (let i = 0; i < 30; i++) {
            const a = (Math.PI * 2 * i) / 30;
            const sp = 1.5 + Math.random() * 2.5;
            this.list.push({
                x: cx, y: cy,
                vx: Math.cos(a) * sp,
                vy: Math.sin(a) * sp,
                life: 1.0,
                color: state.color,
            });
        }
    },
    loop() {
        if (!this.ctx) return;
        const { ctx, canvas } = this;
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        for (let i = this.list.length - 1; i >= 0; i--) {
            const p = this.list[i];
            p.x += p.vx; p.y += p.vy; p.vy += 0.08;
            p.life -= 0.02;
            if (p.life <= 0) { this.list.splice(i, 1); continue; }
            ctx.globalAlpha = p.life;
            ctx.fillStyle = p.color;
            ctx.beginPath();
            ctx.arc(p.x, p.y, 2.5, 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;
        requestAnimationFrame(() => this.loop());
    }
};

// ---------- VRAM ----------
async function pollGpu() {
    try {
        const info = await _invoke('get_gpu_info');
        if (!info || !info.ok) return;
        const txt = document.getElementById('gpu-text');
        const fill = document.getElementById('gpu-fill');
        if (txt)  txt.textContent = info.used + '/' + info.total + ' MB';
        if (fill) fill.style.width = Math.min(100, (info.used / info.total) * 100) + '%';
    } catch (e) { /* silencio */ }
}

// ---------- Cursor tracking (olhos seguem mouse global) ----------
let _eyeLerp = { ox: 0, oy: 0 };

async function trackGlobalCursor() {
    try {
        const pos = await _invoke('get_cursor_relative_to_window');
        if (!pos || !pos.ok) return;

        const maxOffset = 3.5;
        const dist = Math.max(1, pos.dist || 1);
        const factor = Math.min(dist / 200, 1);
        const rawOx = (pos.dx / dist) * maxOffset * factor;
        const rawOy = (pos.dy / dist) * maxOffset * factor;

        _eyeLerp.ox = _eyeLerp.ox * 0.65 + rawOx * 0.35;
        _eyeLerp.oy = _eyeLerp.oy * 0.65 + rawOy * 0.35;

        document.querySelectorAll('.mascot:not(.done):not(.error):not(.sleeping)').forEach(m => {
            m.querySelectorAll('.eye').forEach(eye => {
                eye.style.transform = "translate(" + _eyeLerp.ox.toFixed(2) + "px, " + _eyeLerp.oy.toFixed(2) + "px)";
            });
        });
    } catch (e) { /* silencio */ }
}

// ---------- Hooks ----------
window.myraOnDone = function() {
    playSound('chime');
    fireConfetti();
    particles.burst();
    setTimeout(() => {
        _invoke('resize_window', { width: 440, height: 340 }).catch(() => {});
    }, 350);
};
window.myraOnError = function() {
    playSound('error');
    setTimeout(() => {
        _invoke('resize_window', { width: 440, height: 340 }).catch(() => {});
    }, 350);
};

// ---------- Abrir/fechar settings ----------
function openSettings() {
    const island = document.getElementById('island');
    if (!island) return;
    island.dataset.prevState = island.classList.contains('idle') ? 'idle' :
                               island.classList.contains('running') ? 'running' :
                               island.classList.contains('done') ? 'done' : 'error';
    island.classList.remove('idle','running','done','error');
    island.classList.add('settings');
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const v = document.querySelector('.view-settings');
    if (v) v.classList.add('active');
    applyWindowSize('settings');
    playSound('pop');
}

function closeSettings() {
    const island = document.getElementById('island');
    if (!island) return;
    const prev = island.dataset.prevState || 'idle';
    island.classList.remove('settings');
    island.classList.add(prev);
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const v = document.querySelector('.view-' + prev);
    if (v) v.classList.add('active');
    applyWindowSize(prev === 'idle' ? 'idle' : 'card');
}

// ---------- Binds ----------
function bindButtons() {
    // Engrenagem -> abre settings
    document.getElementById('btn-open-settings')?.addEventListener('click', (e) => {
        e.stopPropagation();
        openSettings();
    });

    // Botao voltar -> fecha settings
    document.getElementById('btn-back-settings')?.addEventListener('click', (e) => {
        e.stopPropagation();
        closeSettings();
    });

    // Botao fechar widget -> fecha app
    document.getElementById('btn-close-widget')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        await _invoke('cancel_task').catch(() => {});
        window.__TAURI__.window.getCurrentWindow().close();
    });

    // Tema
    document.getElementById('btn-theme')?.addEventListener('click', (e) => {
        e.stopPropagation();
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('myra-theme', state.theme);
        applyTheme(); playSound('pop');
    });

    // Som
    document.getElementById('btn-sound')?.addEventListener('click', (e) => {
        e.stopPropagation();
        state.sound = !state.sound;
        localStorage.setItem('myra-sound', state.sound ? 'on' : 'off');
        const b = document.getElementById('btn-sound');
        if (b) {
            b.classList.toggle('active', state.sound);
            b.innerHTML = state.sound ? '&#128266; Som' : '&#128263; Som';
        }
        if (state.sound) playSound('pop');
    });

    // Compacto
    document.getElementById('btn-compact')?.addEventListener('click', (e) => {
        e.stopPropagation();
        state.compact = !state.compact;
        localStorage.setItem('myra-compact', state.compact ? 'on' : 'off');
        applyCompact(); playSound('pop');
    });

    // DND
    document.getElementById('btn-dnd')?.addEventListener('click', (e) => {
        e.stopPropagation();
        state.dnd = !state.dnd;
        localStorage.setItem('myra-dnd', state.dnd ? 'on' : 'off');
        applyDnd(); playSound('pop');
    });

    // Fixar no topo
    document.getElementById('btn-top')?.addEventListener('click', async (e) => {
        e.stopPropagation();
        state.onTop = !state.onTop;
        localStorage.setItem('myra-ontop', state.onTop ? 'on' : 'off');
        await applyOnTop(); playSound('pop');
    });

    // Cor do mascote
    document.getElementById('mascot-color')?.addEventListener('input', (e) => {
        state.color = e.target.value;
        localStorage.setItem('myra-color', state.color);
        applyColor();
    });
}

// ---------- Opacidade ----------
function setupOpacity() {
    const el = document.getElementById('opacity');
    const island = document.getElementById('island');
    if (!el || !island) return;
    const saved = localStorage.getItem('myra-opacity') || '100';
    el.value = saved;
    island.style.opacity = saved / 100;
    el.addEventListener('input', () => {
        island.style.opacity = el.value / 100;
        localStorage.setItem('myra-opacity', el.value);
    });
}

// ---------- Resize hook ----------
window.__myraResize = function(mode) {
    if (mode) applyWindowSize(mode);
    else {
        const island = document.getElementById('island');
        if (!island) return;
        if (island.classList.contains('settings')) applyWindowSize('settings');
        else if (island.classList.contains('idle')) applyWindowSize('idle');
        else applyWindowSize('card');
    }
};

// ---------- Init ----------
window.addEventListener('DOMContentLoaded', () => {
    applyTheme();
    applyColor();
    applyCompact();
    applyDnd();
    applyOnTop();
    bindButtons();
    setupOpacity();
    particles.init();

    const sb = document.getElementById('btn-sound');
    if (sb) {
        sb.classList.toggle('active', state.sound);
        sb.innerHTML = state.sound ? '&#128266; Som' : '&#128263; Som';
    }

    setTimeout(() => applyWindowSize('idle'), 200);

    // VRAM a cada 30s
    pollGpu();
    setInterval(pollGpu, 30000);

    // Cursor tracking a cada 60ms (~16 fps)
    setInterval(trackGlobalCursor, 60);
});
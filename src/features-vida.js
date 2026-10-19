// ============================================================
// MYRA Widget - PACOTE VIDA
// Mascote vivo: dorme, boceja, brinca, reage a hora do dia,
// muda de humor conforme tasks
// ============================================================

const _vida = {
    lastInteraction: Date.now(),
    sleeping: false,
    playfulTimeout: null,
};

const VIDA_CONFIG = {
    SLEEP_AFTER_MS: 2 * 60 * 1000,
    YAWN_INTERVAL_MS: 5 * 60 * 1000,
    PLAYFUL_MS: 3000,
    CHECK_INTERVAL_MS: 5000,
};

// ============================================================
// Frases por hora
// ============================================================
function getGreeting() {
    const h = new Date().getHours();
    if (h >= 5 && h < 12)  return ['Bom dia! \u2600\uFE0F', 'Acordei!', 'Bora trabalhar!'];
    if (h >= 12 && h < 18) return ['Boa tarde! \u{1F324}\uFE0F', 'To aqui!', 'Manda a task!'];
    if (h >= 18 && h < 23) return ['Boa noite! \u{1F306}', 'Ainda acordado?', 'To de plantao!'];
    return ['Boa madrugada! \u{1F319}', 'Nao dorme?', 'To aqui!'];
}

const VIDA_PHRASES = {
    idle:    ['Oi! \u{1F44B}', 'Pronto!', 'To aqui!', 'Manda ver!', 'E ai?', 'Tudo certo?', 'Bora! \u{1F680}'],
    playful: ['Hehe! \u{1F604}', 'De novo!', 'Uhuu!', 'Gira!', 'Yay! \u{1F389}'],
};

// ============================================================
// Mascote visivel
// ============================================================
function getVisibleMascot() {
    const island = document.getElementById('island');
    if (!island) return null;
    if (island.classList.contains('idle'))     return document.querySelector('.view-idle .mascot');
    if (island.classList.contains('running'))  return document.querySelector('.view-running .mascot');
    if (island.classList.contains('done'))     return document.querySelector('.view-done .mascot');
    if (island.classList.contains('error'))    return document.querySelector('.view-error .mascot');
    return null;
}

function speak(text, durationMs = 2500) {
    const m = getVisibleMascot();
    if (!m) return;
    const speech = m.querySelector('.speech');
    if (!speech) return;
    speech.textContent = text;
    speech.classList.add('show');
    clearTimeout(speech._vidaTimeout);
    speech._vidaTimeout = setTimeout(() => {
        speech.classList.remove('show');
    }, durationMs);
}

function markInteraction() {
    _vida.lastInteraction = Date.now();
    if (_vida.sleeping) wakeUp();
}

function wakeUp() {
    _vida.sleeping = false;
    const m = getVisibleMascot();
    if (m) m.classList.remove('sleeping');
    const g = getGreeting();
    speak(g[Math.floor(Math.random() * g.length)]);
}

function sleep() {
    if (_vida.sleeping) return;
    _vida.sleeping = true;
    const m = getVisibleMascot();
    if (m) {
        m.classList.add('sleeping');
        m.classList.remove('playful', 'yawning');
    }
}

function yawn() {
    if (_vida.sleeping) return;
    const m = getVisibleMascot();
    if (!m) return;
    m.classList.add('yawning');
    setTimeout(() => m.classList.remove('yawning'), 1500);
}

function bePlayful() {
    const m = getVisibleMascot();
    if (!m) return;
    m.classList.add('playful');
    speak(VIDA_PHRASES.playful[Math.floor(Math.random() * VIDA_PHRASES.playful.length)]);
    clearTimeout(_vida.playfulTimeout);
    _vida.playfulTimeout = setTimeout(() => m.classList.remove('playful'), VIDA_CONFIG.PLAYFUL_MS);
}

function setMood(kind) {
    const m = getVisibleMascot();
    if (!m) return;
    m.classList.remove('mood-happy', 'mood-sad');
    if (kind === 'done')  m.classList.add('mood-happy');
    if (kind === 'error') m.classList.add('mood-sad');
    setTimeout(() => m.classList.remove('mood-happy', 'mood-sad'), 5000);
}

function vidaLoop() {
    const idle = Date.now() - _vida.lastInteraction;
    if (!_vida.sleeping && idle > VIDA_CONFIG.SLEEP_AFTER_MS) sleep();

    const island = document.getElementById('island');
    if (island && island.classList.contains('idle') && !_vida.sleeping) {
        if (Math.random() < 0.05) {
            const g = getGreeting();
            const all = [...VIDA_PHRASES.idle, ...g];
            speak(all[Math.floor(Math.random() * all.length)]);
        }
    }
}

// ============================================================
// Duplo clique -> brincalhao
// ============================================================
function setupDoubleClick() {
    document.querySelectorAll('.mascot').forEach(m => {
        m.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            markInteraction();
            bePlayful();
        });
    });
}

function setupInteractionWatcher() {
    const island = document.getElementById('island');
    if (island) {
        island.addEventListener('mouseenter', () => markInteraction());
        island.addEventListener('click', () => markInteraction());
    }
}

// ============================================================
// Hooks
// ============================================================
const _origOnDone = window.myraOnDone;
window.myraOnDone = function() {
    if (_origOnDone) _origOnDone();
    setMood('done');
    markInteraction();
    speak('Feito! \u2705', 3000);
};

const _origOnError = window.myraOnError;
window.myraOnError = function() {
    if (_origOnError) _origOnError();
    setMood('error');
    markInteraction();
    speak('Ops! \u{1F605}', 3000);
};

// ============================================================
// Init
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
    setInterval(yawn, VIDA_CONFIG.YAWN_INTERVAL_MS);
    setInterval(vidaLoop, VIDA_CONFIG.CHECK_INTERVAL_MS);

    setupDoubleClick();
    setupInteractionWatcher();

    setTimeout(() => {
        const g = getGreeting();
        speak(g[Math.floor(Math.random() * g.length)], 3500);
    }, 3000);
});
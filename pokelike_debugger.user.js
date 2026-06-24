// ==UserScript==
// @name         Pokelike Debugger Bridge
// @namespace    https://pokelike.xyz/
// @version      1.2.0
// @description  Relie le jeu Pokelike à l'application Pokelike Debugger
// @author       Pokelike Debugger
// @match        https://pokelike.xyz/*
// @match        https://www.pokelike.xyz/*
// @include      *pokelike.xyz*
// @run-at       document-start
// @grant        unsafeWindow
// ==/UserScript==

// @grant unsafeWindow places this script in Tampermonkey's sandbox so the
// WebSocket is NOT subject to the page's CSP. unsafeWindow gives access to
// the page's JS globals (state, getPokedollars…).

(function () {
    'use strict';

    const win      = unsafeWindow;
    const WS_URL   = 'ws://127.0.0.1:9223';
    const RETRY_MS = 3000;

    let ws = null;

    // ------------------------------------------------------------------
    // Visual badge — visible in the page corner regardless of console setup
    // ------------------------------------------------------------------

    let _badge = null;

    function showBadge(text, color) {
        if (!_badge) {
            _badge = document.createElement('div');
            _badge.id = '__pkd_badge';
            Object.assign(_badge.style, {
                position:      'fixed',
                bottom:        '8px',
                right:         '8px',
                zIndex:        '99999',
                padding:       '4px 10px',
                borderRadius:  '6px',
                fontSize:      '11px',
                fontFamily:    'monospace',
                opacity:       '0.85',
                pointerEvents: 'none',
                color:         '#fff',
            });
        }
        _badge.textContent = '🔌 ' + text;
        _badge.style.background = color;
        if (document.body && !document.body.contains(_badge)) {
            document.body.appendChild(_badge);
        }
    }

    function attachBadge() {
        showBadge('Script chargé — connexion…', '#888');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', attachBadge);
    } else {
        attachBadge();
    }

    // ------------------------------------------------------------------
    // Game state
    // ------------------------------------------------------------------

    // ------------------------------------------------------------------
    // WebSocket
    // ------------------------------------------------------------------

    function send(obj) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(obj));
        }
    }

    function connect() {
        ws = new WebSocket(WS_URL);

        ws.onopen = function () {
            showBadge('Connecté', '#2ecc71');
        };

        ws.onmessage = function (event) {
            let msg;
            try { msg = JSON.parse(event.data); } catch { return; }

            if (msg.type !== 'eval') return;

            try {
                const result = win.eval(msg.code);
                if (result && typeof result.then === 'function') {
                    result
                        .then(v  => send({ type: 'result', id: msg.id, value: v  }))
                        .catch(e => send({ type: 'result', id: msg.id, error: e.message }));
                } else {
                    send({ type: 'result', id: msg.id, value: result });
                }
            } catch (e) {
                send({ type: 'result', id: msg.id, error: e.message });
            }
        };

        ws.onclose = function () {
            showBadge('Déconnecté — reconnexion…', '#e74c3c');
            setTimeout(connect, RETRY_MS);
        };

        ws.onerror = function () { /* onclose fires too */ };
    }

    connect();
})();

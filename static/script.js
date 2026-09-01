let tabCorrente = 'peggiori';
let periodoCorrente = '3m';
let categoriaCorrente = 'indici_globali';
let pollingTimer = null;

const STRATEGIE_INFO = {
    'mean_reversion': {
        'icona': '📉',
        'titolo': 'Mean Reversion (Ritorno alla Media)',
        'descrizione': 'Titoli famosi che sono crollati oltre il 10% negli ultimi 6 mesi. La teoria dice che il prezzo tende a tornare verso la media storica. Questi potrebbero essere opportunità di acquisto a sconto, ma attenzione alle "value trap" (aziende che crollano per problemi reali).'
    },
    'momentum': {
        'icona': '📈',
        'titolo': 'Momentum (Segui il Trend)',
        'descrizione': 'Titoli in forte crescita (oltre +15% in 6 mesi). La strategia momentum sfrutta la tendenza dei mercati a continuare nella stessa direzione. Ideale per investimenti a breve-medio termine, ma attenzione alle bolle speculative.'
    },
    'contrarian': {
        'icona': '🔄',
        'titolo': 'Contrarian (Vai Contro il Mercato)',
        'descrizione': 'Indici e mercati emergenti in forte difficoltà negli ultimi 3 mesi. Quando tutti vendono in preda al panico, spesso è il momento migliore per comprare a sconto. Strategia ad alto rischio ma con potenziali rendimenti elevati.'
    },
    'flight_quality': {
        'icona': '🛡️',
        'titolo': 'Flight to Quality (Rifugio Sicuro)',
        'descrizione': 'Le mega-cap che resistono alle correzioni di mercato. Quando i mercati sono volatili, i capitali istituzionali si spostano verso queste aziende solide. Ideale per proteggere il capitale nei periodi di incertezza.'
    }
};

const CATEGORIE_NOMI = {
    'indici_globali': 'Indici Globali',
    'mercati_emergenti': 'Mercati Emergenti',
    'top_100_usa': 'Top 100 USA',
    'aziende_emergenti': 'Aziende Emergenti',
    'materie_prime': 'Materie Prime',
    'crypto_top': 'Crypto Top',
    'etf_settoriali': 'ETF Settoriali'
};

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    controllaStato();
});

function setupEventListeners() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => cambiaTab(btn.dataset.tab));
    });
    
    document.querySelectorAll('.period-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.period-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            periodoCorrente = this.dataset.periodo;
            caricaDati();
        });
    });
    
    const catSelect = document.getElementById('categoria-select');
    if (catSelect) {
        catSelect.addEventListener('change', function() {
            categoriaCorrente = this.value;
            caricaDati();
        });
    }
}

function creaLinkEsterno(ticker) {
    // Pulisce il ticker per Yahoo Finance
    let yahooTicker = ticker;
    if (ticker.includes('/USD')) {
        // Per crypto e forex, usa un link diverso
        const base = ticker.replace('/USD', '');
        return `https://www.google.com/finance/quote/${base}-USD`;
    }
    if (ticker.startsWith('^')) {
        yahooTicker = ticker.replace('^', '%5E');
    }
    return `https://finance.yahoo.com/quote/${yahooTicker}`;
}

function linkTicker(ticker, nome) {
    return `<a href="${creaLinkEsterno(ticker)}" target="_blank" class="ticker-link" title="Apri grafico su Yahoo Finance">${ticker}</a>`;
}

async function controllaStato() {
    const contenuto = document.getElementById('contenuto');
    
    try {
        const response = await fetch('/api/status');
        const stato = await response.json();

        if (stato.fascia_attiva === false && !stato.completato) {
            contenuto.innerHTML = `
                <div class="loading">
                    <div style="font-size: 2em; margin-bottom: 20px;">🌙</div>
                    <p style="font-size: 1.2em; margin-bottom: 10px;">Fascia notturna</p>
                    <p style="color: #666; font-size: 0.95em;">
                        I dati vengono aggiornati solo tra le 09:00 e le 21:00.<br>
                        Riprova dopo le 09:00 per dati freschi.
                    </p>
                </div>
            `;
            return;
        }
        
        if (stato.completato) {
            contenuto.innerHTML = '';
            if (pollingTimer) {
                clearTimeout(pollingTimer);
                pollingTimer = null;
            }
            caricaDati();
        } else if (stato.in_corso) {
            const progresso = stato.progresso || 0;
            contenuto.innerHTML = `
                <div class="loading">
                    <div style="font-size: 2em; margin-bottom: 20px;">📊</div>
                    <p style="font-size: 1.2em; margin-bottom: 10px;">Caricamento dati in corso...</p>
                    <p style="color: #666; font-size: 0.95em;">Primo avvio: circa 10 minuti. Poi tutto diventa istantaneo.</p>
                    <div style="margin-top: 20px; background: #e5e5e5; border-radius: 4px; height: 6px; width: 300px; margin: 20px auto;">
                        <div style="background: #1a1a1a; height: 100%; width: ${progresso}%; border-radius: 4px; transition: width 0.5s;"></div>
                    </div>
                    <p style="color: #999; font-size: 0.85em;">${progresso}%</p>
                </div>
            `;
            pollingTimer = setTimeout(controllaStato, 3000);
        } else if (stato.errore) {
            contenuto.innerHTML = `
                <div class="loading">
                    <p style="color: #c13224; font-size: 1.1em;">❌ Errore nel caricamento dati</p>
                    <p style="color: #666; margin-top: 10px;">${stato.errore}</p>
                    <p style="color: #999; margin-top: 10px; font-size: 0.9em;">Ricarica la pagina per riprovare</p>
                </div>
            `;
        } else {
            contenuto.innerHTML = `<div class="loading">Inizializzazione...</div>`;
            pollingTimer = setTimeout(controllaStato, 2000);
        }
    } catch (error) {
        contenuto.innerHTML = `
            <div class="loading">
                <p style="color: #c13224;">❌ Errore di connessione</p>
            </div>
        `;
        pollingTimer = setTimeout(controllaStato, 5000);
    }
}

function cambiaTab(tab) {
    tabCorrente = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    
    document.getElementById('controls-periodo').style.display = 
        (tab === 'peggiori' || tab === 'migliori') ? 'block' : 'none';
    document.getElementById('controls-categorie').style.display = 
        (tab === 'categorie') ? 'block' : 'none';
    
    caricaDati();
}

async function caricaDati() {
    const contenuto = document.getElementById('contenuto');
    
    try {
        let url;
        if (tabCorrente === 'peggiori') url = `/api/peggiori/${periodoCorrente}`;
        else if (tabCorrente === 'migliori') url = `/api/migliori/${periodoCorrente}`;
        else if (tabCorrente === 'strategie') url = '/api/strategie';
        else if (tabCorrente === 'categorie') url = `/api/categoria/${categoriaCorrente}`;
        
        const response = await fetch(url);
        
        if (response.status === 202) {
            controllaStato();
            return;
        }
        
        if (!response.ok) {
            throw new Error(`Errore ${response.status}`);
        }
        
        const dati = await response.json();
        
        if (tabCorrente === 'peggiori') mostraClassifica(dati, 'Peggiori Performer');
        else if (tabCorrente === 'migliori') mostraClassifica(dati, 'Migliori Performer');
        else if (tabCorrente === 'strategie') mostraStrategie(dati);
        else if (tabCorrente === 'categorie') mostraCategoria(dati);
        
        document.getElementById('update-info').textContent = 
            `Aggiornato: ${new Date().toLocaleString('it-IT')} | Cache: 15 min`;
    } catch (error) {
        contenuto.innerHTML = `<div class="loading">Errore: ${error.message}</div>`;
    }
}

function mostraClassifica(dati, titolo) {
    const periodoNomi = {
        '1_settimana': '1 Settimana', '1_mese': '1 Mese', '3_mesi': '3 Mesi',
        '6_mesi': '6 Mesi', '12_mesi': '12 Mesi', '18_mesi': '18 Mesi', '24_mesi': '24 Mesi'
    };
    
    let html = `<h2 style="margin-bottom: 20px; font-weight: 400;">${titolo} - ${periodoNomi[dati.periodo]}</h2>`;
    html += `<table><thead><tr>
        <th>Ticker</th><th>Nome</th><th>Categoria</th><th>Prezzo</th><th>Variazione</th><th>Grafico</th>
    </tr></thead><tbody>`;
    
    dati.titoli.forEach(titolo => {
        const classe = titolo.variazione >= 0 ? 'positive' : 'negative';
        const simbolo = titolo.variazione >= 0 ? '▲' : '▼';
        const catNome = CATEGORIE_NOMI[titolo.categoria] || titolo.categoria;
        
        html += `<tr>
            <td>${linkTicker(titolo.ticker, titolo.nome)}</td>
            <td>${titolo.nome}</td>
            <td>${catNome}</td>
            <td>$${titolo.prezzo || 'N/A'}</td>
            <td class="${classe}">${simbolo} ${titolo.variazione}%</td>
            <td><a href="${creaLinkEsterno(titolo.ticker)}" target="_blank" class="external-link" title="Apri grafico">📊 Apri</a></td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<div class="insight-box">
        <h3>💡 Insight</h3>
        <p>Totale titoli analizzati: ${dati.totale_titoli}. Clicca su un ticker per vedere il grafico completo su Yahoo Finance.</p>
    </div>`;
    
    document.getElementById('contenuto').innerHTML = html;
}

function mostraStrategie(dati) {
    let html = `<h2 style="margin-bottom: 30px; font-weight: 400;">📊 Strategie di Investimento</h2>`;
    
    const ordine = ['mean_reversion', 'momentum', 'contrarian', 'flight_quality'];
    
    ordine.forEach(key => {
        const info = STRATEGIE_INFO[key];
        const titoli = dati[key] || [];
        
        html += `
        <div class="strategy-section">
            <div class="strategy-header">
                <div class="strategy-icon">${info.icona}</div>
                <div>
                    <div class="strategy-title">${info.titolo}</div>
                </div>
            </div>
            <p class="strategy-description">${info.descrizione}</p>
        `;
        
        if (titoli.length > 0) {
            html += `<div class="strategy-tickers">`;
            titoli.forEach(t => {
                const classe = t.variazione >= 0 ? 'positive' : 'negative';
                html += `
                <div class="strategy-ticker">
                    <span class="ticker-name">${linkTicker(t.ticker, t.nome)}</span>
                    <span class="ticker-var ${classe}">${t.variazione >= 0 ? '▲' : '▼'} ${t.variazione}%</span>
                </div>
                `;
            });
            html += `</div>`;
        } else {
            html += `<p style="color: #999; font-style: italic;">Nessun titolo attualmente rientra in questa strategia con i criteri attuali.</p>`;
        }
        
        html += `</div>`;
    });
    
    html += `<div class="insight-box">
        <h3>⚠️ Disclaimer</h3>
        <p>Queste strategie sono basate su criteri matematici automatici. Non costituiscono consulenza finanziaria. Verifica sempre i fondamentali aziendali e la tua tolleranza al rischio prima di investire.</p>
    </div>`;
    
    document.getElementById('contenuto').innerHTML = html;
}

function mostraCategoria(dati) {
    const catNome = CATEGORIE_NOMI[dati.categoria] || dati.categoria;
    
    let html = `<h2 style="margin-bottom: 20px; font-weight: 400;">${catNome}</h2>`;
    html += `<table><thead><tr>
        <th>Ticker</th><th>Nome</th><th>Prezzo</th>
        <th>1S</th><th>1M</th><th>3M</th><th>6M</th><th>12M</th><th>24M</th><th>Grafico</th>
    </tr></thead><tbody>`;
    
    dati.titoli.forEach(titolo => {
        html += `<tr>
            <td>${linkTicker(titolo.ticker, titolo.nome)}</td>
            <td>${titolo.nome}</td>
            <td>$${titolo.prezzo_attuale || 'N/A'}</td>`;
        
        ['1_settimana', '1_mese', '3_mesi', '6_mesi', '12_mesi', '24_mesi'].forEach(p => {
            const var_val = titolo.variazioni[p];
            if (var_val !== null && var_val !== undefined) {
                const classe = var_val >= 0 ? 'positive' : 'negative';
                html += `<td class="${classe}">${var_val}%</td>`;
            } else {
                html += `<td style="color: #999;">-</td>`;
            }
        });
        
        html += `<td><a href="${creaLinkEsterno(titolo.ticker)}" target="_blank" class="external-link">📊</a></td>`;
        html += `</tr>`;
    });
    
    html += `</tbody></table>`;
    document.getElementById('contenuto').innerHTML = html;
}

// ============================================================================
// GESTIONE FOOTER E REFRESH
// ============================================================================

let footerInterval = null;
let prossimoAggiornamentoSecondi = 0;

function formattaTempo(secondi) {
    if (secondi <= 0) return 'Ora';
    if (secondi < 60) return `${secondi}s`;
    if (secondi < 3600) return `${Math.floor(secondi/60)}m ${secondi%60}s`;
    const ore = Math.floor(secondi / 3600);
    const min = Math.floor((secondi % 3600) / 60);
    return `${ore}h ${min}m`;
}

function formattaData(isoString) {
    if (!isoString) return '-';
    const d = new Date(isoString);
    return d.toLocaleString('it-IT', { 
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}

async function aggiornaFooter() {
    try {
        const response = await fetch('/api/cache-info');
        const info = await response.json();
        
        document.getElementById('footer-ultimo').textContent = 
            formattaData(info.ultimo_aggiornamento);
        
        document.getElementById('footer-fascia').textContent = 
            info.fascia_attiva ? '☀️ Attiva (9-21)' : '🌙 Notturna';
        
        prossimoAggiornamentoSecondi = info.prossimo_aggiornamento_secondi;
        aggiornaCountdown();
        
        // Avvia countdown se non è già attivo
        if (!footerInterval) {
            footerInterval = setInterval(() => {
                prossimoAggiornamentoSecondi--;
                if (prossimoAggiornamentoSecondi < 0) prossimoAggiornamentoSecondi = 0;
                aggiornaCountdown();
                
                // Se arriva a 0, ricarica la pagina
                if (prossimoAggiornamentoSecondi === 0) {
                    clearInterval(footerInterval);
                    footerInterval = null;
                    location.reload();
                }
            }, 1000);
        }
    } catch (e) {
        console.error('Errore footer:', e);
    }
}

function aggiornaCountdown() {
    const el = document.getElementById('footer-prossimo');
    if (el) {
        el.textContent = formattaTempo(prossimoAggiornamentoSecondi);
    }
}

async function forzaRefresh() {
    const btn = document.getElementById('btn-refresh');
    if (btn.disabled) return;
    
    btn.disabled = true;
    btn.classList.add('loading');
    btn.textContent = '⏳ Aggiornamento in corso...';
    
    try {
        const response = await fetch('/api/refresh', { method: 'POST' });
        const data = await response.json();
        
        if (data.status === 'started') {
            btn.textContent = '✅ Avviato, attendi 2-3 min...';
            // Mostra messaggio di attesa
            setTimeout(() => {
                btn.disabled = false;
                btn.classList.remove('loading');
                btn.textContent = '🔄 Aggiorna ora';
                location.reload();
            }, 120000); // ricarica dopo 2 min
        } else {
            alert(data.messaggio);
            btn.disabled = false;
            btn.classList.remove('loading');
            btn.textContent = '🔄 Aggiorna ora';
        }
    } catch (error) {
        alert('Errore: ' + error.message);
        btn.disabled = false;
        btn.classList.remove('loading');
        btn.textContent = '🔄 Aggiorna ora';
    }
}

// Avvia aggiornamento footer quando il documento è pronto
document.addEventListener('DOMContentLoaded', () => {
    aggiornaFooter();
    // Aggiorna info footer ogni 30 secondi
    setInterval(aggiornaFooter, 60000);
});
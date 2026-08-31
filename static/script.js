let tabCorrente = 'peggiori';
let periodoCorrente = '3m';
let categoriaCorrente = 'indici_sviluppati';

document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    caricaDati();
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
    
    document.querySelector('.close').addEventListener('click', chiudiModal);
    window.addEventListener('click', (e) => {
        if (e.target.id === 'chart-modal') chiudiModal();
    });
}

function cambiaTab(tab) {
    tabCorrente = tab;
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
    
    document.getElementById('controls-peggiori').style.display = tab === 'peggiori' ? 'block' : 'none';
    document.getElementById('controls-migliori').style.display = tab === 'migliori' ? 'block' : 'none';
    document.getElementById('controls-categorie').style.display = tab === 'categorie' ? 'block' : 'none';
    
    caricaDati();
}

async function caricaDati() {
    const contenuto = document.getElementById('contenuto');
    contenuto.innerHTML = '<div class="loading">Caricamento...</div>';
    
    try {
        let url;
        if (tabCorrente === 'peggiori') url = `/api/peggiori/${periodoCorrente}`;
        else if (tabCorrente === 'migliori') url = `/api/migliori/${periodoCorrente}`;
        else if (tabCorrente === 'capitalizzati') url = '/api/top-capitalizzati';
        else if (tabCorrente === 'categorie') url = `/api/categoria/${categoriaCorrente}`;
        
        const response = await fetch(url);
        const dati = await response.json();
        
        if (tabCorrente === 'peggiori') mostraClassifica(dati, 'Peggiori Performer');
        else if (tabCorrente === 'migliori') mostraClassifica(dati, 'Migliori Performer');
        else if (tabCorrente === 'capitalizzati') mostraCapitalizzati(dati);
        
        document.getElementById('update-info').textContent = 
            `Aggiornato: ${new Date().toLocaleString('it-IT')}`;
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
        <th>Ticker</th><th>Nome</th><th>Categoria</th><th>Prezzo</th><th>Variazione</th><th></th>
    </tr></thead><tbody>`;
    
    dati.titoli.forEach(titolo => {
        const classe = titolo.variazione >= 0 ? 'positive' : 'negative';
        const simbolo = titolo.variazione >= 0 ? '▲' : '▼';
        html += `<tr>
            <td><a class="ticker-link" onclick="apriGrafico('${titolo.ticker}', '${titolo.nome}')">${titolo.ticker}</a></td>
            <td>${titolo.nome}</td>
            <td>${titolo.categoria}</td>
            <td>$${titolo.prezzo || 'N/A'}</td>
            <td class="${classe}">${simbolo} ${titolo.variazione}%</td>
            <td><a class="ticker-link" onclick="apriGrafico('${titolo.ticker}', '${titolo.nome}')">📊</a></td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    html += `<div class="insight-box">
        <h3>Insight</h3>
        <p>Totale titoli analizzati: ${dati.totale_titoli}. Clicca su un ticker per vedere il grafico completo.</p>
    </div>`;
    
    document.getElementById('contenuto').innerHTML = html;
}

function mostraCapitalizzati(dati) {
    let html = `<h2 style="margin-bottom: 20px; font-weight: 400;">Top 50 per Capitalizzazione</h2>`;
    html += `<table><thead><tr>
        <th>Ticker</th><th>Nome</th><th>Prezzo</th><th>Market Cap</th><th>6M</th><th>12M</th><th></th>
    </tr></thead><tbody>`;
    
    dati.forEach(titolo => {
        const marketCapB = (titolo.market_cap / 1e9).toFixed(2);
        const classe6m = titolo.variazione_6m >= 0 ? 'positive' : 'negative';
        const classe12m = titolo.variazione_12m >= 0 ? 'positive' : 'negative';
        
        html += `<tr>
            <td><a class="ticker-link" onclick="apriGrafico('${titolo.ticker}', '${titolo.nome}')">${titolo.ticker}</a></td>
            <td>${titolo.nome}</td>
            <td>$${titolo.prezzo || 'N/A'}</td>
            <td>$${marketCapB}B</td>
            <td class="${classe6m}">${titolo.variazione_6m || 0}%</td>
            <td class="${classe12m}">${titolo.variazione_12m || 0}%</td>
            <td><a class="ticker-link" onclick="apriGrafico('${titolo.ticker}', '${titolo.nome}')">📊</a></td>
        </tr>`;
    });
    
    html += `</tbody></table>`;
    document.getElementById('contenuto').innerHTML = html;
}

function apriGrafico(ticker, nome) {
    document.getElementById('chart-title').textContent = `${nome} (${ticker})`;
    
    const container = document.getElementById('chart-container');
    container.innerHTML = `<div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({
            "width": "100%",
            "height": 600,
            "symbol": "${ticker}",
            "interval": "D",
            "timezone": "Europe/Rome",
            "theme": "light",
            "style": "1",
            "locale": "it",
            "toolbar_bg": "#fafafa",
            "enable_publishing": false,
            "hide_side_toolbar": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_chart"
        });
        </script>
    </div>`;
    
    document.getElementById('chart-modal').style.display = 'block';
}

function chiudiModal() {
    document.getElementById('chart-modal').style.display = 'none';
    document.getElementById('chart-container').innerHTML = '';
}
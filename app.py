from flask import Flask, jsonify, render_template
import yfinance as yf
import json
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)

# File di cache persistente
CACHE_FILE = 'cache_dati.json'
CACHE_DURATION = 900  # 15 minuti

# ============================================================================
# LISTA COMPLETA TICKERS (semplificata per performance - 100 totali)
# ============================================================================

TICKERS = {
    'indici_sviluppati': {
        '^GSPC': 'S&P 500', '^IXIC': 'Nasdaq 100', '^DJI': 'Dow Jones',
        '^RUT': 'Russell 2000', '^FTSE': 'FTSE 100', '^GDAXI': 'DAX',
        '^FCHI': 'CAC 40', '^STOXX50E': 'Euro Stoxx 50',
        '^N225': 'Nikkei 225', '^HSI': 'Hang Seng',
    },
    'mercati_emergenti': {
        'EEM': 'ETF Emerging Markets', 'VWO': 'Vanguard Emerging',
        'INDA': 'ETF India', 'FXI': 'ETF China Large-Cap',
        'EWZ': 'ETF Brazil', 'EWT': 'ETF Taiwan',
        'EPI': 'ETF India WisdomTree', 'TUR': 'ETF Turkey',
    },
    'top_100_aziende': {
        'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
        'AMZN': 'Amazon', 'NVDA': 'Nvidia', 'META': 'Meta',
        'TSLA': 'Tesla', 'BRK-B': 'Berkshire Hathaway',
        'AVGO': 'Broadcom', 'LLY': 'Eli Lilly', 'WMT': 'Walmart',
        'JPM': 'JPMorgan', 'V': 'Visa', 'UNH': 'UnitedHealth',
        'MA': 'Mastercard', 'HD': 'Home Depot', 'PG': 'Procter & Gamble',
        'XOM': 'Exxon Mobil', 'ORCL': 'Oracle', 'COST': 'Costco',
        'BAC': 'Bank of America', 'NFLX': 'Netflix', 'ABBV': 'AbbVie',
        'CRM': 'Salesforce', 'CVX': 'Chevron', 'KO': 'Coca-Cola',
        'AMD': 'AMD', 'PEP': 'PepsiCo', 'TMO': 'Thermo Fisher',
        'WFC': 'Wells Fargo', 'CSCO': 'Cisco', 'LIN': 'Linde',
        'MCD': 'McDonald\'s', 'ACN': 'Accenture', 'ABT': 'Abbott',
        'ADBE': 'Adobe', 'DIS': 'Disney', 'TMUS': 'T-Mobile',
        'INTC': 'Intel', 'IBM': 'IBM', 'QCOM': 'Qualcomm',
        'TXN': 'Texas Instruments', 'GS': 'Goldman Sachs',
        'MS': 'Morgan Stanley', 'BLK': 'BlackRock',
        'AXP': 'American Express', 'JNJ': 'Johnson & Johnson',
        'PFE': 'Pfizer', 'MRK': 'Merck', 'NKE': 'Nike',
        'BA': 'Boeing', 'CAT': 'Caterpillar', 'GE': 'General Electric',
        'HON': 'Honeywell', 'UPS': 'UPS', 'RTX': 'Raytheon',
        'LMT': 'Lockheed Martin', 'T': 'AT&T', 'VZ': 'Verizon',
        'PYPL': 'PayPal', 'UBER': 'Uber', 'ABNB': 'Airbnb',
        'SPOT': 'Spotify', 'CRWD': 'CrowdStrike', 'PANW': 'Palo Alto',
        'NET': 'Cloudflare', 'SNOW': 'Snowflake', 'PLTR': 'Palantir',
        'SQ': 'Block', 'COIN': 'Coinbase', 'BKNG': 'Booking',
        'SBUX': 'Starbucks', 'TGT': 'Target', 'LOW': 'Lowe\'s',
        'NOW': 'ServiceNow', 'INTU': 'Intuit', 'AMAT': 'Applied Materials',
    },
    'materie_prime': {
        'GC=F': 'Oro', 'SI=F': 'Argento', 'CL=F': 'Petrolio WTI',
        'BZ=F': 'Petrolio Brent', 'NG=F': 'Gas Naturale',
        'HG=F': 'Rame', 'ZC=F': 'Mais', 'KC=F': 'Caffè',
    },
    'crypto': {
        'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum',
        'SOL-USD': 'Solana', 'XRP-USD': 'Ripple',
        'ADA-USD': 'Cardano', 'DOGE-USD': 'Dogecoin',
    },
    'etf_settoriali': {
        'XLK': 'ETF Technology', 'XLF': 'ETF Financial',
        'XLV': 'ETF Healthcare', 'XLE': 'ETF Energy',
        'XLI': 'ETF Industrial', 'ARKK': 'ETF Innovation',
        'SOXX': 'ETF Semiconduttori', 'KWEB': 'ETF Cina Internet',
        'TAN': 'ETF Solare', 'LIT': 'ETF Litio',
    }
}

# ============================================================================
# SISTEMA DI CACHE SU FILE
# ============================================================================

def carica_cache():
    """Carica i dati dalla cache su file"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                # Verifica che la cache non sia scaduta
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    print("✅ Dati caricati dalla cache")
                    return data['dati']
        except Exception as e:
            print(f"Errore caricamento cache: {e}")
    return None

def salva_cache(dati):
    """Salva i dati nella cache su file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'dati': dati
            }, f)
        print("✅ Dati salvati in cache")
    except Exception as e:
        print(f"Errore salvataggio cache: {e}")

def calcola_variazione(ticker_symbol, giorni):
    """Calcola variazione percentuale"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=giorni + 10)
        
        hist = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if len(hist) < 2:
            return None
        
        prezzo_iniziale = hist['Close'].iloc[0]
        prezzo_finale = hist['Close'].iloc[-1]
        
        if prezzo_iniziale == 0:
            return None
        
        variazione = ((prezzo_finale - prezzo_iniziale) / prezzo_iniziale) * 100
        return round(variazione, 2)
    except Exception as e:
        print(f"Errore calcolo {ticker_symbol}: {e}")
        return None

def ottieni_dati_ticker(ticker_symbol, nome, categoria):
    """Ottieni tutti i dati per un ticker"""
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        prezzo_attuale = info.get('regularMarketPrice', 0)
        market_cap = info.get('marketCap', None)
        
        periodi = {
            '1_settimana': 7, '1_mese': 30, '3_mesi': 90,
            '6_mesi': 180, '12_mesi': 365, '18_mesi': 540, '24_mesi': 730
        }
        
        variazioni = {}
        for periodo_nome, giorni in periodi.items():
            var = calcola_variazione(ticker_symbol, giorni)
            variazioni[periodo_nome] = var
        
        return {
            'ticker': ticker_symbol,
            'nome': nome,
            'categoria': categoria,
            'prezzo_attuale': round(prezzo_attuale, 2) if prezzo_attuale else None,
            'market_cap': market_cap,
            'variazioni': variazioni
        }
    except Exception as e:
        print(f"Errore completo {ticker_symbol}: {e}")
        return None

def ottieni_tutti_i_dati():
    """Ottieni tutti i dati con cache"""
    # Prova a caricare dalla cache
    cached = carica_cache()
    if cached:
        return cached
    
    print("🔄 Cache scaduta o assente, scarico nuovi dati...")
    risultati = {}
    
    for categoria, tickers in TICKERS.items():
        print(f"Elaborazione: {categoria} ({len(tickers)} ticker)")
        risultati[categoria] = []
        
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            for ticker, nome in tickers.items():
                future = executor.submit(ottieni_dati_ticker, ticker, nome, categoria)
                futures.append(future)
            
            for future in futures:
                result = future.result()
                if result:
                    risultati[categoria].append(result)
    
    # Salva in cache
    salva_cache(risultati)
    return risultati

# ============================================================================
# PRE-FETCHING: aggiorna la cache in background ogni 15 minuti
# ============================================================================

def background_updater():
    """Aggiorna la cache in background"""
    while True:
        try:
            print("🔄 Background update iniziato...")
            ottieni_tutti_i_dati()
            print("✅ Background update completato")
        except Exception as e:
            print(f"Errore background update: {e}")
        time.sleep(CACHE_DURATION)

# Avvia il thread di background all'avvio
threading.Thread(target=background_updater, daemon=True).start()

# ============================================================================
# ROUTE FLASK
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/peggiori/<periodo>')
def api_peggiori(periodo):
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    if periodo not in periodo_mappatura:
        return jsonify({'errore': 'Periodo non valido'}), 400
    
    periodo_nome = periodo_mappatura[periodo]
    dati = ottieni_tutti_i_dati()
    
    tutti_titoli = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            var = titolo['variazioni'].get(periodo_nome)
            if var is not None:
                tutti_titoli.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': titolo['categoria'],
                    'prezzo': titolo['prezzo_attuale'],
                    'variazione': var
                })
    
    tutti_titoli.sort(key=lambda x: x['variazione'])
    
    return jsonify({
        'periodo': periodo_nome,
        'totale_titoli': len(tutti_titoli),
        'peggiori': tutti_titoli[:50]
    })

@app.route('/api/migliori/<periodo>')
def api_migliori(periodo):
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    if periodo not in periodo_mappatura:
        return jsonify({'errore': 'Periodo non valido'}), 400
    
    periodo_nome = periodo_mappatura[periodo]
    dati = ottieni_tutti_i_dati()
    
    tutti_titoli = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            var = titolo['variazioni'].get(periodo_nome)
            if var is not None:
                tutti_titoli.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': titolo['categoria'],
                    'prezzo': titolo['prezzo_attuale'],
                    'variazione': var
                })
    
    tutti_titoli.sort(key=lambda x: x['variazione'], reverse=True)
    
    return jsonify({
        'periodo': periodo_nome,
        'totale_titoli': len(tutti_titoli),
        'migliori': tutti_titoli[:50]
    })

@app.route('/api/top-capitalizzati')
def api_top_capitalizzati():
    dati = ottieni_tutti_i_dati()
    
    titoli_con_cap = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            if titolo.get('market_cap'):
                titoli_con_cap.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': titolo['categoria'],
                    'prezzo': titolo['prezzo_attuale'],
                    'market_cap': titolo['market_cap'],
                    'variazione_6m': titolo['variazioni'].get('6_mesi')
                })
    
    titoli_con_cap.sort(key=lambda x: x['market_cap'], reverse=True)
    return jsonify(titoli_con_cap[:100])

@app.route('/api/categoria/<categoria_nome>')
def api_per_categoria(categoria_nome):
    dati = ottieni_tutti_i_dati()
    
    if categoria_nome not in dati:
        return jsonify({'errore': 'Categoria non trovata'}), 404
    
    return jsonify({
        'categoria': categoria_nome,
        'titoli': dati[categoria_nome]
    })

if __name__ == '__main__':
    # Forza un primo caricamento della cache all'avvio
    print("🚀 Avvio applicazione e pre-caricamento cache...")
    ottieni_tutti_i_dati()
    app.run(host='0.0.0.0', port=5000)
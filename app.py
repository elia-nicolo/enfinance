from flask import Flask, jsonify, render_template
import requests
import json
import os
import time
import threading
from datetime import datetime

app = Flask(__name__)

CACHE_FILE = 'cache_dati.json'
CACHE_DURATION = 900  # 15 minuti

# ⚠️ INSERISCI QUI LA TUA API KEY DI TWELVE DATA
TWELVE_DATA_API_KEY = os.environ.get('TWELVE_DATA_API_KEY', 'f2cf69a2047947ef9022047ffaa2c8e6')

stato = {
    'in_corso': False, 
    'completato': False, 
    'errore': None, 
    'progresso': 0,
    'ultimo_aggiornamento': None
}

# TICKERS (usiamo solo ticker supportati da Twelve Data)
TICKERS = {
    'indici_sviluppati': {
        'SPX': 'S&P 500', 'NDX': 'Nasdaq 100', 'DJI': 'Dow Jones',
        'FTSE': 'FTSE 100', 'DAX': 'DAX Germania', 'CAC': 'CAC 40 Francia',
        'N225': 'Nikkei 225', 'HSI': 'Hang Seng',
    },
    'mercati_emergenti': {
        'EEM/USD': 'ETF Emerging Markets', 'VWO/USD': 'Vanguard Emerging',
        'INDA/USD': 'ETF India', 'FXI/USD': 'ETF China',
    },
    'top_aziende': {
        'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
        'AMZN': 'Amazon', 'NVDA': 'Nvidia', 'META': 'Meta',
        'TSLA': 'Tesla', 'AVGO': 'Broadcom', 'LLY': 'Eli Lilly',
        'WMT': 'Walmart', 'JPM': 'JPMorgan', 'V': 'Visa',
        'UNH': 'UnitedHealth', 'MA': 'Mastercard', 'HD': 'Home Depot',
        'PG': 'P&G', 'XOM': 'Exxon', 'ORCL': 'Oracle',
        'COST': 'Costco', 'BAC': 'Bank of America', 'NFLX': 'Netflix',
        'ABBV': 'AbbVie', 'CRM': 'Salesforce', 'CVX': 'Chevron',
        'KO': 'Coca-Cola', 'AMD': 'AMD', 'PEP': 'PepsiCo',
        'TMO': 'Thermo Fisher', 'WFC': 'Wells Fargo', 'CSCO': 'Cisco',
        'LIN': 'Linde', 'MCD': 'McDonald\'s', 'ACN': 'Accenture',
        'ABT': 'Abbott', 'ADBE': 'Adobe', 'DIS': 'Disney',
        'TMUS': 'T-Mobile', 'INTC': 'Intel', 'IBM': 'IBM',
        'QCOM': 'Qualcomm', 'TXN': 'Texas Instruments', 'GS': 'Goldman Sachs',
        'MS': 'Morgan Stanley', 'BLK': 'BlackRock', 'AXP': 'Amex',
        'JNJ': 'Johnson & Johnson', 'PFE': 'Pfizer', 'MRK': 'Merck',
        'NKE': 'Nike', 'BA': 'Boeing', 'CAT': 'Caterpillar',
        'GE': 'GE', 'HON': 'Honeywell', 'PYPL': 'PayPal',
        'UBER': 'Uber', 'ABNB': 'Airbnb', 'CRWD': 'CrowdStrike',
        'PANW': 'Palo Alto', 'NET': 'Cloudflare', 'SNOW': 'Snowflake',
        'PLTR': 'Palantir', 'SQ': 'Block', 'COIN': 'Coinbase',
        'SBUX': 'Starbucks', 'NOW': 'ServiceNow',
    },
    'materie_prime': {
        'XAU/USD': 'Oro', 'XAG/USD': 'Argento', 
        'CL/USD': 'Petrolio WTI', 'NG/USD': 'Gas Naturale',
    },
    'crypto': {
        'BTC/USD': 'Bitcoin', 'ETH/USD': 'Ethereum',
        'SOL/USD': 'Solana', 'XRP/USD': 'Ripple', 'DOGE/USD': 'Dogecoin',
    },
    'etf_settoriali': {
        'XLK': 'ETF Technology', 'XLF': 'ETF Financial', 
        'XLV': 'ETF Healthcare', 'XLE': 'ETF Energy',
        'XLI': 'ETF Industrial', 'ARKK': 'ETF Innovation',
        'SOXX': 'ETF Semiconduttori',
    }
}

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    return data['dati']
        except Exception as e:
            print(f"Errore cache: {e}")
    return None

def salva_cache(dati):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'dati': dati}, f)
    except Exception as e:
        print(f"Errore salvataggio cache: {e}")

def scarica_dati_ticker(ticker):
    """Scarica 2 anni di dati da Twelve Data"""
    try:
        url = 'https://api.twelvedata.com/time_series'
        params = {
            'symbol': ticker,
            'interval': '1day',
            'outputsize': 520,  # ~2 anni di dati
            'apikey': TWELVE_DATA_API_KEY,
            'format': 'JSON'
        }
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'values' not in data:
            if 'message' in data:
                print(f"⚠️ {ticker}: {data['message']}")
            return None
        
        # Converte in lista di prezzi di chiusura (dal più vecchio al più recente)
        closes = []
        for entry in reversed(data['values']):  # reversed perché TD restituisce dal più recente
            try:
                closes.append(float(entry['close']))
            except:
                continue
        
        return closes if len(closes) > 30 else None
        
    except Exception as e:
        print(f"❌ {ticker}: {str(e)[:80]}")
        return None

def download_e_elabora():
    """Scarica tutti i dati da Twelve Data"""
    global stato
    
    try:
        stato['in_corso'] = True
        stato['errore'] = None
        stato['progresso'] = 5
        
        # Costruisci lista ticker
        ticker_map = {}
        for cat, tickers in TICKERS.items():
            for t, nome in tickers.items():
                ticker_map[t] = (nome, cat)
        
        ticker_list = list(ticker_map.keys())
        print(f"🔄 Download {len(ticker_list)} ticker da Twelve Data...")
        
        risultati = {cat: [] for cat in TICKERS}
        successi = 0
        
        # Giorni di trading per periodo
        periodi_trading = {
            '1_settimana': 5, '1_mese': 21, '3_mesi': 63,
            '6_mesi': 126, '12_mesi': 252, '18_mesi': 378, '24_mesi': 504
        }
        
        for i, ticker_symbol in enumerate(ticker_list):
            closes = scarica_dati_ticker(ticker_symbol)
            
            if closes:
                prezzo_attuale = round(closes[-1], 2)
                
                variazioni = {}
                for nome_p, giorni_t in periodi_trading.items():
                    if len(closes) > giorni_t:
                        p_iniz = closes[-giorni_t]
                        p_fin = closes[-1]
                        if p_iniz != 0:
                            variazioni[nome_p] = round(((p_fin - p_iniz) / p_iniz) * 100, 2)
                        else:
                            variazioni[nome_p] = None
                    else:
                        variazioni[nome_p] = None
                
                nome, categoria = ticker_map[ticker_symbol]
                risultati[categoria].append({
                    'ticker': ticker_symbol,
                    'nome': nome,
                    'categoria': categoria,
                    'prezzo_attuale': prezzo_attuale,
                    'market_cap': None,  # Twelve Data non lo fornisce nel free tier
                    'variazioni': variazioni
                })
                successi += 1
            
            # Aggiorna progresso
            stato['progresso'] = 5 + int(90 * (i + 1) / len(ticker_list))
            
            # Pausa per rispettare rate-limit (8 req/minuto = 1 ogni 7.5 secondi)
            # Ma possiamo farne 8 in un burst, poi pausa
            if (i + 1) % 7 == 0:
                time.sleep(7)
            else:
                time.sleep(1)
        
        print(f"✅ Completato: {successi}/{len(ticker_list)} ticker scaricati")
        
        salva_cache(risultati)
        
        stato['completato'] = True
        stato['progresso'] = 100
        stato['ultimo_aggiornamento'] = datetime.now().isoformat()
        
    except Exception as e:
        print(f"❌ Errore generale: {e}")
        stato['errore'] = str(e)
    finally:
        stato['in_corso'] = False

def avvia_background():
    if not stato['in_corso'] and not stato['completato']:
        print("🚀 Avvio download in background...")
        t = threading.Thread(target=download_e_elabora, daemon=True)
        t.start()

# All'avvio
cache_iniziale = carica_cache()
if cache_iniziale is not None:
    stato['completato'] = True
    stato['progresso'] = 100
    print("✅ Cache caricata all'avvio")
else:
    avvia_background()

# ============================================================================
# ROUTE
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    return jsonify(stato)

@app.route('/api/peggiori/<periodo>')
def api_peggiori(periodo):
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    periodo_nome = periodo_mappatura.get(periodo, '3_mesi')
    
    tutti_titoli = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            var = titolo['variazioni'].get(periodo_nome)
            if var is not None:
                tutti_titoli.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': categoria.replace('_', ' ').title(),
                    'prezzo': titolo['prezzo_attuale'],
                    'variazione': var
                })
    
    tutti_titoli.sort(key=lambda x: x['variazione'])
    
    return jsonify({
        'periodo': periodo_nome,
        'totale_titoli': len(tutti_titoli),
        'titoli': tutti_titoli[:30]
    })

@app.route('/api/migliori/<periodo>')
def api_migliori(periodo):
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    periodo_nome = periodo_mappatura.get(periodo, '3_mesi')
    
    tutti_titoli = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            var = titolo['variazioni'].get(periodo_nome)
            if var is not None:
                tutti_titoli.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': categoria.replace('_', ' ').title(),
                    'prezzo': titolo['prezzo_attuale'],
                    'variazione': var
                })
    
    tutti_titoli.sort(key=lambda x: x['variazione'], reverse=True)
    
    return jsonify({
        'periodo': periodo_nome,
        'totale_titoli': len(tutti_titoli),
        'titoli': tutti_titoli[:30]
    })

@app.route('/api/top-capitalizzati')
def api_top_capitalizzati():
    """Per ora restituisce i titoli ordinati per nome (Twelve Data free non ha market cap)"""
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    # Fallback: prendi i titoli più conosciuti (top aziende in ordine di importanza)
    top_tickers = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'BRK-B', 'TSLA', 'AVGO', 'LLY']
    titoli_top = []
    
    for categoria, titoli in dati.items():
        for titolo in titoli:
            if titolo['ticker'] in top_tickers:
                titoli_top.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': categoria.replace('_', ' ').title(),
                    'prezzo': titolo['prezzo_attuale'],
                    'market_cap': 1000000000000,  # Placeholder
                    'variazione_6m': titolo['variazioni'].get('6_mesi'),
                    'variazione_12m': titolo['variazioni'].get('12_mesi')
                })
    
    # Ordina secondo la lista di priorità
    titoli_top.sort(key=lambda x: top_tickers.index(x['ticker']) if x['ticker'] in top_tickers else 999)
    
    return jsonify(titoli_top)

@app.route('/api/categoria/<categoria_nome>')
def api_per_categoria(categoria_nome):
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    if categoria_nome not in dati:
        return jsonify({'errore': 'Categoria non trovata'}), 404
    
    return jsonify({
        'categoria': categoria_nome,
        'titoli': dati[categoria_nome]
    })

if __name__ == '__main__':
    print("🚀 Avvio AssetScope con Twelve Data...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
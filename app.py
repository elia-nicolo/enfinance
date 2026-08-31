from flask import Flask, jsonify, render_template
import yfinance as yf
import json
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import requests

app = Flask(__name__)

CACHE_FILE = 'cache_dati.json'
CACHE_DURATION = 900  # 15 minuti

# Headers per evitare blocchi da Yahoo
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

TICKERS = {
    'indici_sviluppati': {
        '^GSPC': 'S&P 500', '^IXIC': 'Nasdaq 100', '^DJI': 'Dow Jones',
        '^RUT': 'Russell 2000', '^FTSE': 'FTSE 100', '^GDAXI': 'DAX',
        '^FCHI': 'CAC 40', '^STOXX50E': 'Euro Stoxx 50',
        '^N225': 'Nikkei 225', '^HSI': 'Hang Seng',
    },
    'mercati_emergenti': {
        'EEM': 'ETF Emerging Markets', 'VWO': 'Vanguard Emerging',
        'INDA': 'ETF India', 'FXI': 'ETF China',
        'EWZ': 'ETF Brazil', 'EWT': 'ETF Taiwan',
    },
    'top_aziende': {
        'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
        'AMZN': 'Amazon', 'NVDA': 'Nvidia', 'META': 'Meta',
        'TSLA': 'Tesla', 'BRK-B': 'Berkshire', 'AVGO': 'Broadcom',
        'LLY': 'Eli Lilly', 'WMT': 'Walmart', 'JPM': 'JPMorgan',
        'V': 'Visa', 'UNH': 'UnitedHealth', 'MA': 'Mastercard',
        'HD': 'Home Depot', 'PG': 'P&G', 'XOM': 'Exxon',
        'ORCL': 'Oracle', 'COST': 'Costco', 'BAC': 'Bank of America',
        'NFLX': 'Netflix', 'ABBV': 'AbbVie', 'CRM': 'Salesforce',
        'CVX': 'Chevron', 'KO': 'Coca-Cola', 'AMD': 'AMD',
        'PEP': 'PepsiCo', 'TMO': 'Thermo Fisher', 'WFC': 'Wells Fargo',
        'CSCO': 'Cisco', 'LIN': 'Linde', 'MCD': 'McDonald\'s',
        'ACN': 'Accenture', 'ABT': 'Abbott', 'ADBE': 'Adobe',
        'DIS': 'Disney', 'TMUS': 'T-Mobile', 'INTC': 'Intel',
        'IBM': 'IBM', 'QCOM': 'Qualcomm', 'TXN': 'Texas Instruments',
        'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley', 'BLK': 'BlackRock',
        'AXP': 'Amex', 'JNJ': 'Johnson & Johnson', 'PFE': 'Pfizer',
        'MRK': 'Merck', 'NKE': 'Nike', 'BA': 'Boeing',
        'CAT': 'Caterpillar', 'GE': 'GE', 'HON': 'Honeywell',
        'PYPL': 'PayPal', 'UBER': 'Uber', 'ABNB': 'Airbnb',
        'CRWD': 'CrowdStrike', 'PANW': 'Palo Alto', 'NET': 'Cloudflare',
        'SNOW': 'Snowflake', 'PLTR': 'Palantir', 'SQ': 'Block',
        'COIN': 'Coinbase', 'SBUX': 'Starbucks', 'NOW': 'ServiceNow',
    },
    'materie_prime': {
        'GC=F': 'Oro', 'SI=F': 'Argento', 'CL=F': 'WTI',
        'BZ=F': 'Brent', 'NG=F': 'Gas Naturale', 'HG=F': 'Rame',
    },
    'crypto': {
        'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum',
        'SOL-USD': 'Solana', 'XRP-USD': 'Ripple',
        'DOGE-USD': 'Dogecoin',
    },
    'etf_settoriali': {
        'XLK': 'Technology', 'XLF': 'Financial', 'XLV': 'Healthcare',
        'XLE': 'Energy', 'XLI': 'Industrial', 'ARKK': 'Innovation',
        'SOXX': 'Semiconduttori', 'KWEB': 'Cina Internet',
    }
}

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    print("✅ Cache caricata")
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

def ottieni_prezzo_attuale(ticker_obj):
    """Ottiene il prezzo attuale in modo robusto"""
    try:
        hist = ticker_obj.history(period='1d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    
    try:
        info = ticker_obj.info
        for key in ['regularMarketPrice', 'currentPrice', 'previousClose']:
            if key in info and info[key]:
                return float(info[key])
    except:
        pass
    
    return None

def calcola_variazione(ticker_symbol, giorni):
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        ticker = yf.Ticker(ticker_symbol, session=session)
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=giorni + 15)
        hist = ticker.history(start=start_date, end=end_date, interval='1d')
        
        if hist.empty or len(hist) < 2:
            return None
        
        prezzo_iniziale = float(hist['Close'].iloc[0])
        prezzo_finale = float(hist['Close'].iloc[-1])
        
        if prezzo_iniziale == 0:
            return None
        
        return round(((prezzo_finale - prezzo_iniziale) / prezzo_iniziale) * 100, 2)
    except Exception as e:
        print(f"⚠️ Errore calcolo {ticker_symbol} ({giorni}g): {str(e)[:50]}")
        return None

def ottieni_dati_ticker(ticker_symbol, nome, categoria):
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        ticker = yf.Ticker(ticker_symbol, session=session)
        
        prezzo_attuale = ottieni_prezzo_attuale(ticker)
        
        market_cap = None
        try:
            info = ticker.info
            market_cap = info.get('marketCap', None)
        except:
            pass
        
        periodi = {
            '1_settimana': 7, '1_mese': 30, '3_mesi': 90,
            '6_mesi': 180, '12_mesi': 365, '18_mesi': 540, '24_mesi': 730
        }
        
        variazioni = {}
        for periodo_nome, giorni in periodi.items():
            variazioni[periodo_nome] = calcola_variazione(ticker_symbol, giorni)
        
        return {
            'ticker': ticker_symbol,
            'nome': nome,
            'categoria': categoria,
            'prezzo_attuale': round(prezzo_attuale, 2) if prezzo_attuale else None,
            'market_cap': market_cap,
            'variazioni': variazioni
        }
    except Exception as e:
        print(f"❌ Errore {ticker_symbol}: {str(e)[:100]}")
        return None

def ottieni_tutti_i_dati():
    cached = carica_cache()
    if cached:
        return cached
    
    print("🔄 Scaricamento dati in corso...")
    risultati = {}
    totale_falliti = 0
    
    for categoria, tickers in TICKERS.items():
        risultati[categoria] = []
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # Ridotto da 15 a 5 per evitare rate-limit
            futures = []
            for ticker, nome in tickers.items():
                future = executor.submit(ottieni_dati_ticker, ticker, nome, categoria)
                futures.append((ticker, future))
            
            for ticker, future in futures:
                try:
                    result = future.result(timeout=30)
                    if result and result.get('prezzo_attuale'):
                        risultati[categoria].append(result)
                    else:
                        totale_falliti += 1
                        print(f"⚠️ Nessun dato per {ticker}")
                except Exception as e:
                    totale_falliti += 1
                    print(f"❌ Timeout/Errore per {ticker}: {str(e)[:50]}")
    
    print(f"✅ Caricamento completato. Successi: {sum(len(v) for v in risultati.values())}, Falliti: {totale_falliti}")
    salva_cache(risultati)
    return risultati

# ============================================================================
# ROUTE
# ============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health():
    """Endpoint per verificare che il server funzioni"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'cache_exists': os.path.exists(CACHE_FILE)
    })

@app.route('/api/dati')
def api_dati():
    return jsonify(ottieni_tutti_i_dati())

@app.route('/api/peggiori/<periodo>')
def api_peggiori(periodo):
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    periodo_nome = periodo_mappatura.get(periodo, '3_mesi')
    dati = ottieni_tutti_i_dati()
    
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
    periodo_mappatura = {
        '1s': '1_settimana', '1m': '1_mese', '3m': '3_mesi',
        '6m': '6_mesi', '12m': '12_mesi', '18m': '18_mesi', '24m': '24_mesi'
    }
    
    periodo_nome = periodo_mappatura.get(periodo, '3_mesi')
    dati = ottieni_tutti_i_dati()
    
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
    dati = ottieni_tutti_i_dati()
    
    titoli_con_cap = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            if titolo.get('market_cap'):
                titoli_con_cap.append({
                    'ticker': titolo['ticker'],
                    'nome': titolo['nome'],
                    'categoria': categoria.replace('_', ' ').title(),
                    'prezzo': titolo['prezzo_attuale'],
                    'market_cap': titolo['market_cap'],
                    'variazione_6m': titolo['variazioni'].get('6_mesi'),
                    'variazione_12m': titolo['variazioni'].get('12_mesi')
                })
    
    titoli_con_cap.sort(key=lambda x: x['market_cap'], reverse=True)
    return jsonify(titoli_con_cap[:50])

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
    print("🚀 Avvio AssetScope...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
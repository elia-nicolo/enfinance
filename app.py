from flask import Flask, jsonify, render_template
import yfinance as yf
import json
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading

app = Flask(__name__)

CACHE_FILE = 'cache_dati.json'
CACHE_DURATION = 900  # 15 minuti

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
        'EPI': 'ETF India WisdomTree', 'TUR': 'ETF Turkey',
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
        'UPS': 'UPS', 'RTX': 'Raytheon', 'LMT': 'Lockheed',
        'T': 'AT&T', 'VZ': 'Verizon', 'PYPL': 'PayPal',
        'UBER': 'Uber', 'ABNB': 'Airbnb', 'SPOT': 'Spotify',
        'CRWD': 'CrowdStrike', 'PANW': 'Palo Alto', 'NET': 'Cloudflare',
        'SNOW': 'Snowflake', 'PLTR': 'Palantir', 'SQ': 'Block',
        'COIN': 'Coinbase', 'BKNG': 'Booking', 'SBUX': 'Starbucks',
        'TGT': 'Target', 'LOW': 'Lowe\'s', 'NOW': 'ServiceNow',
    },
    'materie_prime': {
        'GC=F': 'Oro', 'SI=F': 'Argento', 'CL=F': 'WTI',
        'BZ=F': 'Brent', 'NG=F': 'Gas Naturale', 'HG=F': 'Rame',
        'ZC=F': 'Mais', 'KC=F': 'Caffè',
    },
    'crypto': {
        'BTC-USD': 'Bitcoin', 'ETH-USD': 'Ethereum',
        'SOL-USD': 'Solana', 'XRP-USD': 'Ripple',
        'ADA-USD': 'Cardano', 'DOGE-USD': 'Dogecoin',
    },
    'etf_settoriali': {
        'XLK': 'Technology', 'XLF': 'Financial', 'XLV': 'Healthcare',
        'XLE': 'Energy', 'XLI': 'Industrial', 'ARKK': 'Innovation',
        'SOXX': 'Semiconduttori', 'KWEB': 'Cina Internet',
        'TAN': 'Solare', 'LIT': 'Litio',
    }
}

def carica_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    return data['dati']
        except:
            pass
    return None

def salva_cache(dati):
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({'timestamp': time.time(), 'dati': dati}, f)
    except:
        pass

def calcola_variazione(ticker_symbol, giorni):
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
        
        return round(((prezzo_finale - prezzo_iniziale) / prezzo_iniziale) * 100, 2)
    except:
        return None

def ottieni_dati_ticker(ticker_symbol, nome, categoria):
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
            variazioni[periodo_nome] = calcola_variazione(ticker_symbol, giorni)
        
        return {
            'ticker': ticker_symbol,
            'nome': nome,
            'categoria': categoria,
            'prezzo_attuale': round(prezzo_attuale, 2) if prezzo_attuale else None,
            'market_cap': market_cap,
            'variazioni': variazioni
        }
    except:
        return None

def ottieni_tutti_i_dati():
    cached = carica_cache()
    if cached:
        return cached
    
    risultati = {}
    
    for categoria, tickers in TICKERS.items():
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
    
    salva_cache(risultati)
    return risultati

@app.route('/')
def index():
    return render_template('index.html')

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
                    'categoria': categoria,
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
                    'categoria': categoria,
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
                    'categoria': categoria,
                    'prezzo': titolo['prezzo_attuale'],
                    'market_cap': titolo['market_cap'],
                    'variazione_6m': titolo['variazioni'].get('6_mesi'),
                    'variazione_12m': titolo['variazioni'].get('12_mesi')
                })
    
    titoli_con_cap.sort(key=lambda x: x['market_cap'], reverse=True)
    return jsonify(titoli_con_cap[:50])

if __name__ == '__main__':
    print("🚀 Avvio e pre-caricamento cache...")
    ottieni_tutti_i_dati()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
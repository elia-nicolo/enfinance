from flask import Flask, jsonify, render_template
import yfinance as yf
import json
import os
import time
import threading
from datetime import datetime

app = Flask(__name__)

CACHE_FILE = 'cache_dati.json'
CACHE_DURATION = 900  # 15 minuti

# Stato globale del caricamento
stato = {
    'in_corso': False, 
    'completato': False, 
    'errore': None, 
    'progresso': 0,
    'ultimo_aggiornamento': None
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
    """Carica dati dalla cache se valida"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_DURATION:
                    return data['dati']
        except Exception as e:
            print(f"Errore lettura cache: {e}")
    return None

def salva_cache(dati):
    """Salva dati nella cache"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump({
                'timestamp': time.time(), 
                'dati': dati
            }, f)
        print("✅ Cache salvata")
    except Exception as e:
        print(f"Errore salvataggio cache: {e}")

def download_e_elabora():
    """Scarica TUTTI i dati in una singola richiesta batch"""
    global stato
    
    try:
        stato['in_corso'] = True
        stato['errore'] = None
        stato['progresso'] = 10
        
        # Costruisci mappa ticker -> (nome, categoria)
        ticker_map = {}
        for cat, tickers in TICKERS.items():
            for t, nome in tickers.items():
                ticker_map[t] = (nome, cat)
        
        ticker_list = list(ticker_map.keys())
        print(f"🔄 Download batch di {len(ticker_list)} ticker...")
        
        # UNA SOLA RICHIESTA per tutti i ticker (invece di centinaia)
        data = yf.download(
            ticker_list,
            period="2y",
            interval="1d",
            group_by='ticker',
            auto_adjust=True,
            threads=True,
            progress=False
        )
        
        stato['progresso'] = 40
        print(f"✅ Download completato. Shape: {data.shape}")
        
        if data.empty:
            raise Exception("Nessun dato ricevuto da Yahoo Finance")
        
        # Giorni di TRADING per periodo (non di calendario)
        periodi_trading = {
            '1_settimana': 5,
            '1_mese': 21,
            '3_mesi': 63,
            '6_mesi': 126,
            '12_mesi': 252,
            '18_mesi': 378,
            '24_mesi': 504
        }
        
        risultati = {cat: [] for cat in TICKERS}
        
        for ticker_symbol in ticker_list:
            try:
                # Gestione DataFrame MultiIndex
                if isinstance(data.columns, pd.MultiIndex):
                    if ticker_symbol not in data.columns.get_level_values(0):
                        continue
                    hist = data[ticker_symbol]
                else:
                    hist = data
                
                if 'Close' not in hist.columns:
                    continue
                
                closes = hist['Close'].dropna()
                if len(closes) < 5:
                    continue
                
                prezzo_attuale = round(float(closes.iloc[-1]), 2)
                
                # Calcola tutte le variazioni dalla stessa serie storica
                variazioni = {}
                for nome_p, giorni_t in periodi_trading.items():
                    if len(closes) > giorni_t:
                        p_iniz = float(closes.iloc[-giorni_t])
                        p_fin = float(closes.iloc[-1])
                        if p_iniz != 0:
                            variazioni[nome_p] = round(((p_fin - p_iniz) / p_iniz) * 100, 2)
                        else:
                            variazioni[nome_p] = None
                    else:
                        variazioni[nome_p] = None
                
                nome, categoria = ticker_map[ticker_symbol]
                
                # Market cap (opzionale, veloce)
                market_cap = None
                try:
                    fast = yf.Ticker(ticker_symbol).fast_info
                    market_cap = getattr(fast, 'market_cap', None)
                except:
                    pass
                
                risultati[categoria].append({
                    'ticker': ticker_symbol,
                    'nome': nome,
                    'categoria': categoria,
                    'prezzo_attuale': prezzo_attuale,
                    'market_cap': market_cap,
                    'variazioni': variazioni
                })
                
            except Exception as e:
                print(f"⚠️ Errore elaborazione {ticker_symbol}: {e}")
                continue
        
        stato['progresso'] = 90
        
        # Conta i risultati
        totale = sum(len(v) for v in risultati.values())
        print(f"✅ Elaborati {totale} ticker con successo")
        
        salva_cache(risultati)
        
        stato['completato'] = True
        stato['progresso'] = 100
        stato['ultimo_aggiornamento'] = datetime.now().isoformat()
        
    except Exception as e:
        print(f"❌ Errore nel download: {e}")
        stato['errore'] = str(e)
    finally:
        stato['in_corso'] = False

def avvia_background():
    """Avvia il download in un thread di background"""
    if not stato['in_corso'] and not stato['completato']:
        print("🚀 Avvio download in background...")
        t = threading.Thread(target=download_e_elabora, daemon=True)
        t.start()

# All'avvio: prova la cache, altrimenti avvia download
cache_iniziale = carica_cache()
if cache_iniziale is not None:
    stato['completato'] = True
    stato['progresso'] = 100
    stato['ultimo_aggiornamento'] = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).isoformat()
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
    """Endpoint per verificare lo stato del caricamento"""
    return jsonify(stato)

@app.route('/api/peggiori/<periodo>')
def api_peggiori(periodo):
    # Controlla se i dati sono pronti
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        # Cache scaduta, riavvia download
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
    if not stato['completato']:
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
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
    print("🚀 Avvio AssetScope...")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
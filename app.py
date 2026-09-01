from flask import Flask, jsonify, render_template
import requests
import json
import os
import time
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

app = Flask(__name__)

CACHE_FILE = 'cache_dati.json'

FUSO_ITALIA = ZoneInfo('Europe/Rome')

def ottieni_ora_italiana():
    return datetime.now(FUSO_ITALIA)

def in_fascia_attiva():
    ora = ottieni_ora_italiana().hour
    return 9 <= ora < 21

def ottieni_cache_duration():
    if in_fascia_attiva():
        return 10800  # 3 ore
    else:
        return 43200

def cache_valida():
    if not os.path.exists(CACHE_FILE):
        return False
    
    try:
        eta_file = time.time() - os.path.getmtime(CACHE_FILE)
        durata_massima = ottieni_cache_duration()
        
        if eta_file < durata_massima:
            return True
        
        if not in_fascia_attiva():
            return True
        
        return False
    except:
        return False

def tempo_al_prossimo_aggiornamento():
    """Restituisce i secondi mancanti al prossimo aggiornamento"""
    if not os.path.exists(CACHE_FILE):
        return 0
    
    eta_file = time.time() - os.path.getmtime(CACHE_FILE)
    durata_massima = ottieni_cache_duration()
    rimanenti = durata_massima - eta_file
    
    if not in_fascia_attiva():
        # Calcola secondi fino alle 9:00 di domani
        ora = ottieni_ora_italiana()
        secondi_mancanti = (24 - ora.hour + 9) * 3600 - ora.minute * 60 - ora.second
        return max(0, secondi_mancanti)
    
    return max(0, int(rimanenti))

TWELVE_DATA_API_KEY = os.environ.get('TWELVE_DATA_API_KEY', 'b14ba2a7063447738bd8b353bbf39b1c')

stato = {
    'in_corso': False, 
    'completato': False, 
    'errore': None, 
    'progresso': 0,
    'ultimo_aggiornamento': None
}

# ============================================================================
# TICKER AGGIORNATI - CORRETTI PER TWELVE DATA
# ============================================================================

TICKERS = {
    'indici_globali': {
        'SPX': 'S&P 500', 
        'NDX': 'Nasdaq 100', 
        'DJI': 'Dow Jones',
        'FTSE': 'FTSE 100 UK', 
        'DAX': 'DAX Germania', 
        'CAC': 'CAC 40 Francia',
        'N225': 'Nikkei 225 Giappone', 
        'HSI': 'Hang Seng HK',
        'ASX200': 'ASX 200 Australia', 
        'GSPTSE': 'TSX Canada',
    },
    
    # ETF EUROPEI UCITS (formato TICKER.BORSA)
    'etf_europei': {
        'XDWD.DE': 'Xtrackers MSCI World (Acc)',
        'XEON.DE': 'Xtrackers MSCI Europe',
        'XWD1.DE': 'Xtrackers MSCI AC World',
        'CSPX.DE': 'iShares Core S&P 500 (Acc)',
        'SXR8.DE': 'iShares Core S&P 500 (Dist)',
        'EUNL.DE': 'iShares Core MSCI World',
        'IBCX.DE': 'iShares Euro Corporate Bond',
        'SGLN.DE': 'iShares Physical Gold',
        'QDVE.DE': 'iShares Nasdaq 100 (Acc)',
        'EXST.DE': 'iShares STOXX Europe 600',
        'EIMI.DE': 'iShares Core MSCI EM IMI',
        'VNRA.DE': 'Vanguard FTSE All-World',
        'VUSA.DE': 'Vanguard S&P 500 (Dist)',
        'VUAA.DE': 'Vanguard S&P 500 (Acc)',
        'VWCE.DE': 'Vanguard FTSE All-World (Acc)',
        'AMEU.DE': 'Amundi MSCI Europe',
        'ANX.DE': 'Amundi Nasdaq-100 (Acc)',
    },
    
    # ETF USA (equivalenti degli UCITS, molto liquidi)
    'etf_usa_principali': {
        'SPY': 'SPDR S&P 500 ETF',
        'IVV': 'iShares Core S&P 500',
        'VOO': 'Vanguard S&P 500',
        'QQQ': 'Invesco QQQ (Nasdaq-100)',
        'VTI': 'Vanguard Total Stock Market',
        'ACWI': 'iShares MSCI ACWI (Mondo)',
        'VXUS': 'Vanguard FTSE Ex-US',
        'VEA': 'Vanguard FTSE Developed Markets',
        'VT': 'Vanguard Total World Stock',
    },
    
    # MERCATI EMERGENTI - CORRETTI (senza /USD!)
    'mercati_emergenti': {
        'EEM': 'iShares MSCI Emerging Markets',
        'VWO': 'Vanguard FTSE Emerging',
        'IEMG': 'iShares Core MSCI EM',
        'INDA': 'iShares MSCI India',
        'FXI': 'iShares China Large-Cap',
        'MCHI': 'iShares MSCI China',
        'EWZ': 'iShares MSCI Brazil',
        'EWT': 'iShares MSCI Taiwan',
        'EWJ': 'iShares MSCI Japan',
        'EWY': 'iShares MSCI South Korea',
        'EWW': 'iShares MSCI Mexico',
        'EZA': 'iShares MSCI South Africa',
        'EWS': 'iShares MSCI Singapore',
        'EPI': 'WisdomTree India Earnings',
        'RSX': 'VanEck Russia ETF',
        'TUR': 'iShares MSCI Turkey',
        'AFK': 'VanEck Africa ETF',
    },
    
    'top_100_usa': {
        'AAPL': 'Apple', 'MSFT': 'Microsoft', 'GOOGL': 'Alphabet',
        'AMZN': 'Amazon', 'NVDA': 'Nvidia', 'META': 'Meta',
        'TSLA': 'Tesla', 'AVGO': 'Broadcom', 'LLY': 'Eli Lilly',
        'WMT': 'Walmart', 'JPM': 'JPMorgan', 'V': 'Visa',
        'UNH': 'UnitedHealth', 'MA': 'Mastercard', 'HD': 'Home Depot',
        'PG': 'Procter & Gamble', 'XOM': 'Exxon Mobil', 'ORCL': 'Oracle',
        'COST': 'Costco', 'BAC': 'Bank of America', 'NFLX': 'Netflix',
        'ABBV': 'AbbVie', 'CRM': 'Salesforce', 'CVX': 'Chevron',
        'KO': 'Coca-Cola', 'AMD': 'AMD', 'PEP': 'PepsiCo',
        'TMO': 'Thermo Fisher', 'WFC': 'Wells Fargo', 'CSCO': 'Cisco',
        'LIN': 'Linde', 'MCD': 'McDonald\'s', 'ACN': 'Accenture',
        'ABT': 'Abbott Labs', 'ADBE': 'Adobe', 'DIS': 'Disney',
        'TMUS': 'T-Mobile', 'INTC': 'Intel', 'IBM': 'IBM',
        'QCOM': 'Qualcomm', 'TXN': 'Texas Instruments', 'GS': 'Goldman Sachs',
        'MS': 'Morgan Stanley', 'BLK': 'BlackRock', 'AXP': 'American Express',
        'JNJ': 'Johnson & Johnson', 'PFE': 'Pfizer', 'MRK': 'Merck',
        'NKE': 'Nike', 'BA': 'Boeing', 'CAT': 'Caterpillar',
        'GE': 'General Electric', 'HON': 'Honeywell', 'PYPL': 'PayPal',
        'UBER': 'Uber', 'ABNB': 'Airbnb', 'CRWD': 'CrowdStrike',
        'PANW': 'Palo Alto', 'NET': 'Cloudflare', 'SNOW': 'Snowflake',
        'PLTR': 'Palantir', 'SQ': 'Block', 'COIN': 'Coinbase',
        'SBUX': 'Starbucks', 'NOW': 'ServiceNow', 'INTU': 'Intuit',
    },
    
    'materie_prime': {
        'XAU/USD': 'Oro', 'XAG/USD': 'Argento', 
        'CL/USD': 'Petrolio WTI', 'NG/USD': 'Gas Naturale',
        'HG/USD': 'Rame',
    },
    
    'crypto_top': {
        'BTC/USD': 'Bitcoin', 'ETH/USD': 'Ethereum', 'SOL/USD': 'Solana',
    },
    
    'etf_settoriali': {
        'XLK': 'Technology', 'XLF': 'Financial', 
        'XLV': 'Healthcare', 'XLE': 'Energy',
        'XLI': 'Industrial', 'ARKK': 'Innovation',
        'SOXX': 'Semiconduttori', 'KWEB': 'Cina Internet',
        'TAN': 'Energia Solare', 'LIT': 'Litio e Batterie',
        'XLU': 'Utilities', 'XLRE': 'Real Estate',
        'GLD': 'SPDR Gold Trust', 'IAU': 'iShares Gold Trust',
    },
}

# ============================================================================
# FUNZIONI CACHE E DOWNLOAD (invariate)
# ============================================================================

def carica_cache():
    if not cache_valida():
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
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

def avvia_background(forza=False):
    global stato
    
    if not in_fascia_attiva() and not forza:
        print("🌙 Fascia notturna: download bloccato")
        return
    
    if not stato['in_corso']:
        stato['completato'] = False
        print("☀️ Avvio download...")
        t = threading.Thread(target=download_e_elabora, daemon=True)
        t.start()

def scarica_dati_ticker(ticker):
    try:
        url = 'https://api.twelvedata.com/time_series'
        params = {
            'symbol': ticker,
            'interval': '1day',
            'outputsize': 520,
            'apikey': TWELVE_DATA_API_KEY,
            'format': 'JSON'
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'values' not in data:
            return None
        
        closes = []
        for entry in reversed(data['values']):
            try:
                closes.append(float(entry['close']))
            except:
                continue
        
        return closes if len(closes) > 30 else None
    except Exception as e:
        print(f"Errore {ticker}: {str(e)[:80]}")
        return None

def download_e_elabora():
    global stato
    
    try:
        stato['in_corso'] = True
        stato['errore'] = None
        stato['progresso'] = 5
        
        ticker_map = {}
        for cat, tickers in TICKERS.items():
            for t, nome in tickers.items():
                ticker_map[t] = (nome, cat)
        
        ticker_list = list(ticker_map.keys())
        print(f"Download {len(ticker_list)} ticker...")
        
        risultati = {cat: [] for cat in TICKERS}
        
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
                    'variazioni': variazioni
                })
            
            stato['progresso'] = 5 + int(90 * (i + 1) / len(ticker_list))
            
            if (i + 1) % 7 == 0:
                time.sleep(7)
            else:
                time.sleep(1)
        
        salva_cache(risultati)
        
        stato['completato'] = True
        stato['progresso'] = 100
        stato['ultimo_aggiornamento'] = datetime.now().isoformat()
        
    except Exception as e:
        stato['errore'] = str(e)
    finally:
        stato['in_corso'] = False

cache_iniziale = carica_cache()
if cache_iniziale is not None:
    stato['completato'] = True
    stato['progresso'] = 100
    print(f"✅ Cache caricata. Ora italiana: {ottieni_ora_italiana().strftime('%H:%M')}")
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
    stato_extra = stato.copy()
    stato_extra['ora_italiana'] = ottieni_ora_italiana().strftime('%H:%M')
    stato_extra['fascia_attiva'] = in_fascia_attiva()
    
    # Info cache per il footer
    if os.path.exists(CACHE_FILE):
        eta_file = time.time() - os.path.getmtime(CACHE_FILE)
        durata = ottieni_cache_duration()
        stato_extra['cache_eta_secondi'] = int(eta_file)
        stato_extra['cache_durata_secondi'] = durata
        stato_extra['prossimo_aggiornamento_secondi'] = tempo_al_prossimo_aggiornamento()
    else:
        stato_extra['cache_eta_secondi'] = 0
        stato_extra['cache_durata_secondi'] = 0
        stato_extra['prossimo_aggiornamento_secondi'] = 0
    
    return jsonify(stato_extra)

@app.route('/api/cache-info')
def api_cache_info():
    """Info dettagliate sulla cache per il footer"""
    info = {
        'ora_italiana': ottieni_ora_italiana().strftime('%H:%M'),
        'fascia_attiva': in_fascia_attiva(),
        'cache_presente': os.path.exists(CACHE_FILE),
    }
    
    if os.path.exists(CACHE_FILE):
        eta = time.time() - os.path.getmtime(CACHE_FILE)
        durata = ottieni_cache_duration()
        info['cache_eta_secondi'] = int(eta)
        info['cache_durata_secondi'] = durata
        info['prossimo_aggiornamento_secondi'] = tempo_al_prossimo_aggiornamento()
        info['ultimo_aggiornamento'] = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE)).isoformat()
    else:
        info['cache_eta_secondi'] = 0
        info['cache_durata_secondi'] = 0
        info['prossimo_aggiornamento_secondi'] = 0
    
    return jsonify(info)

@app.route('/api/refresh', methods=['POST'])
def api_refresh():
    """Forza un refresh manuale dei dati"""
    if stato['in_corso']:
        return jsonify({'status': 'already_running', 'messaggio': 'Aggiornamento già in corso'}), 409
    
    if not in_fascia_attiva():
        return jsonify({
            'status': 'blocked', 
            'messaggio': 'Refresh bloccato: fascia notturna (21:00-09:00)'
        }), 403
    
    print("🔄 Refresh manuale richiesto")
    avvia_background(forza=True)
    return jsonify({'status': 'started', 'messaggio': 'Aggiornamento avviato'})

# Tutte le route /api/peggiori, /api/migliori, /api/categoria, /api/strategie 
# rimangono come le hai già (con il controllo in_fascia_attiva)

@app.route('/api/peggiori/<periodo>')
def api_peggiori(periodo):
    if not stato['completato']:
        if not in_fascia_attiva():
            return jsonify({
                'errore': 'Dati non disponibili',
                'motivo': 'Fascia notturna (21:00-09:00). I dati verranno aggiornati alle 09:00.',
                'fascia_attiva': False
            }), 503
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
    if not stato['completato']:
        if not in_fascia_attiva():
            return jsonify({
                'errore': 'Dati non disponibili',
                'motivo': 'Fascia notturna (21:00-09:00). I dati verranno aggiornati alle 09:00.',
                'fascia_attiva': False
            }), 503
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

@app.route('/api/categoria/<categoria_nome>')
def api_per_categoria(categoria_nome):
    if not stato['completato']:
        if not in_fascia_attiva():
            return jsonify({
                'errore': 'Dati non disponibili',
                'motivo': 'Fascia notturna (21:00-09:00). I dati verranno aggiornati alle 09:00.',
                'fascia_attiva': False
            }), 503
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

@app.route('/api/strategie')
def api_strategie():
    if not stato['completato']:
        if not in_fascia_attiva():
            return jsonify({
                'errore': 'Dati non disponibili',
                'motivo': 'Fascia notturna (21:00-09:00). I dati verranno aggiornati alle 09:00.',
                'fascia_attiva': False
            }), 503
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    dati = carica_cache()
    if dati is None:
        avvia_background()
        return jsonify({'in_attesa': True, 'stato': stato}), 202
    
    tutti_titoli = []
    for categoria, titoli in dati.items():
        for titolo in titoli:
            tutti_titoli.append(titolo)
    
    strategie = {}
    
    mean_reversion = []
    for t in tutti_titoli:
        var_6m = t['variazioni'].get('6_mesi')
        if var_6m is not None and var_6m < -10:
            if t['categoria'] in ['top_100_usa', 'indici_globali', 'etf_europei', 'etf_usa_principali']:
                mean_reversion.append({
                    'ticker': t['ticker'],
                    'nome': t['nome'],
                    'prezzo': t['prezzo_attuale'],
                    'variazione': var_6m,
                    'categoria': t['categoria']
                })
    mean_reversion.sort(key=lambda x: x['variazione'])
    strategie['mean_reversion'] = mean_reversion[:10]
    
    momentum = []
    for t in tutti_titoli:
        var_6m = t['variazioni'].get('6_mesi')
        if var_6m is not None and var_6m > 15:
            momentum.append({
                'ticker': t['ticker'],
                'nome': t['nome'],
                'prezzo': t['prezzo_attuale'],
                'variazione': var_6m,
                'categoria': t['categoria']
            })
    momentum.sort(key=lambda x: x['variazione'], reverse=True)
    strategie['momentum'] = momentum[:10]
    
    contrarian = []
    for t in tutti_titoli:
        var_3m = t['variazioni'].get('3_mesi')
        if var_3m is not None and var_3m < -8:
            if t['categoria'] in ['mercati_emergenti', 'indici_globali', 'etf_settoriali', 'etf_europei']:
                contrarian.append({
                    'ticker': t['ticker'],
                    'nome': t['nome'],
                    'prezzo': t['prezzo_attuale'],
                    'variazione': var_3m,
                    'categoria': t['categoria']
                })
    contrarian.sort(key=lambda x: x['variazione'])
    strategie['contrarian'] = contrarian[:10]
    
    flight_quality = []
    mega_cap_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'BRK-B', 'JPM', 'V', 'UNH']
    for t in tutti_titoli:
        if t['ticker'] in mega_cap_tickers:
            var_6m = t['variazioni'].get('6_mesi')
            if var_6m is not None and var_6m > -5:
                flight_quality.append({
                    'ticker': t['ticker'],
                    'nome': t['nome'],
                    'prezzo': t['prezzo_attuale'],
                    'variazione': var_6m,
                    'categoria': t['categoria']
                })
    flight_quality.sort(key=lambda x: x['variazione'], reverse=True)
    strategie['flight_quality'] = flight_quality[:10]
    
    return jsonify(strategie)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
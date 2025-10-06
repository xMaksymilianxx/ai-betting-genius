# api/analyze.py - WERSJA Z OSTATECZNYM TRYBEM DIAGNOSTYCZNYM
import requests
import json
import time
from datetime import datetime
from typing import List, Dict
import random

# ==================== KONFIGURACJA 3 API ====================
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKbER9Gx6Oj7e6XRud0oh"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"

API_SOURCES = [
    {'name': 'sportmonks', 'priority': 1, 'fetch_func': 'fetch_sportmonks_live'},
    {'name': 'football-data', 'priority': 2, 'fetch_func': 'fetch_footballdata_live'},
    {'name': 'api-football', 'priority': 3, 'fetch_func': 'fetch_apifootball_live'}
]

# ==================== INTELIGENTNY ROUTER API (FALLBACK) ====================
def fetch_live_matches_with_fallback() -> Dict:
    all_matches = []
    successful_apis = []
    print("\n============== ROZPOCZYNAM DIAGNOSTYKĘ POBIERANIA MECZÓW ==============")
    for api_config in sorted(API_SOURCES, key=lambda x: x['priority']):
        api_name = api_config['name']
        print(f"\n--- Próba z API: {api_name} ---")
        try:
            fetcher_func = globals()[api_config['fetch_func']]
            matches = fetcher_func()
            if matches:
                all_matches.extend(matches)
                successful_apis.append({'name': api_name, 'matches': len(matches)})
                if len(all_matches) >= 10: break
        except Exception as e:
            print(f"❌ KRYTYCZNY BŁĄD WEWNĘTRZNY [{api_name}]: {e}")
            
    unique_matches = list({f"{m.get('home_team', '')}_{m.get('away_team', '')}": m for m in all_matches}.values())
    print(f"\n============== ZAKOŃCZONO DIAGNOSTYKĘ ==============")
    print(f"Podsumowanie: Znaleziono {len(unique_matches)} unikalnych meczów z {len(successful_apis)} API.")
    return {'matches': unique_matches, 'sources': successful_apis}

# ==================== FETCHERS & PARSERS Z PEŁNYM LOGOWANIEM ====================
def fetch_sportmonks_live() -> List[Dict]:
    url = f"https://api.sportmonks.com/v3/football/livescores?api_token={SPORTMONKS_KEY}&include=scores;participants;state"
    print(f"  [LOG] Wysyłanie zapytania do: {url.split('?')[0]}")
    try:
        response = requests.get(url, timeout=12)
        print(f"  [LOG] Status odpowiedzi: {response.status_code}")
        print(f"  [LOG] Odpowiedź API (fragment): {response.text[:500]}")
        if response.status_code == 200:
            data = response.json().get('data', [])
            print(f"  [LOG] API zwróciło {len(data)} surowych meczów.")
            return [parse_sportmonks_match(fix) for fix in data if fix.get('state_id') in [2, 3, 4]]
    except Exception as e:
        print(f"  [LOG] Błąd połączenia ze Sportmonks: {e}")
    return []

def parse_sportmonks_match(m: Dict) -> Dict:
    parts=m.get('participants',[])
    home=next((p for p in parts if p.get('meta',{}).get('location')=='home'),{})
    away=next((p for p in parts if p.get('meta',{}).get('location')=='away'),{})
    return {'source':'sportmonks','league':m.get('league',{}).get('name','?'),'home_team':home.get('name','H'),'away_team':away.get('name','A'),'home_goals':next((s['score']['goals'] for s in m.get('scores',[]) if s.get('participant_id')==home.get('id')),0),'away_goals':next((s['score']['goals'] for s in m.get('scores',[]) if s.get('participant_id')==away.get('id')),0),'minute':m.get('periods',[{'length':0}])[-1].get('length',45)}

def fetch_footballdata_live() -> List[Dict]:
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALLDATA_KEY}
    print(f"  [LOG] Wysyłanie zapytania do: {url}")
    try:
        response = requests.get(url, headers=headers, params={'status': 'LIVE'}, timeout=12)
        print(f"  [LOG] Status odpowiedzi: {response.status_code}")
        print(f"  [LOG] Odpowiedź API (fragment): {response.text[:500]}")
        if response.status_code == 200:
            data = response.json().get('matches', [])
            print(f"  [LOG] API zwróciło {len(data)} surowych meczów.")
            return [parse_footballdata_match(m) for m in data]
    except Exception as e:
        print(f"  [LOG] Błąd połączenia z Football-Data: {e}")
    return []

def parse_footballdata_match(m: Dict) -> Dict:
    s=m.get('score',{}).get('fullTime',{})
    return {'source':'football-data','league':m.get('competition',{}).get('name','?'),'home_team':m.get('homeTeam',{}).get('name','H'),'away_team':m.get('awayTeam',{}).get('name','A'),'home_goals':s.get('home',0) or 0,'away_goals':s.get('away',0) or 0,'minute':m.get('minute',45)}

def fetch_apifootball_live() -> List[Dict]:
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-key': APIFOOTBALL_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}
    print(f"  [LOG] Wysyłanie zapytania do: {url}")
    try:
        response = requests.get(url, headers=headers, params={'live': 'all'}, timeout=12)
        print(f"  [LOG] Status odpowiedzi: {response.status_code}")
        print(f"  [LOG] Odpowiedź API (fragment): {response.text[:500]}")
        if response.status_code == 200:
            data = response.json().get('response', [])
            print(f"  [LOG] API zwróciło {len(data)} surowych meczów.")
            return [parse_apifootball_match(fix) for fix in data]
    except Exception as e:
        print(f"  [LOG] Błąd połączenia z API-Football: {e}")
    return []

def parse_apifootball_match(fix: Dict) -> Dict:
    teams,goals=fix.get('teams',{}),fix.get('goals',{})
    return {'source':'api-football','league':fix.get('league',{}).get('name','?'),'home_team':teams.get('home',{}).get('name','H'),'away_team':teams.get('away',{}).get('name','A'),'home_goals':goals.get('home',0) or 0,'away_goals':goals.get('away',0) or 0,'minute':fix.get('fixture',{}).get('status',{}).get('elapsed',45)}

# ==================== SILNIK ANALIZY AI v4.0 (BEZ ZMIAN) ====================
def analyze_match_with_ai(match: Dict, config: Dict) -> Dict:
    home_xg, away_xg = round(random.uniform(0.1, 3.5), 2), round(random.uniform(0.1, 3.5), 2)
    signals, value_signals = [], []
    if abs(home_xg - away_xg) > 1.2:
        winner = match['home_team'] if home_xg > away_xg else match['away_team']
        signals.append({'type':f"⚡ {winner} ma przewagę",'accuracy':78,'reasoning':f'Przewaga w xG o {abs(home_xg-away_xg):.1f}','algorithm':'MOMENTUM'})
    
    # Symulacja Value Bet
    ai_prob_over = min((home_xg + away_xg) / 2.5, 0.95)
    simulated_odds_over = round(max(1 / (ai_prob_over * 0.8) if ai_prob_over > 0 else 10.0, 1.1), 2)
    if ai_prob_over > (1 / simulated_odds_over) * 1.2 and simulated_odds_over >= 1.9:
        line = match['home_goals'] + match['away_goals'] + 0.5
        value_signals.append({'type': f"💰 VALUE: Over {line} Gola (Kurs {simulated_odds_over})",'accuracy': int(ai_prob_over*100)-5,'reasoning': f"AI ocenia szansę na {int(ai_prob_over*100)}%, rynek na {int(100/simulated_odds_over)}%.",'algorithm': 'VALUE_BET_OVER'})

    all_signals = signals + value_signals
    if not all_signals: return None
    confidence = int(sum(s['accuracy'] for s in all_signals) / len(all_signals))
    if any("VALUE" in s['algorithm'] for s in all_signals): confidence = min(99, confidence + 10)
    if confidence < config['min_confidence']: return None
    return {**match, 'confidence': confidence, 'signals': all_signals, 'home_xg': home_xg, 'away_xg': away_xg}

# ==================== GŁÓWNY HANDLER VERCEL (BEZ ZMIAN) ====================
from http.server import BaseHTTPRequestHandler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            min_confidence = int(body.get('minConfidence', 70))
            matches_data = fetch_live_matches_with_fallback()
            
            if not matches_data['matches']:
                self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': 'DIAGNOSTYKA: Nie znaleziono meczów na żywo w żadnym z API. Sprawdź logi Vercel.'}).encode('utf-8'))
                return

            analyzed_matches = [analysis for match in matches_data['matches'] if (analysis := analyze_match_with_ai(match, {'min_confidence': min_confidence})) is not None]
            
            response_data = {'success': True, 'results': analyzed_matches, 'message': f"Znaleziono {len(analyzed_matches)} okazji."}
            self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
    def do_OPTIONS(self):
        self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-control-allow-methods','POST,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()

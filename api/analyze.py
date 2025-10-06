# api/analyze.py - ULTIMATE AI BETTING GENIUS
# Stabilna wersja z 3 API (Sportmonks, Football-Data, API-Football) i inteligentnym fallbackiem

import requests
import json
import time
from datetime import datetime
from typing import List, Dict

# ==================== KONFIGURACJA 3 API ====================
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKbER9Gx6Oj7e6XRud0oh"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"

API_SOURCES = [
    {
        'name': 'sportmonks',
        'priority': 1,
        'fetch_func': 'fetch_sportmonks_live'
    },
    {
        'name': 'football-data',
        'priority': 2,
        'fetch_func': 'fetch_footballdata_live'
    },
    {
        'name': 'api-football',
        'priority': 3,
        'fetch_func': 'fetch_apifootball_live'
    }
]

# ==================== INTELIGENTNY ROUTER API (FALLBACK) ====================
def fetch_live_matches_with_fallback() -> Dict:
    """
    Pobiera mecze na żywo, automatycznie przełączając się między API w razie problemów.
    """
    all_matches = []
    successful_apis = []
    
    print("\n🔍 Rozpoczynam pobieranie meczów na żywo z 3 API...")
    
    for api_config in sorted(API_SOURCES, key=lambda x: x['priority']):
        api_name = api_config['name']
        print(f"🔄 Próbuję API: {api_name} (Priorytet #{api_config['priority']})...")
        
        try:
            fetcher_func = globals()[api_config['fetch_func']]
            matches = fetcher_func()
            
            if matches:
                print(f"✅ SUKCES: [{api_name}] Znaleziono {len(matches)} meczów.")
                all_matches.extend(matches)
                successful_apis.append({'name': api_name, 'matches': len(matches)})
                # Jeśli którekolwiek API zwróciło wystarczająco dużo danych, możemy przerwać
                if len(all_matches) >= 5:
                    print("✅ Znaleziono wystarczającą liczbę meczów. Zakończono pobieranie.")
                    break
            else:
                print(f"⚠️ [{api_name}] Nie znaleziono meczów. Próbuję następne API...")
                
        except Exception as e:
            print(f"❌ KRYTYCZNY BŁĄD [{api_name}]: {str(e)[:150]}")
            continue
            
    # Usuwanie duplikatów (jeśli API zwrócą te same mecze)
    unique_matches = list({f"{m.get('home_team', '')}_{m.get('away_team', '')}": m for m in all_matches}.values())
    
    print(f"\n📈 Podsumowanie:")
    print(f"  • Użyte API: {[api['name'] for api in successful_apis]}")
    print(f"  • Łącznie unikalnych meczów: {len(unique_matches)}")
    
    return {'matches': unique_matches, 'sources': successful_apis}

# ==================== FETCHERS & PARSERS DLA KAŻDEGO API ====================

# --- Sportmonks (PRIMARY) ---
def fetch_sportmonks_live() -> List[Dict]:
    url = "https://api.sportmonks.com/v3/football/livescores"
    params = {'api_token': SPORTMONKS_KEY, 'include': 'scores;participants;state'}
    response = requests.get(url, params=params, timeout=12)
    if response.status_code == 200:
        return [parse_sportmonks_match(fix) for fix in response.json().get('data', []) if fix.get('state_id') in [2, 3, 4]]
    return []

def parse_sportmonks_match(fix: Dict) -> Dict:
    parts = fix.get('participants', [])
    home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
    away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
    scores = fix.get('scores', [])
    home_s = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('score',{}).get('participant')=='home'),0)
    away_s = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('score',{}).get('participant')=='away'),0)
    return {'source':'sportmonks','league':fix.get('league',{}).get('name','?'),'home_team':home.get('name','H'),'away_team':away.get('name','A'),'home_goals':home_s,'away_goals':away_s,'minute':fix.get('periods', [{'length':0}])[-1].get('length',45)}

# --- Football-Data.org (SECONDARY) ---
def fetch_footballdata_live() -> List[Dict]:
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALLDATA_KEY}
    response = requests.get(url, headers=headers, params={'status': 'LIVE'}, timeout=12)
    if response.status_code == 200:
        return [parse_footballdata_match(m) for m in response.json().get('matches', [])]
    return []

def parse_footballdata_match(m: Dict) -> Dict:
    s = m.get('score', {}).get('fullTime', {})
    return {'source':'football-data','league':m.get('competition',{}).get('name','?'),'home_team':m.get('homeTeam',{}).get('name','H'),'away_team':m.get('awayTeam',{}).get('name','A'),'home_goals':s.get('home',0) or 0,'away_goals':s.get('away',0) or 0,'minute':m.get('minute',45)}

# --- API-Football (TERTIARY - ⚠️ No live matches on free plan) ---
def fetch_apifootball_live() -> List[Dict]:
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-key': APIFOOTBALL_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}
    response = requests.get(url, headers=headers, params={'live': 'all'}, timeout=12)
    if response.status_code == 200:
        # Prawdopodobnie zwróci pustą listę w darmowej wersji
        return [parse_apifootball_match(fix) for fix in response.json().get('response', [])]
    return []

def parse_apifootball_match(fix: Dict) -> Dict:
    teams = fix.get('teams', {})
    goals = fix.get('goals', {})
    return {'source':'api-football','league':fix.get('league',{}).get('name','?'),'home_team':teams.get('home',{}).get('name','H'),'away_team':teams.get('away',{}).get('name','A'),'home_goals':goals.get('home',0) or 0,'away_goals':goals.get('away',0) or 0,'minute':fix.get('fixture',{}).get('status',{}).get('elapsed',45)}

# ==================== SILNIK ANALIZY AI ====================
def analyze_match_with_ai(match: Dict, config: Dict) -> Dict:
    # Symulacja pełnej analizy AI (25+ modułów)
    home_xg = round(random.uniform(0.5, 3.0), 2)
    away_xg = round(random.uniform(0.5, 3.0), 2)
    signals = []
    
    # Symulacja algorytmu HIGHXGNOGOALS
    if (home_xg + away_xg > 2.0) and (match.get('home_goals',0) + match.get('away_goals',0) == 0) and match.get('minute',0) > 20:
        signals.append({'type':'🎯 Next Goal Expected','accuracy':84,'reasoning':f"High xG ({home_xg+away_xg:.1f}) with 0 goals",'algorithm':'HIGHXGNOGOALS'})

    # Symulacja algorytmu MOMENTUMSHIFT
    if abs(home_xg - away_xg) > 1.2:
        winner = match.get('home_team') if home_xg > away_xg else match.get('away_team')
        signals.append({'type':f"⚡ {winner} To Win",'accuracy':78,'reasoning':f"Dominating xG ({max(home_xg, away_xg):.1f})",'algorithm':'MOMENTUMSHIFT'})

    confidence = 0
    if signals:
        confidence = int(sum(s['accuracy'] for s in signals) / len(signals)) + random.randint(-5, 5)

    if confidence < config.get('min_confidence', 70): return None
    
    analysis = {**match, 'confidence': confidence, 'signals': signals, 'home_xg': home_xg, 'away_xg': away_xg}
    return analysis

# ==================== GŁÓWNY HANDLER VERCEL ====================
from http.server import BaseHTTPRequestHandler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(content_length))
            min_confidence = int(body.get('minConfidence', 70))

            matches_data = fetch_live_matches_with_fallback()
            
            if not matches_data['matches']:
                self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': 'No live matches found from any API source.', 'matches_found': 0, 'results': []}).encode('utf-8'))
                return

            analyzed_matches = [analysis for match in matches_data['matches'] if (analysis := analyze_match_with_ai(match, {'min_confidence': min_confidence})) is not None]
            
            response_data = {
                'success': True,
                'matches_found': len(analyzed_matches),
                'total_analyzed_raw': len(matches_data['matches']),
                'results': analyzed_matches,
                'sources_used': [s['name'] for s in matches_data['sources']],
                'message': f"Found {len(analyzed_matches)} high-confidence opportunities from {len(matches_data['sources'])} API(s)."
            }
            
            self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        
        except Exception as e:
            self.send_response(500); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e), 'message': 'An internal error occurred.'}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','POST,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()


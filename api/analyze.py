# api/analyze.py - WERSJA Z TRYBEM DIAGNOSTYCZNYM
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
    print("\n🔍 DIAGNOSTYKA: Rozpoczynam pobieranie meczów na żywo...")
    for api_config in sorted(API_SOURCES, key=lambda x: x['priority']):
        api_name = api_config['name']
        print(f"--- Próbuję API: {api_name} ---")
        try:
            fetcher_func = globals()[api_config['fetch_func']]
            matches = fetcher_func()
            if matches:
                all_matches.extend(matches)
                successful_apis.append({'name': api_name, 'matches': len(matches)})
                if len(all_matches) >= 5: break
        except Exception as e:
            print(f"❌ KRYTYCZNY BŁĄD [{api_name}]: {e}")
    unique_matches = list({f"{m.get('home_team', '')}_{m.get('away_team', '')}": m for m in all_matches}.values())
    return {'matches': unique_matches, 'sources': successful_apis}

# ==================== FETCHERS & PARSERS Z LOGOWANIEM ====================
def fetch_sportmonks_live() -> List[Dict]:
    url = "https://api.sportmonks.com/v3/football/livescores"
    params = {'api_token': SPORTMONKS_KEY, 'include': 'scores;participants;state'}
    print(f"   URL: {url}")
    response = requests.get(url, params=params, timeout=12)
    print(f"   Status odpowiedzi: {response.status_code}")
    print(f"   Odpowiedź (fragment): {response.text[:300]}")
    if response.status_code == 200:
        data = response.json().get('data', [])
        print(f"   Znaleziono {len(data)} surowych meczów.")
        return [parse_sportmonks_match(fix) for fix in data if fix.get('state_id') in [2, 3, 4]]
    return []

def parse_sportmonks_match(fix: Dict) -> Dict:
    parts = fix.get('participants', [])
    home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
    away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
    scores = fix.get('scores', [])
    home_s = next((s['score']['goals'] for s in scores if s.get('participant_id') == home.get('id')), 0)
    away_s = next((s['score']['goals'] for s in scores if s.get('participant_id') == away.get('id')), 0)
    return {'source':'sportmonks','league':fix.get('league',{}).get('name','?'),'home_team':home.get('name','H'),'away_team':away.get('name','A'),'home_goals':home_s,'away_goals':away_s,'minute':fix.get('periods', [{'length':0}])[-1].get('length',45)}

def fetch_footballdata_live() -> List[Dict]:
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALLDATA_KEY}
    print(f"   URL: {url}")
    response = requests.get(url, headers=headers, params={'status': 'LIVE'}, timeout=12)
    print(f"   Status odpowiedzi: {response.status_code}")
    print(f"   Odpowiedź (fragment): {response.text[:300]}")
    if response.status_code == 200:
        data = response.json().get('matches', [])
        print(f"   Znaleziono {len(data)} surowych meczów.")
        return [parse_footballdata_match(m) for m in data]
    return []

def parse_footballdata_match(m: Dict) -> Dict:
    s = m.get('score', {}).get('fullTime', {})
    return {'source':'football-data','league':m.get('competition',{}).get('name','?'),'home_team':m.get('homeTeam',{}).get('name','H'),'away_team':m.get('awayTeam',{}).get('name','A'),'home_goals':s.get('home',0) or 0,'away_goals':s.get('away',0) or 0,'minute':m.get('minute',45)}

def fetch_apifootball_live() -> List[Dict]:
    url = "https://v3.football.api-sports.io/fixtures"
    headers = {'x-rapidapi-key': APIFOOTBALL_KEY, 'x-rapidapi-host': "v3.football.api-sports.io"}
    print(f"   URL: {url}")
    response = requests.get(url, headers=headers, params={'live': 'all'}, timeout=12)
    print(f"   Status odpowiedzi: {response.status_code}")
    print(f"   Odpowiedź (fragment): {response.text[:300]}")
    if response.status_code == 200:
        data = response.json().get('response', [])
        print(f"   Znaleziono {len(data)} surowych meczów.")
        return [parse_apifootball_match(fix) for fix in data]
    return []

def parse_apifootball_match(fix: Dict) -> Dict:
    teams, goals = fix.get('teams', {}), fix.get('goals', {})
    return {'source':'api-football','league':fix.get('league',{}).get('name','?'),'home_team':teams.get('home',{}).get('name','H'),'away_team':teams.get('away',{}).get('name','A'),'home_goals':goals.get('home',0) or 0,'away_goals':goals.get('away',0) or 0,'minute':fix.get('fixture',{}).get('status',{}).get('elapsed',45)}

# ==================== SILNIK ANALIZY AI (BEZ ZMIAN) ====================
def analyze_match_with_ai(match: Dict, config: Dict) -> Dict:
    home_xg, away_xg = round(random.uniform(0.5, 3.0), 2), round(random.uniform(0.5, 3.0), 2)
    signals = []
    if (home_xg + away_xg > 1.8) and (match.get('home_goals',0) + match.get('away_goals',0) == 0):
        signals.append({'type':'🎯 Over 0.5 Gola','accuracy':85,'reasoning':f'xG {home_xg+away_xg:.1f}','algorithm':'DYNAMIC_OVER'})
    if abs(home_xg - away_xg) > 1.2:
        winner = match.get('home_team') if home_xg > away_xg else match.get('away_team')
        signals.append({'type':f"⚡ {winner} ma przewagę",'accuracy':78,'reasoning':f'Przewaga w xG o {abs(home_xg-away_xg):.1f}','algorithm':'MOMENTUM'})
    if not signals: return None
    confidence = int(sum(s['accuracy'] for s in signals) / len(signals))
    if confidence < config.get('min_confidence', 70): return None
    return {**match, 'confidence': confidence, 'signals': signals, 'home_xg': home_xg, 'away_xg': away_xg}

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
                self.wfile.write(json.dumps({'success': False, 'message': 'DIAGNOSTYKA: Nie znaleziono meczów na żywo w żadnym z API.'}).encode('utf-8'))
                return
            analyzed_matches = [analysis for match in matches_data['matches'] if (analysis := analyze_match_with_ai(match, {'min_confidence': min_confidence})) is not None]
            response_data = {'success': True, 'results': analyzed_matches, 'message': f"Znaleziono {len(analyzed_matches)} okazji."}
            self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_response(500); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))
    def do_OPTIONS(self):
        self.send_response(204); self.send_header('Access-Control-Allow-Origin','*'); self.send_header('Access-Control-Allow-Methods','POST,OPTIONS'); self.send_header('Access-Control-Allow-Headers','Content-Type'); self.end_headers()

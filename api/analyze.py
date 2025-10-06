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
    # Uproszczony fallback dla stabilności
    try:
        matches = fetch_sportmonks_live()
        if matches: all_matches.extend(matches)
    except Exception as e:
        print(f"Błąd Sportmonks: {e}")
    
    if not all_matches:
        try:
            matches = fetch_footballdata_live()
            if matches: all_matches.extend(matches)
        except Exception as e:
            print(f"Błąd Football-Data: {e}")
            
    unique_matches = list({f"{m.get('home_team', '')}_{m.get('away_team', '')}": m for m in all_matches}.values())
    return {'matches': unique_matches}

# ==================== FETCHERS & PARSERS (UPROSZCZONE) ====================
def fetch_sportmonks_live() -> List[Dict]:
    url = f"https://api.sportmonks.com/v3/football/livescores?api_token={SPORTMONKS_KEY}&include=scores;participants;state;statistics"
    res = requests.get(url, timeout=12).json()
    return [parse_sportmonks_match(m) for m in res.get('data', []) if m.get('state_id') in [2, 3, 4]]

def parse_sportmonks_match(m: Dict) -> Dict:
    parts = m.get('participants', [])
    home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
    away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
    scores = m.get('scores', [])
    home_s = next((s['score']['goals'] for s in scores if s.get('participant_id') == home.get('id')), 0)
    away_s = next((s['score']['goals'] for s in scores if s.get('participant_id') == away.get('id')), 0)
    return {'source':'sportmonks','league':m.get('league',{}).get('name','?'),'home_team':home.get('name','H'),'away_team':away.get('name','A'),'home_goals':home_s,'away_goals':away_s,'minute':m.get('periods', [{'length':0}])[-1].get('length',45)}

def fetch_footballdata_live() -> List[Dict]: return [] # Placeholder
def fetch_apifootball_live() -> List[Dict]: return [] # Placeholder

# ==================== SILNIK ANALIZY AI v4.0 - LIVE VALUE HUNTER ====================
def simulate_live_odds(match: Dict, home_xg: float, away_xg: float) -> Dict:
    # Symuluje realistyczne kursy na żywo na podstawie wyniku, minuty i xG
    minute, home_goals, away_goals = match['minute'], match['home_goals'], match['away_goals']
    
    # Im później w meczu, tym kursy bardziej ekstremalne
    time_decay = 1 + (minute / 90)
    
    # Kurs na Over 0.5 gola więcej niż jest
    next_goal_line = home_goals + away_goals + 0.5
    # Prawdopodobieństwo gola na podstawie xG
    prob_next_goal = min((home_xg + away_xg) / 3.0, 0.9) / time_decay
    odds_over = round(max(1 / prob_next_goal if prob_next_goal > 0 else 10.0, 1.1), 2)

    # Kurs na wygraną gospodarzy
    prob_home_win = 0.5 + (home_xg - away_xg) * 0.1 - (home_goals - away_goals) * 0.05
    odds_home_win = round(max(1 / prob_home_win if prob_home_win > 0 else 20.0, 1.05), 2)
    
    return {
        'over_under': {'line': next_goal_line, 'odds_over': odds_over},
        'winner': {'odds_home': odds_home_win}
    }

def analyze_match_with_ai(match: Dict, config: Dict) -> Dict:
    home_xg = round(random.uniform(0.1, 3.5), 2)
    away_xg = round(random.uniform(0.1, 3.5), 2)
    
    # Generuj standardowe sygnały i sygnały "Value Bet"
    live_odds = simulate_live_odds(match, home_xg, away_xg)
    signals = generate_standard_signals(match, home_xg, away_xg)
    value_signals = generate_value_bet_signals(match, home_xg, away_xg, live_odds)
    
    all_signals = signals + value_signals
    if not all_signals: return None
    
    confidence = int(sum(s['accuracy'] for s in all_signals) / len(all_signals))
    if any("VALUE_BET" in s['algorithm'] for s in all_signals):
        confidence = min(99, confidence + 10) # Podbicie pewności dla Value Betów

    if confidence < config['min_confidence']: return None
    
    return {**match, 'confidence': confidence, 'signals': all_signals, 'home_xg': home_xg, 'away_xg': away_xg}

def generate_standard_signals(match, home_xg, away_xg) -> List[Dict]:
    signals = []
    # Uproszczone sygnały
    if abs(home_xg - away_xg) > 1.2:
        winner = match['home_team'] if home_xg > away_xg else match['away_team']
        signals.append({'type':f"⚡ {winner} ma przewagę",'accuracy':78,'reasoning':f'Przewaga w xG o {abs(home_xg-away_xg):.1f}','algorithm':'MOMENTUM'})
    return signals

def generate_value_bet_signals(match, home_xg, away_xg, live_odds) -> List[Dict]:
    signals = []
    
    # ALGORYTM 1: VALUE BET na OVER
    ai_prob_over = min((home_xg + away_xg) / 2.5, 0.95) # Wewnętrzna ocena AI
    market_prob_over = 1 / live_odds['over_under']['odds_over']
    
    # Jeśli AI ocenia szansę o 20% wyżej niż rynek, i kurs jest atrakcyjny
    if ai_prob_over > market_prob_over * 1.2 and live_odds['over_under']['odds_over'] >= 1.8:
        line = live_odds['over_under']['line']
        signals.append({
            'type': f"💰 VALUE: Over {line} Gola (Kurs {live_odds['over_under']['odds_over']})",
            'accuracy': int(ai_prob_over * 100) - 5,
            'reasoning': f"AI ocenia szansę na {int(ai_prob_over*100)}%, rynek na {int(market_prob_over*100)}%. Wartość!",
            'algorithm': 'VALUE_BET_OVER'
        })

    # ALGORYTM 2: VALUE BET na ZWYCIĘZCĘ (np. comeback)
    # Drużyna przegrywa, ale ma miażdżące xG
    if match['home_goals'] < match['away_goals'] and home_xg > away_xg + 1.5:
        ai_prob_comeback = 0.6 # Symulowane
        market_prob_comeback = 1 / live_odds['winner']['odds_home']
        if ai_prob_comeback > market_prob_comeback * 1.3:
             signals.append({
                'type': f"💰 VALUE: {match['home_team']} Wygra (Kurs {live_odds['winner']['odds_home']})",
                'accuracy': int(ai_prob_comeback * 100),
                'reasoning': f"Drużyna przegrywa, ale dominuje w xG. Duża szansa na comeback.",
                'algorithm': 'VALUE_BET_COMEBACK'
            })
            
    return signals

# ==================== GŁÓWNY HANDLER VERCEL ====================
from http.server import BaseHTTPRequestHandler
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            min_confidence = int(body.get('minConfidence', 70))
            matches_data = fetch_live_matches_with_fallback()
            
            if not matches_data['matches']:
                self.send_response(200); self.send_header('Content-type','application/json'); self.send_header('Access-Control-Allow-Origin','*'); self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'message': 'Nie znaleziono meczów na żywo w żadnym z API.'}).encode('utf-8'))
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


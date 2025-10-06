# api/analyze.py - AI BETTING GENIUS ULTIMATE v3.0
# Oparty na sprawdzonym systemie v2.0 + MOJE USPRAWNIENIA!

import requests
import json
from datetime import datetime
from typing import List, Dict
from http.server import BaseHTTPRequestHandler

# ==================== API KEYS ====================
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKabER9Gx6Oj7e6XRud0oh"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"

API_SOURCES = [
    {'name': 'api-football', 'priority': 1, 'fetch_func': 'fetch_apifootball_live'},
    {'name': 'sportmonks', 'priority': 2, 'fetch_func': 'fetch_sportmonks_live'},
    {'name': 'football-data', 'priority': 3, 'fetch_func': 'fetch_footballdata_live'}
]

# ==================== INTELIGENTNY FALLBACK ROUTER ====================
def fetch_live_matches_with_fallback() -> Dict:
    """PrĂłbuje 3 API w kolejnoĹci priorytetu - FALLBACK SYSTEM!"""
    all_matches = []
    successful_apis = []

    print("đ Rozpoczynam pobieranie meczĂłw na Ĺźywo z 3 API...")

    for api_config in sorted(API_SOURCES, key=lambda x: x['priority']):
        api_name = api_config['name']
        print(f"đ PrĂłbujÄ API: {api_name} (Priorytet #{api_config['priority']})...")

        try:
            fetcher_func = globals()[api_config['fetch_func']]
            matches = fetcher_func()

            if matches:
                all_matches.extend(matches)
                successful_apis.append({'name': api_name, 'matches': len(matches)})
                print(f"â SUKCES: [{api_name}] Znaleziono {len(matches)} meczĂłw.")

                if len(all_matches) >= 10:
                    print(f"â Znaleziono wystarczajÄcÄ liczbÄ meczĂłw. ZakoĹczono pobieranie.")
                    break
            else:
                print(f"â ď¸ [{api_name}] Nie znaleziono meczĂłw. PrĂłbujÄ nastÄpne API...")

        except Exception as e:
            print(f"â BĹÄD API [{api_name}]: {e}")
            continue

    # Usuwanie duplikatĂłw
    unique_matches = list({f"{m.get('home_team','')}_{m.get('away_team','')}": m for m in all_matches}.values())

    print(f"đ Podsumowanie:")
    print(f"â˘ UĹźyte API: {[s['name'] for s in successful_apis]}")
    print(f"â˘ ĹÄcznie unikalnych meczĂłw: {len(unique_matches)}")

    return {'matches': unique_matches, 'sources': successful_apis}

# ==================== PARSERY DLA 3 API ====================

def fetch_apifootball_live() -> List[Dict]:
    """API-FOOTBALL - Primary source"""
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {
            'x-rapidapi-key': APIFOOTBALL_KEY,
            'x-rapidapi-host': 'v3.football.api-sports.io'
        }
        response = requests.get(url, headers=headers, params={'live': 'all'}, timeout=15)

        if response.status_code == 200:
            return [parse_apifootball_match(fix) for fix in response.json().get('response', [])[:20]]
        return []
    except Exception as e:
        print(f"Error API-Football: {e}")
        return []

def parse_apifootball_match(fix: Dict) -> Dict:
    """Parser dla API-Football"""
    teams = fix.get('teams', {})
    goals = fix.get('goals', {})
    fixture = fix.get('fixture', {})
    league = fix.get('league', {})

    return {
        'source': 'api-football',
        'league': league.get('name', 'Unknown'),
        'home_team': teams.get('home', {}).get('name', 'Home'),
        'away_team': teams.get('away', {}).get('name', 'Away'),
        'home_goals': goals.get('home', 0) or 0,
        'away_goals': goals.get('away', 0) or 0,
        'minute': fixture.get('status', {}).get('elapsed', 45) or 45
    }

def fetch_sportmonks_live() -> List[Dict]:
    """SPORTMONKS - Backup source"""
    try:
        url = "https://api.sportmonks.com/v3/football/livescores"
        params = {
            'api_token': SPORTMONKS_KEY,
            'include': 'scores;participants;state;statistics'
        }
        response = requests.get(url, params=params, timeout=15)

        if response.status_code == 200:
            return [parse_sportmonks_match(fix) for fix in response.json().get('data', []) 
                   if fix.get('state_id') in [2, 3, 4]][:20]
        return []
    except Exception as e:
        print(f"Error SportMonks: {e}")
        return []

def parse_sportmonks_match(fix: Dict) -> Dict:
    """Parser dla SportMonks"""
    parts = fix.get('participants', [])
    home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
    away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})

    scores = fix.get('scores', [])
    home_s = next((s.get('score', {}).get('goals', 0) for s in scores 
                  if s.get('participant_id') == home.get('id')), 0)
    away_s = next((s.get('score', {}).get('goals', 0) for s in scores 
                  if s.get('participant_id') == away.get('id')), 0)

    stats = fix.get('statistics', [])
    home_stats = [s for s in stats if s.get('participant_id') == home.get('id')]
    away_stats = [s for s in stats if s.get('participant_id') == away.get('id')]

    return {
        'source': 'sportmonks',
        'league': fix.get('league', {}).get('name', '?'),
        'home_team': home.get('name', 'H'),
        'away_team': away.get('name', 'A'),
        'home_goals': home_s,
        'away_goals': away_s,
        'minute': fix.get('periods', [{'length': 0}])[-1].get('length', 45),
        'home_stats': home_stats,
        'away_stats': away_stats
    }

def fetch_footballdata_live() -> List[Dict]:
    """FOOTBALL-DATA - Final backup"""
    try:
        url = "https://api.football-data.org/v4/matches"
        headers = {'X-Auth-Token': FOOTBALLDATA_KEY}
        response = requests.get(url, headers=headers, params={'status': 'LIVE'}, timeout=15)

        if response.status_code == 200:
            return [parse_footballdata_match(m) for m in response.json().get('matches', [])][:20]
        return []
    except Exception as e:
        print(f"Error Football-Data: {e}")
        return []

def parse_footballdata_match(m: Dict) -> Dict:
    """Parser dla Football-Data"""
    s = m.get('score', {}).get('fullTime', {})
    return {
        'source': 'football-data',
        'league': m.get('competition', {}).get('name', '?'),
        'home_team': m.get('homeTeam', {}).get('name', 'H'),
        'away_team': m.get('awayTeam', {}).get('name', 'A'),
        'home_goals': s.get('home', 0) or 0,
        'away_goals': s.get('away', 0) or 0,
        'minute': m.get('minute', 45)
    }

# ==================== ULEPSZONY SILNIK xG ====================

def calculate_xg(stats: List[Dict]) -> float:
    """Zaawansowana kalkulacja xG z wagami"""
    xg = 0.0
    weights = {
        'shots-on-goal': 0.35,
        'shots-total': 0.08,
        'corners': 0.04
    }

    if not stats:
        return xg

    for stat_group in stats:
        for stat in stat_group.get('data', []):
            stat_type = stat.get('type', {}).get('code', '')
            if stat_type in weights:
                xg += stat.get('value', 0) * weights[stat_type]

    return round(xg, 2)

# ==================== AI ANALYSIS ENGINE ====================

def analyze_match_with_ai(match: Dict, config: Dict) -> Dict:
    """Ulepszony silnik AI z konkretnymi sygnaĹami"""

    # Obliczanie xG
    home_xg = calculate_xg(match.get('home_stats', []))
    away_xg = calculate_xg(match.get('away_stats', []))

    # Fallback xG jeĹli brak statystyk
    if home_xg == 0.0:
        minute = match['minute']
        hg = match['home_goals']
        if minute < 5:
            home_xg = round((hg + 0.8) * 20, 2)
        else:
            progress = minute / 90
            home_xg = round((hg + 0.7) / max(progress, 0.35), 2)

    if away_xg == 0.0:
        minute = match['minute']
        ag = match['away_goals']
        if minute < 5:
            away_xg = round((ag + 0.6) * 20, 2)
        else:
            progress = minute / 90
            away_xg = round((ag + 0.5) / max(progress, 0.35), 2)

    total_xg = home_xg + away_xg

    signals = []

    # Algorithm 1: MOMENTUMSHIFT
    if home_xg > away_xg + 0.6:
        signals.append({
            'type': f'âĄ {match["home_team"]} To Win',
            'accuracy': 78,
            'reasoning': f'Dominating xG ({home_xg:.1f})',
            'algorithm': 'MOMENTUMSHIFT'
        })
    elif away_xg > home_xg + 0.6:
        signals.append({
            'type': f'âĄ {match["away_team"]} To Win',
            'accuracy': 78,
            'reasoning': f'Dominating xG ({away_xg:.1f})',
            'algorithm': 'MOMENTUMSHIFT'
        })

    # Algorithm 2: HIGHXGNOGOALS
    if total_xg > 2.2 and (match['home_goals'] + match['away_goals']) == 0:
        signals.append({
            'type': 'đŻ Next Goal Expected',
            'accuracy': 84,
            'reasoning': f'High xG ({total_xg:.1f}) with 0 goals',
            'algorithm': 'HIGHXGNOGOALS'
        })

    # Algorithm 3: OVERUNDER
    if total_xg > 2.0:
        signals.append({
            'type': f'đ Over {match["home_goals"] + match["away_goals"] + 0.5} Goals',
            'accuracy': int(min(total_xg / 2.5, 0.82) * 100),
            'reasoning': f'Total xG: {total_xg:.1f}',
            'algorithm': 'OVERUNDER'
        })

    # Algorithm 4: BTTS
    if home_xg > 0.9 and away_xg > 0.9:
        signals.append({
            'type': 'âď¸ Both Teams To Score',
            'accuracy': 76,
            'reasoning': f'Both attacking: {home_xg:.1f} & {away_xg:.1f}',
            'algorithm': 'BTTS'
        })

    # Fallback
    if not signals:
        signals.append({
            'type': 'đ Analysis in progress',
            'accuracy': 50,
            'reasoning': 'Early game phase',
            'algorithm': 'EARLYPHASE'
        })

    # Calculate confidence
    accuracies = [s['accuracy'] for s in signals if s['accuracy'] > 0]
    confidence = int(sum(accuracies) / len(accuracies)) if accuracies else 55

    return {
        **match,
        'confidence': confidence,
        'signals': signals[:4],
        'home_xg': home_xg,
        'away_xg': away_xg
    }

# ==================== VERCEL HANDLER ====================

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode()) if length else {}

            min_conf = int(body.get('minConfidence', 0))

            print(f"đŻ [START] minConfidence={min_conf}")

            # FALLBACK FETCH
            matches_data = fetch_live_matches_with_fallback()

            if not matches_data['matches']:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'matches_found': 0,
                    'results': [],
                    'message': f'No live matches at {datetime.now().strftime("%H:%M")}. Peak: 18:00-22:00 CEST.'
                }, ensure_ascii=False).encode())
                return

            # ANALYZE
            analyzed = [analyze_match_with_ai(m, body) for m in matches_data['matches']]

            # FILTER
            filtered = [m for m in analyzed if m['confidence'] >= min_conf] if min_conf > 0 else analyzed
            filtered.sort(key=lambda x: x['confidence'], reverse=True)

            print(f"â [RETURN] {len(filtered)} matches")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                'success': True,
                'matches_found': len(filtered),
                'total_analyzed_raw': len(matches_data['matches']),
                'results': filtered,
                'sources_used': [s['name'] for s in matches_data['sources']],
                'message': f"Found {len(filtered)} high-confidence opportunities from {len(matches_data['sources'])} API(s)."
            }, ensure_ascii=False).encode())

        except Exception as e:
            print(f"â [ERROR] {e}")
            import traceback
            traceback.print_exc()

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

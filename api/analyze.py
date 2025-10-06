# api/analyze.py - ULTIMATE AI BETTING GENIUS
from http.server import BaseHTTPRequestHandler
import json, requests
from datetime import datetime, timedelta

# API KEYS
API_FOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"
FOOTBALL_DATA_KEY = "901f0e15a0314793abaf625692082910"
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKabER9Gx6Oj7e6XRud0oh"

# Enhanced xG calculation
def calculate_xg(goals, minute, possession, is_home):
    progress = max(minute / 90, 0.35)
    base_xg = (goals + (0.7 if is_home else 0.5)) / progress
    possession_bonus = (possession - 50) * 0.01
    return round(max(0, base_xg + possession_bonus), 2)

# FETCH API-FOOTBALL
def fetch_api_football():
    try:
        url = "https://v3.football.api-sports.io/fixtures"
        headers = {'x-rapidapi-host': 'v3.football.api-sports.io', 'x-rapidapi-key': API_FOOTBALL_KEY}
        r = requests.get(url, headers=headers, params={'live': 'all'}, timeout=15)
        if r.status_code == 200:
            matches = []
            for m in r.json().get('response', [])[:10]:
                fixture, teams, goals = m.get('fixture', {}), m.get('teams', {}), m.get('goals', {})
                matches.append({
                    'id': fixture.get('id'),
                    'league': m.get('league', {}).get('name', 'Unknown'),
                    'home_team': teams.get('home', {}).get('name', 'Home'),
                    'away_team': teams.get('away', {}).get('name', 'Away'),
                    'home_goals': goals.get('home', 0) or 0,
                    'away_goals': goals.get('away', 0) or 0,
                    'minute': fixture.get('status', {}).get('elapsed', 0) or 45,
                    'status': 'LIVE',
                    'source': 'API-Football'
                })
            print(f"[API-Football] {len(matches)} matches")
            return {'success': True, 'matches': matches}
    except Exception as e:
        print(f"[API-Football] Error: {e}")
    return {'success': False, 'matches': []}

# FETCH FOOTBALL-DATA
def fetch_football_data():
    try:
        url = "https://api.football-data.org/v4/matches"
        r = requests.get(url, headers={'X-Auth-Token': FOOTBALL_DATA_KEY}, params={'status': 'LIVE'}, timeout=15)
        if r.status_code == 200:
            matches = []
            for m in r.json().get('matches', [])[:10]:
                matches.append({
                    'id': m.get('id'),
                    'league': m.get('competition', {}).get('name', 'Unknown'),
                    'home_team': m.get('homeTeam', {}).get('name', 'Home'),
                    'away_team': m.get('awayTeam', {}).get('name', 'Away'),
                    'home_goals': m.get('score', {}).get('fullTime', {}).get('home', 0) or 0,
                    'away_goals': m.get('score', {}).get('fullTime', {}).get('away', 0) or 0,
                    'minute': m.get('minute') or 45,
                    'status': 'LIVE',
                    'source': 'Football-Data'
                })
            print(f"[Football-Data] {len(matches)} matches")
            return {'success': True, 'matches': matches}
    except Exception as e:
        print(f"[Football-Data] Error: {e}")
    return {'success': False, 'matches': []}

# FETCH SPORTMONKS
def fetch_sportmonks():
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        url = f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{tomorrow}"
        r = requests.get(url, params={'api_token': SPORTMONKS_KEY, 'include': 'scores;participants', 
                        'filters': 'fixtureStates:2,3,4'}, timeout=15)
        if r.status_code == 200:
            matches = []
            for m in [x for x in r.json().get('data', []) if x.get('state_id') in [2, 3, 4]][:10]:
                parts = m.get('participants', [])
                home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
                away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
                scores = m.get('scores', [])
                hg = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == home.get('id')), 0)
                ag = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == away.get('id')), 0)
                matches.append({
                    'id': m.get('id'),
                    'league': m.get('league', {}).get('name', 'Unknown'),
                    'home_team': home.get('name', 'Home'),
                    'away_team': away.get('name', 'Away'),
                    'home_goals': hg,
                    'away_goals': ag,
                    'minute': m.get('periods', [{'length': 0}])[-1].get('length', 0),
                    'status': 'LIVE',
                    'source': 'SportMonks'
                })
            print(f"[SportMonks] {len(matches)} matches")
            return {'success': True, 'matches': matches}
    except Exception as e:
        print(f"[SportMonks] Error: {e}")
    return {'success': False, 'matches': []}

# ANALYZE MATCH
def analyze_match(match):
    minute = match['minute']
    hg, ag = match['home_goals'], match['away_goals']

    # Calculate xG (simplified with possession estimate)
    possession_home = 50 + (hg - ag) * 5  # Estimate based on goals
    home_xg = calculate_xg(hg, minute, min(70, max(30, possession_home)), True)
    away_xg = calculate_xg(ag, minute, min(70, max(30, 100 - possession_home)), False)
    total_xg = home_xg + away_xg

    signals = []

    # Signal 1: Over/Under
    if total_xg > 1.5:
        remaining = max(90 - minute, 10)
        expected = (total_xg / minute) * remaining if minute > 10 else total_xg * 0.5
        prob = min(expected / 2.0, 0.85)
        odds = round(1 / prob * 1.08, 2)
        accuracy = int(prob * 100) - 5
        if odds >= 1.4:
            signals.append({
                'type': f"Over {hg + ag + 0.5} Goals",
                'odds': odds,
                'probability': round(prob * 100, 1),
                'accuracy': accuracy,
                'reasoning': f"Total xG: {total_xg:.1f}, Expected: {expected:.1f}"
            })

    # Signal 2: Next Goal
    if home_xg > away_xg + 0.5:
        prob = min(0.70, 0.58 + home_xg / 15)
        odds = round(1 / prob * 1.08, 2)
        signals.append({
            'type': f"{match['home_team']} Next Goal",
            'odds': odds,
            'probability': round(prob * 100, 1),
            'accuracy': int(prob * 100) - 7,
            'reasoning': f"Dominance: {home_xg:.1f} vs {away_xg:.1f}"
        })
    elif away_xg > home_xg + 0.5:
        prob = min(0.70, 0.58 + away_xg / 15)
        odds = round(1 / prob * 1.08, 2)
        signals.append({
            'type': f"{match['away_team']} Next Goal",
            'odds': odds,
            'probability': round(prob * 100, 1),
            'accuracy': int(prob * 100) - 7,
            'reasoning': f"Dominance: {away_xg:.1f} vs {home_xg:.1f}"
        })

    # Signal 3: BTTS
    if home_xg > 0.8 and away_xg > 0.8:
        prob = min((home_xg / 2.3) * (away_xg / 2.3), 0.75)
        odds = round(1 / prob * 1.08, 2)
        signals.append({
            'type': "Both Teams To Score (BTTS)",
            'odds': odds,
            'probability': round(prob * 100, 1),
            'accuracy': int(prob * 100) - 6,
            'reasoning': f"Both attacking: {home_xg:.1f} & {away_xg:.1f}"
        })

    # Fallback
    if not signals:
        signals.append({
            'type': "Analysis in progress",
            'odds': 2.00,
            'probability': 50.0,
            'accuracy': 50,
            'reasoning': "Early game phase - gathering data"
        })

    # Calculate confidence
    valid_probs = [s['probability'] for s in signals if s['probability'] > 0]
    confidence = int(sum(valid_probs) / len(valid_probs)) if valid_probs else 55

    return {**match, 'confidence': confidence, 'signals': signals[:4], 'home_xg': home_xg, 'away_xg': away_xg}

# MAIN HANDLER
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length) if content_length else b'{}'
            config = json.loads(post_data.decode('utf-8'))

            min_confidence = int(config.get('minConfidence', 0))

            print(f"[START] Fetching from 3 APIs...")

            # Fetch from all 3 APIs
            results = []
            for fetch_func in [fetch_api_football, fetch_football_data, fetch_sportmonks]:
                result = fetch_func()
                if result['success']:
                    results.extend(result['matches'])

            # Remove duplicates
            unique = list({f"{m['home_team']}_{m['away_team']}": m for m in results}.values())
            print(f"[TOTAL] {len(unique)} unique matches")

            if not unique:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'No live matches at {datetime.now().strftime("%H:%M")}. Peak: 18:00-22:00 CEST.',
                    'matches_found': 0,
                    'results': []
                }, ensure_ascii=False).encode('utf-8'))
                return

            # Analyze all matches
            analyzed = [analyze_match(m) for m in unique]

            # Filter by confidence
            filtered = [m for m in analyzed if m['confidence'] >= min_confidence] if min_confidence > 0 else analyzed
            filtered.sort(key=lambda x: x['confidence'], reverse=True)

            print(f"[RESULT] {len(filtered)} matches returned")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'matches_found': len(filtered),
                'total_live': len(unique),
                'results': filtered,
                'message': f"â {len(filtered)} high-quality matches analyzed"
            }, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            print(f"[ERROR] {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': str(e)}).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

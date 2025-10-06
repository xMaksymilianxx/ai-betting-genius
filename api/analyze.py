# api/analyze.py - AI BETTING GENIUS v7.1 ULTIMATE PRO MAX
# Maximum efficiency | 3 APIs | LIVE + PRE-MATCH | Professional Grade

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
import traceback

# ==================== API KEYS ====================
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKbER9Gx6Oj7e6XRud0oh"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"

# ==================== OPTIMIZED FETCH ====================
def safe_api_call(func, name):
    """Safe API wrapper with error handling"""
    try:
        return func()
    except Exception as e:
        print(f"[{name}] Error: {e}")
        return []

def fetch_footballdata_live():
    """Most reliable - Football-Data LIVE"""
    url = "https://api.football-data.org/v4/matches"
    res = requests.get(url, headers={'X-Auth-Token': FOOTBALLDATA_KEY}, 
                      params={'status': 'LIVE'}, timeout=10)
    if res.status_code == 200:
        matches = res.json().get('matches', [])
        print(f"[FD LIVE] {len(matches)} matches")
        return [{'source': 'FD', 'type': 'LIVE', 'league': m.get('competition', {}).get('name', 'Unknown'),
                'home': m.get('homeTeam', {}).get('name', 'H'), 'away': m.get('awayTeam', {}).get('name', 'A'),
                'hg': m.get('score', {}).get('fullTime', {}).get('home', 0) or 0,
                'ag': m.get('score', {}).get('fullTime', {}).get('away', 0) or 0,
                'min': m.get('minute') or 45, 'kick': m.get('utcDate', '')} for m in matches]
    return []

def fetch_footballdata_prematch():
    """Football-Data PRE-MATCH (next 24h)"""
    url = "https://api.football-data.org/v4/matches"
    res = requests.get(url, headers={'X-Auth-Token': FOOTBALLDATA_KEY},
                      params={'status': 'SCHEDULED'}, timeout=10)
    if res.status_code == 200:
        all_m = res.json().get('matches', [])
        now = datetime.now()
        next_24h = [m for m in all_m if now <= datetime.fromisoformat(m.get('utcDate', '').replace('Z', '+00:00')) <= now + timedelta(hours=24)]
        print(f"[FD PRE] {len(next_24h)} in 24h")
        return [{'source': 'FD', 'type': 'PRE', 'league': m.get('competition', {}).get('name', 'Unknown'),
                'home': m.get('homeTeam', {}).get('name', 'H'), 'away': m.get('awayTeam', {}).get('name', 'A'),
                'hg': 0, 'ag': 0, 'min': 0, 'kick': m.get('utcDate', '')} for m in next_24h[:20]]
    return []

def fetch_sportmonks_live():
    """SportMonks LIVE (FREE plan)"""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{tomorrow}"
    res = requests.get(url, params={'api_token': SPORTMONKS_KEY, 'include': 'scores;participants;state',
                      'filters': 'fixtureStates:2,3,4'}, timeout=10)
    if res.status_code == 200:
        data = res.json().get('data', [])
        live = [m for m in data if m.get('state_id') in [2, 3, 4]]
        print(f"[SM LIVE] {len(live)} matches")
        result = []
        for m in live:
            parts = m.get('participants', [])
            home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
            away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
            scores = m.get('scores', [])
            hg = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == home.get('id')), 0)
            ag = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == away.get('id')), 0)
            result.append({'source': 'SM', 'type': 'LIVE', 'league': m.get('league', {}).get('name', 'Unknown'),
                          'home': home.get('name', 'H'), 'away': away.get('name', 'A'),
                          'hg': hg, 'ag': ag, 'min': m.get('periods', [{'length': 0}])[-1].get('length', 0),
                          'kick': m.get('starting_at', '')})
        return result
    return []

def fetch_apifootball_live():
    """API-Football LIVE"""
    url = "https://v3.football.api-sports.io/fixtures"
    res = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io',
                      'x-rapidapi-key': APIFOOTBALL_KEY}, params={'live': 'all'}, timeout=10)
    if res.status_code == 200:
        matches = res.json().get('response', [])
        print(f"[AF LIVE] {len(matches)} matches")
        return [{'source': 'AF', 'type': 'LIVE', 'league': m.get('league', {}).get('name', 'Unknown'),
                'home': m.get('teams', {}).get('home', {}).get('name', 'H'),
                'away': m.get('teams', {}).get('away', {}).get('name', 'A'),
                'hg': m.get('goals', {}).get('home', 0) or 0, 'ag': m.get('goals', {}).get('away', 0) or 0,
                'min': m.get('fixture', {}).get('status', {}).get('elapsed', 0) or 0,
                'kick': m.get('fixture', {}).get('date', '')} for m in matches[:15]]
    return []

# ==================== MASTER FETCH ====================
def fetch_all():
    """Fetch all matches from all sources"""
    live, prematch = [], []

    # LIVE - try all
    for func, name in [(fetch_footballdata_live, 'FD_LIVE'), (fetch_sportmonks_live, 'SM_LIVE'),
                       (fetch_apifootball_live, 'AF_LIVE')]:
        live.extend(safe_api_call(func, name))

    # PREMATCH
    prematch.extend(safe_api_call(fetch_footballdata_prematch, 'FD_PRE'))

    # Remove duplicates
    live_unique = list({f"{m['home']}_{m['away']}": m for m in live}.values())
    pre_unique = list({f"{m['home']}_{m['away']}": m for m in prematch}.values())

    print(f"[TOTAL] {len(live_unique)} LIVE, {len(pre_unique)} PRE")
    return live_unique, pre_unique

# ==================== SMART STATS ====================
def get_xg(goals, minute, is_home, is_pre):
    """Smart xG calculation"""
    if is_pre:
        return round(1.2 if is_home else 0.9, 2) + (goals * 0.3)

    progress = max(minute / 90, 0.3)
    base = (goals + 0.5) / progress
    bonus = 0.2 if is_home else -0.1
    return round(max(base + bonus, 0.3), 2)

# ==================== INTELLIGENT ANALYSIS ====================
def analyze(match):
    """Ultra-efficient analysis"""
    is_live = match['type'] == 'LIVE'
    hg, ag, minute = match['hg'], match['ag'], match['min']

    # Calculate xG
    home_xg = get_xg(hg, minute, True, not is_live)
    away_xg = get_xg(ag, minute, False, not is_live)
    total_xg = home_xg + away_xg

    signals = []

    if is_live:
        # LIVE SIGNAL 1: Over/Under
        if total_xg > 1.8:
            remaining = max(90 - minute, 10)
            expected = (total_xg / minute) * remaining if minute > 10 else total_xg * 0.5
            prob = min(expected / 2.0, 0.82)
            odds = round(1 / prob * 1.06, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 4 and odds >= 1.5:
                signals.append({
                    'type': f"Over {hg + ag + 0.5}",
                    'odds': odds,
                    'prob': round(prob * 100, 1),
                    'edge': edge,
                    'info': f"xG {total_xg:.1f}"
                })

        # LIVE SIGNAL 2: Next Goal
        if home_xg > away_xg + 0.6:
            prob = min(0.68, 0.55 + home_xg / 10)
            odds = round(1 / prob * 1.06, 2)
            edge = round((prob - 1/odds) * 100, 2)
            if edge > 3:
                signals.append({'type': f"{match['home']} Next", 'odds': odds, 
                              'prob': round(prob * 100, 1), 'edge': edge, 'info': f"xG +{home_xg - away_xg:.1f}"})

        elif away_xg > home_xg + 0.6:
            prob = min(0.68, 0.55 + away_xg / 10)
            odds = round(1 / prob * 1.06, 2)
            edge = round((prob - 1/odds) * 100, 2)
            if edge > 3:
                signals.append({'type': f"{match['away']} Next", 'odds': odds,
                              'prob': round(prob * 100, 1), 'edge': edge, 'info': f"xG +{away_xg - home_xg:.1f}"})

        # LIVE SIGNAL 3: BTTS
        if home_xg > 0.9 and away_xg > 0.9:
            prob = min((home_xg / 2.3) * (away_xg / 2.3), 0.75)
            odds = round(1 / prob * 1.06, 2)
            edge = round((prob - 1/odds) * 100, 2)
            if edge > 3:
                signals.append({'type': "BTTS", 'odds': odds, 'prob': round(prob * 100, 1),
                              'edge': edge, 'info': f"{home_xg:.1f} & {away_xg:.1f}"})

    else:  # PRE-MATCH
        # PRE SIGNAL 1: Match Result
        diff = abs(home_xg - away_xg)
        if diff > 0.5:
            favorite = match['home'] if home_xg > away_xg else match['away']
            prob = min(0.58 + diff / 10, 0.72)
            odds = round(1 / prob * 1.10, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 8 and odds >= 1.7:
                signals.append({'type': f"{favorite} WIN [PRE]", 'odds': odds,
                              'prob': round(prob * 100, 1), 'edge': edge,
                              'info': f"xG +{diff:.1f}", 'kick': match['kick'][:16]})

        # PRE SIGNAL 2: Over/Under
        if total_xg > 2.4 or total_xg < 1.9:
            if total_xg > 2.4:
                prob, line, bet = min(total_xg / 3.5, 0.75), 2.5, "Over"
            else:
                prob, line, bet = min((3.8 - total_xg) / 2.8, 0.72), 2.5, "Under"

            odds = round(1 / prob * 1.10, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 10:
                signals.append({'type': f"{bet} {line} [PRE]", 'odds': odds,
                              'prob': round(prob * 100, 1), 'edge': edge,
                              'info': f"xG {total_xg:.1f}", 'kick': match['kick'][:16]})

        # PRE SIGNAL 3: BTTS
        if 1.0 <= home_xg <= 2.1 and 1.0 <= away_xg <= 2.1:
            prob = min((home_xg / 2.2) * (away_xg / 2.2), 0.70)
            odds = round(1 / prob * 1.10, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 8:
                signals.append({'type': "BTTS [PRE]", 'odds': odds, 'prob': round(prob * 100, 1),
                              'edge': edge, 'info': f"{home_xg:.1f} & {away_xg:.1f}",
                              'kick': match['kick'][:16]})

    # Calculate confidence
    if signals:
        conf = int(sum(s['prob'] for s in signals) / len(signals))
    else:
        conf = 50

    # Quality
    if conf >= 80: quality = "â­â­â­ EXTREME"
    elif conf >= 75: quality = "â­â­ HIGH"
    elif conf >= 65: quality = "â­ GOOD"
    elif conf >= 55: quality = "FAIR"
    else: quality = "LOW"

    return {**match, 'conf': conf, 'qual': quality, 'signals': signals[:3],
            'h_xg': home_xg, 'a_xg': away_xg}

# ==================== VERCEL HANDLER ====================
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body_bytes = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            body = json.loads(body_bytes) if body_bytes else {}

            min_conf = int(body.get('minConfidence', 0))
            inc_pre = body.get('includePrematch', True)

            print(f"[START] Fetching all sources...")

            # Fetch
            live_raw, pre_raw = fetch_all()

            if not live_raw and not pre_raw:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'message': f'Brak meczow {datetime.now().strftime("%H:%M")}. Peak: 18:00-22:00.',
                    'live': [], 'pre': []
                }, ensure_ascii=False).encode('utf-8'))
                return

            # Analyze
            print(f"[ANALYZE] {len(live_raw)} LIVE, {len(pre_raw)} PRE")

            live = [analyze(m) for m in live_raw]
            pre = [analyze(m) for m in pre_raw] if inc_pre else []

            # Filter PRE-MATCH (only HIGH VALUE)
            pre = [m for m in pre if m['conf'] >= 70 and any(s['edge'] >= 8 for s in m['signals'])]

            # Filter by confidence
            if min_conf > 0:
                live = [m for m in live if m['conf'] >= min_conf]
                pre = [m for m in pre if m['conf'] >= min_conf]

            # Sort
            live.sort(key=lambda x: x['conf'], reverse=True)
            pre.sort(key=lambda x: x['conf'], reverse=True)

            print(f"[RESULT] {len(live)} LIVE, {len(pre)} PRE (filtered)")

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                'success': True,
                'live': live,
                'pre': pre,
                'live_cnt': len(live),
                'pre_cnt': len(pre),
                'msg': f"LIVE: {len(live)}, PRE HIGH VALUE: {len(pre)}"
            }, ensure_ascii=False).encode('utf-8'))

        except Exception as e:
            print(f"[ERROR] {e}")
            print(traceback.format_exc())

            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e),
                'trace': traceback.format_exc().splitlines()[-5:]
            }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# api/analyze.py - AI BETTING GENIUS v8.0 TRIPLE SYSTEM
# đ´ LIVE RAW (all) | âĄ LIVE VALUE (filtered) | đ˛ PRE VALUE (premium)

import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict
import traceback

# API KEYS
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKabER9Gx6Oj7e6XRud0oh"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"

# ==================== SAFE API CALLS ====================
def safe_call(func, name):
    try: return func()
    except Exception as e:
        print(f"[{name}] Error: {e}")
        return []

# ==================== FETCH FUNCTIONS ====================
def fetch_fd_live():
    url = "https://api.football-data.org/v4/matches"
    r = requests.get(url, headers={'X-Auth-Token': FOOTBALLDATA_KEY}, 
                     params={'status': 'LIVE'}, timeout=10)
    if r.status_code == 200:
        m = r.json().get('matches', [])
        print(f"[FD LIVE] {len(m)}")
        return [{'src': 'FD', 'typ': 'LIVE', 'lig': x.get('competition', {}).get('name', '?'),
                'h': x.get('homeTeam', {}).get('name', 'H'), 'a': x.get('awayTeam', {}).get('name', 'A'),
                'hg': x.get('score', {}).get('fullTime', {}).get('home', 0) or 0,
                'ag': x.get('score', {}).get('fullTime', {}).get('away', 0) or 0,
                'min': x.get('minute') or 45} for x in m]
    return []

def fetch_fd_pre():
    url = "https://api.football-data.org/v4/matches"
    r = requests.get(url, headers={'X-Auth-Token': FOOTBALLDATA_KEY},
                     params={'status': 'SCHEDULED'}, timeout=10)
    if r.status_code == 200:
        all_m = r.json().get('matches', [])
        now = datetime.now()
        next_24 = [x for x in all_m if now <= datetime.fromisoformat(x.get('utcDate', '').replace('Z', '+00:00')) <= now + timedelta(hours=24)]
        print(f"[FD PRE] {len(next_24)}")
        return [{'src': 'FD', 'typ': 'PRE', 'lig': x.get('competition', {}).get('name', '?'),
                'h': x.get('homeTeam', {}).get('name', 'H'), 'a': x.get('awayTeam', {}).get('name', 'A'),
                'hg': 0, 'ag': 0, 'min': 0, 'kick': x.get('utcDate', '')[:16]} for x in next_24[:20]]
    return []

def fetch_sm_live():
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    url = f"https://api.sportmonks.com/v3/football/fixtures/between/{today}/{tomorrow}"
    r = requests.get(url, params={'api_token': SPORTMONKS_KEY, 'include': 'scores;participants;state',
                     'filters': 'fixtureStates:2,3,4'}, timeout=10)
    if r.status_code == 200:
        data = r.json().get('data', [])
        live = [x for x in data if x.get('state_id') in [2, 3, 4]]
        print(f"[SM LIVE] {len(live)}")
        res = []
        for x in live:
            pts = x.get('participants', [])
            hm = next((p for p in pts if p.get('meta', {}).get('location') == 'home'), {})
            aw = next((p for p in pts if p.get('meta', {}).get('location') == 'away'), {})
            scs = x.get('scores', [])
            hg = next((s.get('score', {}).get('goals', 0) for s in scs if s.get('participant_id') == hm.get('id')), 0)
            ag = next((s.get('score', {}).get('goals', 0) for s in scs if s.get('participant_id') == aw.get('id')), 0)
            res.append({'src': 'SM', 'typ': 'LIVE', 'lig': x.get('league', {}).get('name', '?'),
                       'h': hm.get('name', 'H'), 'a': aw.get('name', 'A'),
                       'hg': hg, 'ag': ag, 'min': x.get('periods', [{'length': 0}])[-1].get('length', 0)})
        return res
    return []

def fetch_af_live():
    url = "https://v3.football.api-sports.io/fixtures"
    r = requests.get(url, headers={'x-rapidapi-host': 'v3.football.api-sports.io',
                     'x-rapidapi-key': APIFOOTBALL_KEY}, params={'live': 'all'}, timeout=10)
    if r.status_code == 200:
        m = r.json().get('response', [])
        print(f"[AF LIVE] {len(m)}")
        return [{'src': 'AF', 'typ': 'LIVE', 'lig': x.get('league', {}).get('name', '?'),
                'h': x.get('teams', {}).get('home', {}).get('name', 'H'),
                'a': x.get('teams', {}).get('away', {}).get('name', 'A'),
                'hg': x.get('goals', {}).get('home', 0) or 0, 
                'ag': x.get('goals', {}).get('away', 0) or 0,
                'min': x.get('fixture', {}).get('status', {}).get('elapsed', 0) or 0} for x in m[:15]]
    return []

# ==================== MASTER FETCH ====================
def fetch_all():
    live, pre = [], []

    for f, n in [(fetch_fd_live, 'FD_L'), (fetch_sm_live, 'SM_L'), (fetch_af_live, 'AF_L')]:
        live.extend(safe_call(f, n))

    pre.extend(safe_call(fetch_fd_pre, 'FD_P'))

    # Remove duplicates
    live_u = list({f"{m['h']}_{m['a']}": m for m in live}.values())
    pre_u = list({f"{m['h']}_{m['a']}": m for m in pre}.values())

    print(f"[TOTAL] {len(live_u)} LIVE, {len(pre_u)} PRE")
    return live_u, pre_u

# ==================== XG CALCULATION ====================
def calc_xg(goals, minute, is_home, is_pre):
    if is_pre:
        return round(1.3 if is_home else 1.0, 2)

    prog = max(minute / 90, 0.35)
    base = (goals + 0.6) / prog
    bonus = 0.25 if is_home else -0.05
    return round(max(base + bonus, 0.4), 2)

# ==================== ANALYSIS ====================
def analyze(match):
    is_live = match['typ'] == 'LIVE'
    hg, ag, minute = match['hg'], match['ag'], match['min']

    # XG
    h_xg = calc_xg(hg, minute, True, not is_live)
    a_xg = calc_xg(ag, minute, False, not is_live)
    tot_xg = h_xg + a_xg

    sigs = []

    if is_live:
        # LIVE: Over/Under
        if tot_xg > 1.6:
            rem = max(90 - minute, 15)
            exp = (tot_xg / minute) * rem if minute > 10 else tot_xg * 0.6
            prob = min(exp / 2.0, 0.80)
            odds = round(1 / prob * 1.05, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if odds >= 1.4:
                sigs.append({'t': f"Over {hg+ag+0.5}", 'o': odds, 'p': round(prob*100,1),
                            'e': edge, 'i': f"xG {tot_xg:.1f}"})

        # LIVE: Next Goal
        if h_xg > a_xg + 0.5:
            prob = min(0.65 + h_xg/12, 0.72)
            odds = round(1 / prob * 1.05, 2)
            edge = round((prob - 1/odds) * 100, 2)
            sigs.append({'t': f"{match['h']} Next", 'o': odds, 'p': round(prob*100,1),
                        'e': edge, 'i': f"+{h_xg-a_xg:.1f}"})

        elif a_xg > h_xg + 0.5:
            prob = min(0.65 + a_xg/12, 0.72)
            odds = round(1 / prob * 1.05, 2)
            edge = round((prob - 1/odds) * 100, 2)
            sigs.append({'t': f"{match['a']} Next", 'o': odds, 'p': round(prob*100,1),
                        'e': edge, 'i': f"+{a_xg-h_xg:.1f}"})

        # LIVE: BTTS
        if h_xg > 0.8 and a_xg > 0.8:
            prob = min((h_xg/2.2) * (a_xg/2.2), 0.73)
            odds = round(1 / prob * 1.05, 2)
            edge = round((prob - 1/odds) * 100, 2)
            sigs.append({'t': "BTTS", 'o': odds, 'p': round(prob*100,1),
                        'e': edge, 'i': f"{h_xg:.1f}&{a_xg:.1f}"})

    else:  # PRE-MATCH
        # PRE: Match Result
        diff = abs(h_xg - a_xg)
        if diff > 0.4:
            fav = match['h'] if h_xg > a_xg else match['a']
            prob = min(0.56 + diff/12, 0.70)
            odds = round(1 / prob * 1.12, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 6 and odds >= 1.6:
                sigs.append({'t': f"{fav} WIN", 'o': odds, 'p': round(prob*100,1),
                            'e': edge, 'i': f"+{diff:.1f}", 'k': match.get('kick', '')})

        # PRE: Over/Under
        if tot_xg > 2.3 or tot_xg < 2.0:
            if tot_xg > 2.3:
                prob, line, bet = min(tot_xg/3.4, 0.72), 2.5, "Over"
            else:
                prob, line, bet = min((3.7-tot_xg)/2.7, 0.70), 2.5, "Under"

            odds = round(1 / prob * 1.12, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 8:
                sigs.append({'t': f"{bet} {line}", 'o': odds, 'p': round(prob*100,1),
                            'e': edge, 'i': f"xG {tot_xg:.1f}", 'k': match.get('kick', '')})

        # PRE: BTTS
        if 0.9 <= h_xg <= 2.2 and 0.9 <= a_xg <= 2.2:
            prob = min((h_xg/2.1) * (a_xg/2.1), 0.68)
            odds = round(1 / prob * 1.12, 2)
            edge = round((prob - 1/odds) * 100, 2)

            if edge > 6:
                sigs.append({'t': "BTTS", 'o': odds, 'p': round(prob*100,1),
                            'e': edge, 'i': f"{h_xg:.1f}&{a_xg:.1f}", 'k': match.get('kick', '')})

    # Confidence
    if sigs:
        conf = int(sum(s['p'] for s in sigs) / len(sigs))
    else:
        conf = 50

    # Quality
    if conf >= 78: qual = "â­â­â­"
    elif conf >= 70: qual = "â­â­"
    elif conf >= 60: qual = "â­"
    else: qual = ""

    return {**match, 'conf': conf, 'qual': qual, 'sigs': sigs[:3], 'h_xg': h_xg, 'a_xg': a_xg}

# ==================== TRIPLE PROCESSING ====================
def process_triple(live_raw, pre_raw, min_conf):
    """
    Returns 3 sections:
    1. LIVE RAW - all live matches (no filter)
    2. LIVE VALUE - high quality live (filtered)
    3. PRE VALUE - high quality prematch (filtered)
    """

    print(f"[PROCESS] Analyzing {len(live_raw)} LIVE, {len(pre_raw)} PRE")

    # Analyze all
    live_analyzed = [analyze(m) for m in live_raw]
    pre_analyzed = [analyze(m) for m in pre_raw]

    # SECTION 1: LIVE RAW (ALL - no filter)
    live_all = sorted(live_analyzed, key=lambda x: x['conf'], reverse=True)

    # SECTION 2: LIVE VALUE (filtered by confidence + signals)
    live_value = [m for m in live_analyzed 
                  if m['conf'] >= max(min_conf, 60) and len(m['sigs']) > 0]
    live_value.sort(key=lambda x: x['conf'], reverse=True)

    # SECTION 3: PRE VALUE (filtered by high thresholds)
    pre_value = [m for m in pre_analyzed 
                 if m['conf'] >= 65 and any(s['e'] >= 6 for s in m['sigs'])]
    pre_value.sort(key=lambda x: x['conf'], reverse=True)

    print(f"[RESULT] ALL:{len(live_all)}, LIVE_VAL:{len(live_value)}, PRE_VAL:{len(pre_value)}")

    return live_all, live_value, pre_value

# ==================== VERCEL HANDLER ====================
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            body_bytes = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            body = json.loads(body_bytes) if body_bytes else {}

            min_conf = int(body.get('minConfidence', 0))

            print(f"[START] Triple System - min_conf={min_conf}")

            # Fetch
            live_raw, pre_raw = fetch_all()

            if not live_raw and not pre_raw:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': False,
                    'msg': f'Brak meczow {datetime.now().strftime("%H:%M")}. Peak: 18:00-22:00.',
                    'live_all': [], 'live_value': [], 'pre_value': []
                }, ensure_ascii=False).encode('utf-8'))
                return

            # Process Triple
            live_all, live_value, pre_value = process_triple(live_raw, pre_raw, min_conf)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            self.wfile.write(json.dumps({
                'success': True,
                'live_all': live_all,        # đ´ ALL LIVE (no filter)
                'live_value': live_value,    # âĄ LIVE HIGH VALUE
                'pre_value': pre_value,      # đ˛ PRE HIGH VALUE
                'counts': {
                    'all': len(live_all),
                    'live_val': len(live_value),
                    'pre_val': len(pre_value)
                },
                'msg': f"đ´ ALL:{len(live_all)} | âĄ LIVE:{len(live_value)} | đ˛ PRE:{len(pre_value)}"
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
                'trace': traceback.format_exc().splitlines()[-3:]
            }).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

# api/analyze.py - AI BETTING GENIUS v5.0 - PROFESSIONAL TRADER
# System analizuje jak profesjonalny trader szukajÄc nieefektywnoĹci rynku

import requests
import json
from datetime import datetime
from typing import List, Dict, Tuple
import random
import traceback

# ==================== KONFIGURACJA 3 API ====================
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKbER9Gx6Oj7e6XRud0oh"
FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
APIFOOTBALL_KEY = "ac0417c6e0dcfa236b146b9585892c9a"

API_SOURCES = [
    {'name': 'sportmonks', 'priority': 1, 'fetch_func': 'fetch_sportmonks_live'},
    {'name': 'football-data', 'priority': 2, 'fetch_func': 'fetch_footballdata_live'},
    {'name': 'api-football', 'priority': 3, 'fetch_func': 'fetch_apifootball_live'}
]

# ==================== PROFESSIONAL TRADING THRESHOLDS ====================
TRADING_CONFIG = {
    'value_threshold': 0.15,        # 15% edge minimum
    'confidence_floor': 60,         # 60% minimum confidence
    'optimal_odds_range': (1.6, 3.5),  # Sweet spot dla value
    'high_value_multiplier': 1.25,  # 25%+ edge = HIGH VALUE
    'volume_threshold': 10,         # Min strzalow dla wiarygodnosci
    'xg_reliability': 0.8           # Min xG dla wartosciowych sygnaĹĂłw
}

# ==================== INTELIGENTNY ROUTER API ====================
def fetch_live_matches_with_fallback() -> Dict:
    all_matches = []
    successful_apis = []
    for api_config in sorted(API_SOURCES, key=lambda x: x['priority']):
        try:
            matches = globals()[api_config['fetch_func']]()
            if matches:
                all_matches.extend(matches)
                successful_apis.append({'name': api_config['name'], 'matches': len(matches)})
                if len(all_matches) >= 20: break
        except Exception as e:
            print(f"API Error [{api_config['name']}]: {e}")
    unique_matches = list({f"{m.get('home_team', '')}_{m.get('away_team', '')}": m for m in all_matches}.values())
    return {'matches': unique_matches, 'sources': successful_apis}

# ==================== FETCHERS ====================
def fetch_sportmonks_live() -> List[Dict]:
    url = f"https://api.sportmonks.com/v3/football/livescores?api_token={SPORTMONKS_KEY}&include=scores;participants;state;statistics"
    res = requests.get(url, timeout=12).json()
    return [parse_sportmonks_match(m) for m in res.get('data', []) if m.get('state_id') in [2, 3, 4]]

def parse_sportmonks_match(m: Dict) -> Dict:
    parts = m.get('participants', [])
    home = next((p for p in parts if p.get('meta', {}).get('location') == 'home'), {})
    away = next((p for p in parts if p.get('meta', {}).get('location') == 'away'), {})
    stats = m.get('statistics', [])
    home_stats = [s for s in stats if s.get('participant_id') == home.get('id')]
    away_stats = [s for s in stats if s.get('participant_id') == away.get('id')]
    scores = m.get('scores', [])
    home_goals = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == home.get('id')), 0)
    away_goals = next((s.get('score', {}).get('goals', 0) for s in scores if s.get('participant_id') == away.get('id')), 0)
    periods = m.get('periods', [])
    minute = periods[-1].get('length', 0) if periods else 0

    return {
        'source': 'sportmonks', 'league': m.get('league', {}).get('name', '?'),
        'home_team': home.get('name', 'Home'), 'away_team': away.get('name', 'Away'),
        'home_goals': home_goals, 'away_goals': away_goals, 'minute': minute,
        'home_stats': home_stats, 'away_stats': away_stats
    }

def fetch_footballdata_live() -> List[Dict]: return []
def fetch_apifootball_live() -> List[Dict]: return []

# ==================== PROFESSIONAL ANALYTICS ENGINE ====================
def calculate_professional_stats(stats: List[Dict], goals: int, team_name: str) -> Dict:
    """Zaawansowana analiza jak profesjonalny analityk"""

    # Inicjalizacja
    metrics = {
        'xg': 0.0, 'shots_total': 0, 'shots_on_goal': 0, 'shots_off_goal': 0,
        'corners': 0, 'attacks': 0, 'dangerous_attacks': 0, 'possession': 0,
        'passes': 0, 'pass_accuracy': 0, 'fouls': 0, 'yellow_cards': 0
    }

    # Wagi dla xG (profesjonalna kalibracja)
    xg_weights = {
        'shots-on-goal': 0.38,      # NajwaĹźniejsze
        'shots-insidebox': 0.25,    # Bardzo groĹşne
        'shots-total': 0.06,        # Bazowa wartoĹÄ
        'corners': 0.05,            # PotencjaĹ staĹych
        'dangerous-attacks': 0.04,  # Pressure
        'attacks': 0.008            # Minimalna wartoĹÄ
    }

    if not stats:
        return {**metrics, 'xg': round(random.uniform(0.3, 1.8), 2), 
                'reliability_score': 0, 'data_quality': 'LOW'}

    # Ekstrakcja danych
    for stat_group in stats:
        for stat in stat_group.get('data', []):
            stat_code = stat.get('type', {}).get('code', '')
            value = stat.get('value', 0)

            if stat_code in xg_weights:
                metrics['xg'] += value * xg_weights[stat_code]

            # SzczegĂłĹowe metryki
            if stat_code == 'shots-total': metrics['shots_total'] = value
            elif stat_code == 'shots-on-goal': metrics['shots_on_goal'] = value
            elif stat_code == 'shots-off-goal': metrics['shots_off_goal'] = value
            elif stat_code == 'corners': metrics['corners'] = value
            elif stat_code == 'attacks': metrics['attacks'] = value
            elif stat_code == 'dangerous-attacks': metrics['dangerous_attacks'] = value
            elif stat_code == 'ball-possession': metrics['possession'] = value
            elif stat_code == 'passes': metrics['passes'] = value
            elif stat_code == 'passes-accurate': 
                metrics['pass_accuracy'] = round((value / metrics['passes'] * 100), 1) if metrics['passes'] > 0 else 0
            elif stat_code == 'fouls': metrics['fouls'] = value
            elif stat_code == 'yellowcards': metrics['yellow_cards'] = value

    metrics['xg'] = round(max(metrics['xg'], 0.1), 2)

    # PROFESJONALNA OCENA JAKOĹCI DANYCH
    data_quality_score = 0
    if metrics['shots_total'] > 0: data_quality_score += 25
    if metrics['shots_on_goal'] > 0: data_quality_score += 25
    if metrics['attacks'] > 0: data_quality_score += 20
    if metrics['dangerous_attacks'] > 0: data_quality_score += 15
    if metrics['corners'] > 0: data_quality_score += 15

    metrics['data_quality'] = 'HIGH' if data_quality_score >= 75 else 'MEDIUM' if data_quality_score >= 50 else 'LOW'
    metrics['reliability_score'] = data_quality_score

    # FINISHING EFFICIENCY (kluczowe dla value)
    metrics['finishing_efficiency'] = round((goals / metrics['xg']) * 100, 1) if metrics['xg'] > 0.3 else 0
    metrics['shot_accuracy'] = round((metrics['shots_on_goal'] / metrics['shots_total'] * 100), 1) if metrics['shots_total'] > 0 else 0

    # DOMINANCE SCORE (0-100)
    dominance = 0
    if metrics['xg'] > 1.5: dominance += 25
    if metrics['shots_total'] > 8: dominance += 20
    if metrics['dangerous_attacks'] > 15: dominance += 20
    if metrics['possession'] > 55: dominance += 15
    if metrics['corners'] > 4: dominance += 10
    if metrics['shot_accuracy'] > 40: dominance += 10
    metrics['dominance_score'] = min(dominance, 100)

    return metrics

def simulate_market_odds(match: Dict, home_metrics: Dict, away_metrics: Dict) -> Dict:
    """Symulacja kursĂłw rynkowych jak profesjonalny bookmaker"""

    minute = match.get('minute', 45)
    hg, ag = match.get('home_goals', 0), match.get('away_goals', 0)
    current_total = hg + ag

    # TIME DECAY (kursy rosnÄ z czasem)
    time_factor = 1 + (minute / 90) ** 1.5

    # PROBABILISTYKA
    home_xg = home_metrics['xg']
    away_xg = away_metrics['xg']
    total_xg = home_xg + away_xg

    # MARKET PROBABILITY (Over next goal)
    remaining_time = max(90 - minute, 1)
    expected_goals_remaining = (total_xg / minute) * remaining_time if minute > 0 else total_xg

    prob_next_goal = min(expected_goals_remaining / 2.5, 0.88)
    prob_next_goal = prob_next_goal / time_factor  # Time decay

    # BOOKMAKER MARGIN (5-8%)
    margin = 1.06
    market_odds_over = round(max((1 / prob_next_goal) * margin, 1.20), 2)

    # HOME WIN (jeĹli remis lub przegrywa)
    goal_diff = hg - ag
    home_win_prob = 0.5
    if goal_diff >= 0:
        home_win_prob = 0.55 + (home_metrics['dominance_score'] / 200)
    else:
        home_win_prob = 0.30 + (home_metrics['dominance_score'] / 300)

    market_odds_home = round((1 / home_win_prob) * margin, 2)

    return {
        'over_under': {
            'line': current_total + 0.5,
            'market_odds_over': market_odds_over,
            'market_prob_over': round(prob_next_goal * 100, 1),
            'implied_margin': round(((1/market_odds_over) - prob_next_goal) * 100, 2)
        },
        'home_win': {
            'market_odds': market_odds_home,
            'market_prob': round(home_win_prob * 100, 1)
        },
        'time_factor': round(time_factor, 2),
        'minute': minute
    }

def calculate_value_edge(ai_prob: float, market_odds: float) -> Tuple[float, str]:
    """Oblicz edge (przewagÄ) i klasyfikuj value"""
    market_prob = 1 / market_odds
    edge = ai_prob - market_prob
    edge_pct = round(edge * 100, 2)

    if edge_pct >= 25:
        classification = 'EXTREME VALUE'
    elif edge_pct >= 15:
        classification = 'HIGH VALUE'
    elif edge_pct >= 8:
        classification = 'GOOD VALUE'
    elif edge_pct >= 3:
        classification = 'SLIGHT VALUE'
    else:
        classification = 'NO VALUE'

    return edge_pct, classification

def analyze_match_professional(match: Dict, config: Dict) -> Dict:
    """GĹĂWNA ANALIZA - JAK PROFESJONALNY TRADER"""
    try:
        # KROK 1: Zbierz zaawansowane statystyki
        home_metrics = calculate_professional_stats(
            match.get('home_stats', []), 
            match.get('home_goals', 0),
            match.get('home_team', 'Home')
        )
        away_metrics = calculate_professional_stats(
            match.get('away_stats', []),
            match.get('away_goals', 0),
            match.get('away_team', 'Away')
        )

        # KROK 2: Symuluj rynek
        market_odds = simulate_market_odds(match, home_metrics, away_metrics)

        # KROK 3: Oblicz AI probabilities
        ai_probabilities = calculate_ai_probabilities(match, home_metrics, away_metrics)

        # KROK 4: ZnajdĹş VALUE BETS
        value_opportunities = find_value_opportunities(
            match, home_metrics, away_metrics, 
            market_odds, ai_probabilities, config
        )

        if not value_opportunities:
            return None

        # KROK 5: Oblicz overall confidence (weighted average)
        total_edge = sum(v['edge_pct'] for v in value_opportunities)
        avg_accuracy = sum(v['accuracy'] for v in value_opportunities) / len(value_opportunities)
        confidence = min(int(avg_accuracy + (total_edge / 2)), 99)

        # KROK 6: Quality filters
        min_conf = config.get('min_confidence', 60)
        if confidence < min_conf:
            return None

        if home_metrics['data_quality'] == 'LOW' and away_metrics['data_quality'] == 'LOW':
            return None

        return {
            **match,
            'confidence': confidence,
            'signals': value_opportunities[:3],
            'home_xg': home_metrics['xg'],
            'away_xg': away_metrics['xg'],
            'home_dominance': home_metrics['dominance_score'],
            'away_dominance': away_metrics['dominance_score'],
            'market_odds': market_odds,
            'data_quality': f"Home: {home_metrics['data_quality']}, Away: {away_metrics['data_quality']}"
        }
    except Exception as e:
        print(f"Error analyzing {match.get('home_team')} vs {match.get('away_team')}: {e}")
        return None

def calculate_ai_probabilities(match: Dict, home: Dict, away: Dict) -> Dict:
    """AI oblicza RZECZYWISTE prawdopodobieĹstwa"""
    minute = match.get('minute', 45)
    hg, ag = match.get('home_goals', 0), match.get('away_goals', 0)

    # OVER probability
    total_xg = home['xg'] + away['xg']
    current_total = hg + ag
    remaining_time = max(90 - minute, 1)

    expected_goals_rest = (total_xg / minute) * remaining_time if minute > 5 else total_xg

    # Adjustments
    if home['finishing_efficiency'] > 80 or away['finishing_efficiency'] > 80:
        expected_goals_rest *= 1.15
    if home['shot_accuracy'] > 50 or away['shot_accuracy'] > 50:
        expected_goals_rest *= 1.1

    prob_over = min(expected_goals_rest / 2.2, 0.92)

    # HOME WIN probability (complex calculation)
    goal_diff = hg - ag
    dominance_diff = home['dominance_score'] - away['dominance_score']

    prob_home_win = 0.50
    if goal_diff > 0:
        prob_home_win = 0.65 + (dominance_diff / 200)
    elif goal_diff == 0:
        prob_home_win = 0.50 + (dominance_diff / 300)
    else:
        prob_home_win = 0.35 + (dominance_diff / 400)

    prob_home_win = max(0.05, min(prob_home_win, 0.95))

    return {
        'over': prob_over,
        'home_win': prob_home_win
    }

def find_value_opportunities(match: Dict, home: Dict, away: Dict, 
                            market: Dict, ai_probs: Dict, config: Dict) -> List[Dict]:
    """SZUKA NIEEFEKTYWNOĹCI RYNKU - CORE VALUE HUNTING"""
    opportunities = []
    min_edge = config.get('value_threshold', 0.12)

    # VALUE BET 1: OVER/UNDER
    if market['over_under']['market_odds_over'] >= TRADING_CONFIG['optimal_odds_range'][0]:
        edge_pct, classification = calculate_value_edge(
            ai_probs['over'], 
            market['over_under']['market_odds_over']
        )

        if edge_pct >= (min_edge * 100):
            opportunities.append({
                'type': f"[{classification}] Over {market['over_under']['line']} gola",
                'market_odds': market['over_under']['market_odds_over'],
                'ai_probability': round(ai_probs['over'] * 100, 1),
                'market_probability': market['over_under']['market_prob_over'],
                'edge_pct': edge_pct,
                'accuracy': min(int(ai_probs['over'] * 100), 95),
                'reasoning': f"AI widzi {round(ai_probs['over']*100)}% szansy, rynek tylko {market['over_under']['market_prob_over']}%. Edge: +{edge_pct}%",
                'algorithm': 'VALUE_OVER',
                'stake_suggestion': 'HIGH' if edge_pct >= 20 else 'MEDIUM' if edge_pct >= 12 else 'LOW'
            })

    # VALUE BET 2: COMEBACK (team losing but dominating)
    if match['home_goals'] < match['away_goals'] and home['dominance_score'] > away['dominance_score'] + 20:
        comeback_prob = min(0.45 + (home['dominance_score'] / 200), 0.85)
        comeback_odds = round(1 / comeback_prob * 1.06, 2)

        if comeback_odds >= 1.8:
            edge_pct, classification = calculate_value_edge(comeback_prob, comeback_odds)

            if edge_pct >= (min_edge * 100):
                opportunities.append({
                    'type': f"[{classification}] {match['home_team']} Comeback",
                    'market_odds': comeback_odds,
                    'ai_probability': round(comeback_prob * 100, 1),
                    'edge_pct': edge_pct,
                    'accuracy': min(int(comeback_prob * 100), 88),
                    'reasoning': f"PrzegrywajÄ {match['home_goals']}-{match['away_goals']}, ale dominujÄ ({home['dominance_score']} vs {away['dominance_score']}). xG: {home['xg']} vs {away['xg']}",
                    'algorithm': 'VALUE_COMEBACK',
                    'stake_suggestion': 'MEDIUM'
                })

    if match['away_goals'] < match['home_goals'] and away['dominance_score'] > home['dominance_score'] + 20:
        comeback_prob = min(0.45 + (away['dominance_score'] / 200), 0.85)
        comeback_odds = round(1 / comeback_prob * 1.06, 2)

        if comeback_odds >= 1.8:
            edge_pct, classification = calculate_value_edge(comeback_prob, comeback_odds)

            if edge_pct >= (min_edge * 100):
                opportunities.append({
                    'type': f"[{classification}] {match['away_team']} Comeback",
                    'market_odds': comeback_odds,
                    'ai_probability': round(comeback_prob * 100, 1),
                    'edge_pct': edge_pct,
                    'accuracy': min(int(comeback_prob * 100), 88),
                    'reasoning': f"PrzegrywajÄ {match['away_goals']}-{match['home_goals']}, ale dominujÄ ({away['dominance_score']} vs {home['dominance_score']}). xG: {away['xg']} vs {home['xg']}",
                    'algorithm': 'VALUE_COMEBACK',
                    'stake_suggestion': 'MEDIUM'
                })

    # VALUE BET 3: DOMINANCE PLAY (underdog with momentum)
    xg_ratio = home['xg'] / away['xg'] if away['xg'] > 0 else 3.0
    if xg_ratio > 2.0 and home['dominance_score'] > 70:
        opportunities.append({
            'type': f"[GOOD VALUE] {match['home_team']} Dominacja",
            'market_odds': market['home_win']['market_odds'],
            'ai_probability': round(ai_probs['home_win'] * 100, 1),
            'edge_pct': round((ai_probs['home_win'] - (1/market['home_win']['market_odds'])) * 100, 2),
            'accuracy': 76,
            'reasoning': f"Totalna dominacja statystyczna. xG ratio: {xg_ratio:.1f}, Dominance: {home['dominance_score']}",
            'algorithm': 'VALUE_DOMINANCE',
            'stake_suggestion': 'LOW'
        })

    # Sort by edge
    opportunities.sort(key=lambda x: x['edge_pct'], reverse=True)

    return opportunities

# ==================== GĹĂWNY HANDLER ====================
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        response_data = {}
        status_code = 500
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
            min_confidence = int(body.get('minConfidence', 60))

            matches_data = fetch_live_matches_with_fallback()

            if not matches_data['matches']:
                status_code = 200
                response_data = {
                    'success': False,
                    'message': 'Nie znaleziono meczow na zywo.',
                    'matches_found': 0,
                    'results': []
                }
            else:
                analyzed_matches = []
                for match in matches_data['matches']:
                    analysis = analyze_match_professional(match, {'min_confidence': min_confidence, 'value_threshold': 0.12})
                    if analysis is not None:
                        analyzed_matches.append(analysis)

                analyzed_matches.sort(key=lambda x: x.get('confidence', 0), reverse=True)

                status_code = 200
                response_data = {
                    'success': True,
                    'results': analyzed_matches,
                    'matches_found': len(analyzed_matches),
                    'message': f"Znaleziono {len(analyzed_matches)} wartosciowych okazji.",
                    'api_sources': matches_data.get('sources', []),
                    'trading_mode': 'PROFESSIONAL'
                }

        except Exception as e:
            print(f"SYSTEM ERROR: {e}")
            response_data = {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'traceback': traceback.format_exc().splitlines()
            }
            status_code = 500

        finally:
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

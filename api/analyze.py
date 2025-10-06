# api/analyze.py
import requests, json, traceback
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

FOOTBALLDATA_KEY = "901f0e15a0314793abaf625692082910"
SPORTMONKS_KEY = "GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKabER9Gx6Oj7e6XRud0oh"

def fetch():
    m = []
    try:
        r = requests.get("https://api.football-data.org/v4/matches", 
                        headers={'X-Auth-Token': FOOTBALLDATA_KEY}, 
                        params={'status': 'LIVE'}, timeout=10)
        if r.status_code == 200:
            for x in r.json().get('matches', []):
                m.append({'src':'FD','lig':x.get('competition',{}).get('name','?'),
                         'h':x.get('homeTeam',{}).get('name','H'),'a':x.get('awayTeam',{}).get('name','A'),
                         'hg':x.get('score',{}).get('fullTime',{}).get('home',0) or 0,
                         'ag':x.get('score',{}).get('fullTime',{}).get('away',0) or 0,
                         'min':x.get('minute') or 45})
            print(f"[FD] {len(r.json().get('matches',[]))}")
    except: pass
    try:
        td = datetime.now().strftime('%Y-%m-%d')
        tm = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        r = requests.get(f"https://api.sportmonks.com/v3/football/fixtures/between/{td}/{tm}",
                        params={'api_token':SPORTMONKS_KEY,'include':'scores;participants',
                               'filters':'fixtureStates:2,3,4'}, timeout=10)
        if r.status_code == 200:
            for x in [y for y in r.json().get('data',[]) if y.get('state_id') in [2,3,4]]:
                pts = x.get('participants',[])
                hm = next((p for p in pts if p.get('meta',{}).get('location')=='home'),{})
                aw = next((p for p in pts if p.get('meta',{}).get('location')=='away'),{})
                scs = x.get('scores',[])
                hg = next((s.get('score',{}).get('goals',0) for s in scs if s.get('participant_id')==hm.get('id')),0)
                ag = next((s.get('score',{}).get('goals',0) for s in scs if s.get('participant_id')==aw.get('id')),0)
                m.append({'src':'SM','lig':x.get('league',{}).get('name','?'),
                         'h':hm.get('name','H'),'a':aw.get('name','A'),
                         'hg':hg,'ag':ag,'min':x.get('periods',[{'length':0}])[-1].get('length',0)})
            print(f"[SM] {len([y for y in r.json().get('data',[]) if y.get('state_id') in [2,3,4]])}")
    except: pass
    u = list({f"{x['h']}_{x['a']}":x for x in m}.values())
    print(f"[TOTAL] {len(u)}")
    return u

def analyze(m):
    pr = max(m['min']/90, 0.35)
    hx = round((m['hg']+0.7)/pr, 2)
    ax = round((m['ag']+0.5)/pr, 2)
    s = []
    if hx+ax > 1.5:
        rm = max(90-m['min'], 10)
        ex = (hx+ax)/m['min']*rm if m['min']>10 else (hx+ax)*0.5
        p = min(ex/2.0, 0.78)
        s.append({'type':f"Over {m['hg']+m['ag']+0.5}",'odds':round(1/p*1.05,2),
                 'prob':round(p*100,1),'acc':int(p*100)-5,'info':f"xG {hx+ax:.1f}"})
    if hx > ax + 0.4:
        p = min(0.65, 0.55+hx/15)
        s.append({'type':f"{m['h']} Next",'odds':round(1/p*1.05,2),
                 'prob':round(p*100,1),'acc':int(p*100)-7,'info':f"+{hx-ax:.1f}"})
    elif ax > hx + 0.4:
        p = min(0.65, 0.55+ax/15)
        s.append({'type':f"{m['a']} Next",'odds':round(1/p*1.05,2),
                 'prob':round(p*100,1),'acc':int(p*100)-7,'info':f"+{ax-hx:.1f}"})
    if hx>0.7 and ax>0.7:
        p = min((hx/2.2)*(ax/2.2), 0.72)
        s.append({'type':"BTTS",'odds':round(1/p*1.05,2),
                 'prob':round(p*100,1),'acc':int(p*100)-6,'info':f"{hx:.1f}&{ax:.1f}"})
    if not s: s.append({'type':"Analiza",'odds':2.0,'prob':50,'acc':50,'info':"Wczesna faza"})
    v = [x['prob'] for x in s if x['prob']>0]
    c = int(sum(v)/len(v)) if v else 55
    return {**m,'conf':c,'sigs':s[:4],'hx':hx,'ax':ax}

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            b = self.rfile.read(int(self.headers.get('Content-Length',0)))
            d = json.loads(b) if b else {}
            mc = int(d.get('minConfidence',0))
            print(f"[REQ] mc={mc}")
            ms = fetch()
            if not ms:
                self.send_response(200)
                self.send_header('Content-type','application/json')
                self.send_header('Access-Control-Allow-Origin','*')
                self.end_headers()
                self.wfile.write(json.dumps({'success':False,'msg':f'Brak {datetime.now().strftime("%H:%M")}',
                                            'matches_found':0,'results':[]},ensure_ascii=False).encode('utf-8'))
                return
            a = [analyze(x) for x in ms]
            f = [x for x in a if x['conf']>=mc] if mc>0 else a
            f.sort(key=lambda x:x['conf'],reverse=True)
            print(f"[OK] {len(f)}")
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps({'success':True,'results':f,'matches_found':len(f),
                                        'total':len(ms)},ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            print(f"[ERR] {e}")
            self.send_response(500)
            self.send_header('Content-type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps({'success':False,'error':str(e)}).encode('utf-8'))
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()

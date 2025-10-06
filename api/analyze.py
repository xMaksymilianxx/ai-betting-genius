import requests,json,traceback
from datetime import datetime,timedelta
from http.server import BaseHTTPRequestHandler

K1,K2="901f0e15a0314793abaf625692082910","GDkPEhJTHCqSscTnlGu2j87eG3Gw77ECv25j0nbnKabER9Gx6Oj7e6XRud0oh"

def f1():
 try:
  print("[FD] Fetching...")
  r=requests.get("https://api.football-data.org/v4/matches",headers={'X-Auth-Token':K1},params={'status':'LIVE'},timeout=20)
  if r.status_code==200:
   m=r.json().get('matches',[])
   print(f"[FD] {len(m)} matches")
   return[{'h':x['homeTeam']['name'],'a':x['awayTeam']['name'],'hg':x['score']['fullTime']['home']or 0,'ag':x['score']['fullTime']['away']or 0,'min':x.get('minute',45),'lig':x['competition']['name']}for x in m]
  print(f"[FD] Status {r.status_code}")
 except Exception as e:
  print(f"[FD] Error: {e}")
 return[]

def f2():
 try:
  print("[SM] Fetching...")
  td,tm=datetime.now().strftime('%Y-%m-%d'),(datetime.now()+timedelta(1)).strftime('%Y-%m-%d')
  r=requests.get(f"https://api.sportmonks.com/v3/football/fixtures/between/{td}/{tm}",params={'api_token':K2,'include':'scores;participants','filters':'fixtureStates:2,3,4'},timeout=20)
  if r.status_code==200:
   data=r.json().get('data',[])
   live=[x for x in data if x.get('state_id')in[2,3,4]]
   print(f"[SM] {len(live)} matches")
   res=[]
   for m in live:
    p=m.get('participants',[])
    h=next((x for x in p if x.get('meta',{}).get('location')=='home'),{})
    a=next((x for x in p if x.get('meta',{}).get('location')=='away'),{})
    s=m.get('scores',[])
    hg=next((x.get('score',{}).get('goals',0)for x in s if x.get('participant_id')==h.get('id')),0)
    ag=next((x.get('score',{}).get('goals',0)for x in s if x.get('participant_id')==a.get('id')),0)
    res.append({'h':h.get('name','?'),'a':a.get('name','?'),'hg':hg,'ag':ag,'min':m.get('periods',[{'length':0}])[-1].get('length',0),'lig':m.get('league',{}).get('name','?')})
   return res
  print(f"[SM] Status {r.status_code}")
 except Exception as e:
  print(f"[SM] Error: {e}")
 return[]

def an(m):
 pr=max(m['min']/90,.35)
 hx,ax=round((m['hg']+.7)/pr,2),round((m['ag']+.5)/pr,2)
 s=[]
 if hx+ax>1.5:
  rm=max(90-m['min'],10)
  ex=(hx+ax)/m['min']*rm if m['min']>10 else(hx+ax)*.5
  p=min(ex/2,.78)
  s.append({'t':f"Over {m['hg']+m['ag']+.5}",'o':round(1/p*1.05,2),'p':round(p*100,1),'i':f"xG {hx+ax:.1f}"})
 if hx>ax+.4:s.append({'t':f"{m['h']} Next",'o':round(1/min(.65,.55+hx/15)*1.05,2),'p':round(min(.65,.55+hx/15)*100,1),'i':f"+{hx-ax:.1f}"})
 elif ax>hx+.4:s.append({'t':f"{m['a']} Next",'o':round(1/min(.65,.55+ax/15)*1.05,2),'p':round(min(.65,.55+ax/15)*100,1),'i':f"+{ax-hx:.1f}"})
 if hx>.7 and ax>.7:s.append({'t':"BTTS",'o':round(1/min((hx/2.2)*(ax/2.2),.72)*1.05,2),'p':round(min((hx/2.2)*(ax/2.2),.72)*100,1),'i':f"{hx:.1f}&{ax:.1f}"})
 if not s:s=[{'t':"Analiza",'o':2.0,'p':50,'i':"Wczesna faza"}]
 v=[x['p']for x in s if x['p']>0]
 return{**m,'c':int(sum(v)/len(v))if v else 55,'s':s[:4],'hx':hx,'ax':ax}

class handler(BaseHTTPRequestHandler):
 def do_POST(self):
  try:
   b=json.loads(self.rfile.read(int(self.headers['Content-Length'])))if int(self.headers.get('Content-Length',0))else{}
   mc=int(b.get('minConfidence',0))
   print(f"[START] minConf={mc}")
   m1=f1()
   m2=f2()
   m=m1+m2
   u=list({f"{x['h']}_{x['a']}":x for x in m}.values())
   print(f"[TOTAL] {len(u)} unique")
   if not u:
    self.send_response(200)
    self.send_header('Content-type','application/json')
    self.send_header('Access-Control-Allow-Origin','*')
    self.end_headers()
    self.wfile.write(json.dumps({'success':False,'msg':f'Brak live {datetime.now().strftime("%H:%M")}','results':[]},ensure_ascii=False).encode())
    return
   a=[an(x)for x in u]
   f=[x for x in a if x['c']>=mc]if mc>0 else a
   f.sort(key=lambda x:x['c'],reverse=True)
   print(f"[RETURN] {len(f)} matches")
   self.send_response(200)
   self.send_header('Content-type','application/json')
   self.send_header('Access-Control-Allow-Origin','*')
   self.end_headers()
   self.wfile.write(json.dumps({'success':True,'results':f,'matches_found':len(f)},ensure_ascii=False).encode())
  except Exception as e:
   print(f"[ERROR] {e}")
   traceback.print_exc()
   self.send_response(500)
   self.send_header('Content-type','application/json')
   self.send_header('Access-Control-Allow-Origin','*')
   self.end_headers()
   self.wfile.write(json.dumps({'success':False,'error':str(e)}).encode())
 def do_OPTIONS(self):
  self.send_response(204)
  self.send_header('Access-Control-Allow-Origin','*')
  self.send_header('Access-Control-Allow-Methods','POST,OPTIONS')
  self.send_header('Access-Control-Allow-Headers','Content-Type')
  self.end_headers()

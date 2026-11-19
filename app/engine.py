import os,json,hashlib,time
from uuid import uuid4
from datetime import datetime,timezone
from sqlalchemy import create_engine,text
from jsonschema import Draft202012Validator
from .metrics import Case,Trace,score,gate,DEFAULT_POLICY

def now(): return datetime.now(timezone.utc).isoformat()
class Engine:
    def __init__(self,url=None): self.db=create_engine(url or os.getenv('DATABASE_URL','sqlite:///./evaltrace.db'))
    def migrate(self):
        with self.db.begin() as c:
            c.execute(text('CREATE TABLE IF NOT EXISTS datasets (id VARCHAR(64) PRIMARY KEY, name VARCHAR(200), version VARCHAR(64) NOT NULL, cases TEXT NOT NULL, created_at VARCHAR(40), UNIQUE(name,version))'))
            c.execute(text('CREATE TABLE IF NOT EXISTS runs (id VARCHAR(64) PRIMARY KEY, dataset_id VARCHAR(64) REFERENCES datasets(id), target VARCHAR(40), status VARCHAR(40), result TEXT, created_at VARCHAR(40))'))
            c.execute(text('CREATE TABLE IF NOT EXISTS gate_policies (id INTEGER PRIMARY KEY, policy TEXT NOT NULL)'))
            c.execute(text('INSERT INTO gate_policies VALUES (1,:p) ON CONFLICT(id) DO NOTHING'),{'p':json.dumps(DEFAULT_POLICY)})
    def policy(self):
        with self.db.connect() as c: return json.loads(c.execute(text('SELECT policy FROM gate_policies WHERE id=1')).scalar_one())
    def register(self,name,raw):
        if len(raw)>100: raise ValueError('At most 100 cases')
        cases=[Case.model_validate(x) for x in raw]
        if not cases or len({c.id for c in cases})!=len(cases): raise ValueError('Cases must have unique IDs and dataset must not be empty')
        for case in cases: Draft202012Validator.check_schema(case.output_schema)
        payload=json.dumps([c.model_dump() for c in cases],sort_keys=True);version=hashlib.sha256(payload.encode()).hexdigest();identity=str(uuid4())
        with self.db.begin() as c:
            existing=c.execute(text('SELECT id FROM datasets WHERE name=:n AND version=:v'),{'n':name,'v':version}).scalar()
            if existing:return {'id':existing,'version':version,'reused':True}
            c.execute(text('INSERT INTO datasets VALUES (:id,:n,:v,:cases,:stamp)'),{'id':identity,'n':name,'v':version,'cases':payload,'stamp':now()})
        return {'id':identity,'version':version,'reused':False}
    def datasets(self):
        with self.db.connect() as c: return [dict(r) for r in c.execute(text('SELECT id,name,version,created_at FROM datasets ORDER BY created_at DESC')).mappings()]
    def execute(self,dataset_id,target):
        with self.db.connect() as c: dataset=c.execute(text('SELECT * FROM datasets WHERE id=:id'),{'id':dataset_id}).mappings().first()
        if not dataset:raise KeyError('Dataset not found')
        if target not in ('fixture-baseline','fixture-regressed','local-http'):raise ValueError('Unknown adapter')
        identity=str(uuid4());policy=self.policy()
        with self.db.begin() as c: c.execute(text('INSERT INTO runs VALUES (:id,:d,:t,:s,:r,:stamp)'),{'id':identity,'d':dataset_id,'t':target,'s':'running','r':'{}','stamp':now()})
        results=[]
        try:
            for raw in json.loads(dataset['cases']):
                case=Case.model_validate(raw);started=time.perf_counter()
                try:
                    if target=='local-http':
                        import httpx
                        endpoint=os.getenv('LOCAL_TARGET_URL','http://127.0.0.1:9000/evaluate')
                        from urllib.parse import urlparse
                        parsed=urlparse(endpoint)
                        if parsed.hostname not in ('127.0.0.1','localhost','::1') or parsed.scheme!='http':raise ValueError('Only loopback HTTP target URLs are allowed')
                        response=httpx.post(endpoint,json={'prompt':case.prompt},timeout=10,follow_redirects=False,trust_env=False);response.raise_for_status();trace=Trace.model_validate(response.json())
                    else: trace=case.fixture if target=='fixture-baseline' else case.regressed_fixture
                except Exception as error:
                    # Store exception class only; URLs/credentials/provider payloads are not logged.
                    trace=Trace(answer='',structured={},completed=False,exception=type(error).__name__)
                scores=score(case,trace)
                results.append({'case_id':case.id,'prompt':case.prompt,'trace':trace.model_dump(),'scores':scores,'elapsed_ms':(time.perf_counter()-started)*1000,'relevant_ids':case.relevant_ids})
            average={k:sum(r['scores'][k] for r in results)/len(results) for k in results[0]['scores']}
            result={'id':identity,'dataset_id':dataset_id,'dataset_version':dataset['version'],'target':target,'scores':average,'gate':gate(average,policy),'policy_snapshot':policy,'cases':results,'mode':'synthetic fixture' if target.startswith('fixture') else 'local HTTP','judge':'not configured; grounded_token_overlap is a lexical heuristic, not a hallucination detector','tokens':None,'cost':None,'metric_version':'1'}
            status='completed'
        except BaseException:
            with self.db.begin() as c:c.execute(text("UPDATE runs SET status='interrupted' WHERE id=:id"),{'id':identity})
            raise
        with self.db.begin() as c:c.execute(text('UPDATE runs SET status=:s,result=:r WHERE id=:id'),{'id':identity,'s':status,'r':json.dumps(result)})
        return result
    def runs(self):
        with self.db.connect() as c:return [dict(r)|{'result':json.loads(r['result'])} for r in c.execute(text('SELECT * FROM runs ORDER BY created_at DESC LIMIT 100')).mappings()]
    def run(self,identity):
        with self.db.connect() as c:r=c.execute(text('SELECT * FROM runs WHERE id=:id'),{'id':identity}).mappings().first()
        if not r:raise KeyError('Run not found')
        return {'status':r['status'],**json.loads(r['result'])}
    def compare(self,baseline,candidate):
        a=self.run(baseline);b=self.run(candidate)
        if a['dataset_version']!=b['dataset_version']:raise ValueError('Comparisons require identical dataset versions')
        return {'baseline':baseline,'candidate':candidate,'delta':{k:b['scores'][k]-a['scores'][k] for k in a['scores']},'candidate_gate':b['gate']}

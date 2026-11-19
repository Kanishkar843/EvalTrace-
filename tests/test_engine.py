import json,math
from pathlib import Path
import pytest
from app.engine import Engine
from app.metrics import Case,Trace,score,recall,ndcg,gate,DEFAULT_POLICY
@pytest.fixture
def raw():return json.loads(Path('data/suite.json').read_text())
@pytest.fixture
def engine(tmp_path):
    e=Engine('sqlite:///'+str(tmp_path/'runs.db'));e.migrate();return e
def test_metric_hand_calculations():
    assert recall(['a','x'],['a','b'],2)==.5
    assert ndcg(['x','a'],['a'])==pytest.approx(1/math.log2(3))
    assert ndcg(['a','a'],['a','b'])==pytest.approx(1/(1+1/math.log2(3)))
    assert recall([],[])==0 and ndcg([],[])==0
def test_output_tools_citations_and_grounding(raw):
    c=Case.model_validate(raw[0]);good=score(c,c.fixture);bad=score(c,c.regressed_fixture)
    assert good['structured_validity']==good['tool_accuracy']==good['grounded_token_overlap']==1
    assert bad['structured_validity']==bad['tool_accuracy']==bad['citation_reference_validity']==0
    c.fixture.citations=[];assert score(c,c.fixture)['grounded_token_overlap']==0
    c.fixture.tools[0].arguments={};assert score(c,c.fixture)['tool_accuracy']==0
def test_immutable_versions_reproducible_runs_gates(engine,raw):
    d=engine.register('demo',raw);assert engine.register('demo',raw)['reused']
    a=engine.execute(d['id'],'fixture-baseline');b=engine.execute(d['id'],'fixture-regressed');repeat=engine.execute(d['id'],'fixture-baseline')
    assert a['gate']['passed'] and not b['gate']['passed']
    assert a['scores']==repeat['scores'] and a['id']!=repeat['id']
    assert engine.compare(a['id'],b['id'])['delta']['recall_at_5']==-1
    engine.db.dispose();assert engine.run(a['id'])['scores']==a['scores']
def test_dataset_validation(engine,raw):
    with pytest.raises(ValueError):engine.register('empty',[])
    with pytest.raises(ValueError):engine.register('dupe',[raw[0],raw[0]])
    with pytest.raises(ValueError):engine.register('corrupt',[{'id':'x'}])
    with pytest.raises(KeyError):engine.execute('absent','fixture-baseline')
def test_unavailable_judge_not_fabricated(engine,raw):
    d=engine.register('demo',raw);r=engine.execute(d['id'],'fixture-baseline')
    assert 'not configured' in r['judge'] and r['tokens'] is None and r['cost'] is None

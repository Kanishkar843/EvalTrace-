import math,re
from pydantic import BaseModel,Field,ConfigDict
from jsonschema import Draft202012Validator
class Tool(BaseModel):
    name:str=Field(max_length=100)
    arguments:dict
class Document(BaseModel):
    id:str=Field(max_length=100)
    text:str=Field(max_length=10000)
class Trace(BaseModel):
    model_config=ConfigDict(extra='forbid')
    answer:str=Field(max_length=10000)
    structured:dict
    tools:list[Tool]=Field(default_factory=list,max_length=30)
    retrieved:list[Document]=Field(default_factory=list,max_length=100)
    citations:list[str]=Field(default_factory=list,max_length=100)
    completed:bool=True
    exception:str|None=None
class Case(BaseModel):
    model_config=ConfigDict(extra='forbid')
    id:str=Field(min_length=1,max_length=100)
    prompt:str=Field(min_length=1,max_length=2000)
    relevant_ids:list[str]=Field(max_length=100)
    expected_tools:list[Tool]=Field(default_factory=list,max_length=30)
    output_schema:dict
    fixture:Trace
    regressed_fixture:Trace

def recall(ranked,relevant,k=5):
    return len(set(ranked[:k])&set(relevant))/len(set(relevant)) if relevant else 0.0
def ndcg(ranked,relevant,k=10):
    # Repeated retrieved IDs earn gain only once.
    seen=set();gain=0
    for rank,identity in enumerate(ranked[:k],1):
        if identity in relevant and identity not in seen: gain+=1/math.log2(rank+1)
        seen.add(identity)
    ideal=sum(1/math.log2(rank+1) for rank in range(1,min(k,len(set(relevant)))+1))
    return gain/ideal if ideal else 0.0
def terms(s): return set(re.findall(r'[a-z0-9]+',s.lower()))
def score(case,trace):
    ranked=[d.id for d in trace.retrieved]; docs={d.id:d.text for d in trace.retrieved}
    support=sum(1 for c in trace.citations if c in docs)/len(trace.citations) if trace.citations else 0.0
    evidence=' '.join(docs[c] for c in trace.citations if c in docs)
    answer_terms=terms(trace.answer);grounded=len(answer_terms&terms(evidence))/len(answer_terms) if answer_terms else 0.0
    return {'structured_validity':float(Draft202012Validator(case.output_schema).is_valid(trace.structured)),
    'tool_accuracy':float([t.model_dump() for t in trace.tools]==[t.model_dump() for t in case.expected_tools]),
    'recall_at_5':recall(ranked,case.relevant_ids),'ndcg_at_10':ndcg(ranked,case.relevant_ids),
    'citation_reference_validity':support,'grounded_token_overlap':grounded,
    'task_completion':float(trace.completed and not trace.exception),'exception_rate':float(bool(trace.exception))}
def gate(scores,policy):
    checks={name:{'value':scores.get(name,0),'floor':floor,'passed':scores.get(name,0)>=floor} for name,floor in policy.items()}
    return {'passed':all(c['passed'] for c in checks.values()),'checks':checks}
DEFAULT_POLICY={'structured_validity':1.0,'tool_accuracy':1.0,'recall_at_5':0.8,'ndcg_at_10':0.8,'citation_reference_validity':1.0,'task_completion':1.0}

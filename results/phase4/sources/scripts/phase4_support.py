"""Phase4 condition adapters and optional samplers; no historical edits."""
from copy import deepcopy
from types import SimpleNamespace
import json

from tais.adaptive.policy import Phase4Sender
from tais.paper_baselines import episodes
from tais.transfer_signals import generate
from ablation_support import cases as ma_cases,make_trace as ma_trace,replay as ma_replay


def new_methods():
    return [f'{kind}-T{t}-U{u}' for kind in ('Robust','Risk') for t in (0,1) for u in (0,1)]


def methods(plan):
    return [f'A{i}' for i in range(8)]+plan['ma1_plan']['baseline_ids']+new_methods()


def cases(plan):
    sweep=plan['sweep']
    return ma_cases(plan['ma1_plan'])+[f'sweep_a{a}_{d}_n{n}' for a in sweep['amplitude_factors']
                                      for d in sweep['durations'] for n in sweep['noise_factors']]


def make_trace(plan,seed,case):
    if case in ma_cases(plan['ma1_plan']):
        return ma_trace(plan['ma1_plan'],seed,case)
    if case not in cases(plan):raise ValueError(case)
    _,a,d,n=case.split('_');amplitude=float(a[1:]);noise=float(n[1:])
    spec=deepcopy(plan['ma1_plan']['generator'])
    spec['events']['amplitude']={c:[v*amplitude for v in bounds] for c,bounds in spec['events']['amplitude'].items()}
    bounds=plan['sweep']['durations'][d]
    spec['events']['duration_ranges']={f'bin{i}':bounds for i in range(3)}
    spec['noise']['sigma']=[v*noise for v in spec['noise']['sigma']]
    tr=generate(spec,seed,'clean_both');tr.scenario=case
    return tr


def replay(trace,cfg,method,plan):
    if method not in new_methods():
        return ma_replay(SimpleNamespace(observed=trace.observed),cfg,method,plan['ma1_plan'])
    kind,t,u=method.split('-')
    sender=Phase4Sender(cfg,plan,kind,trust=t=='T1',selective=u=='U1')
    rows=[]
    try:
        for source in trace.observed:
            item=sender.push(source)
            if item is not None:rows.append(item['record'])
    finally:
        sender.close()
    return episodes(rows,tuple(cfg['channels']))

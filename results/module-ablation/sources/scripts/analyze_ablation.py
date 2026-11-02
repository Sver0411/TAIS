#!/usr/bin/env python3
"""Analyze saved per-run/per-event observations without rerunning policies."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from ablation_support import FACTORS

COLORS = dict(zip(FACTORS, ['#8b8b8b', '#4477aa', '#228833', '#ccbb44',
                          '#66ccee', '#aa3377', '#ee7733', '#cc3311']))
BASELINE_COLORS = dict(zip(['Fixed-5', 'Fixed-20', 'Fixed-60', 'Delta-budget-SU40',
                            'Variance-budget-SU40', 'GateOnly', 'JO-SU-20', 'JO-SU-40'],
                           ['#222222', '#777777', '#bbbbbb', '#7b3294',
                            '#008080', '#8c510a', '#01665e', '#5e3c99']))
PRIMARY = ['f1', 'recall', 'bytes', 'restricted_delay_s', 'fault_induced_false', 'same_fault_fn']


def aggregate(frame):
    tp, fp, n = frame.sender_tp.sum(), frame.sender_fp.sum(), frame.n_events.sum()
    rt, rf = frame.receiver_tp.sum(), frame.receiver_fp.sum()
    return dict(tp=tp, fp=fp, fn=n-tp, n_events=n,
                precision=tp/(tp+fp) if tp+fp else np.nan,
                recall=tp/n if n else np.nan,
                f1=2*tp/(n+tp+fp) if n+tp+fp else np.nan,
                receiver_f1=2*rt/(n+rt+rf) if n+rt+rf else np.nan,
                miss_rate=(n-tp)/n if n else np.nan,
                receiver_recall=rt/n if n else np.nan,
                bytes=frame.binary_v1_bytes.sum(), samples=frame.samples.sum(),
                uploads=frame.uploads.sum(), hours=frame.duration_s.sum()/3600,
                restricted_delay_s=frame.sender_restricted_delay_sum_s.sum()/n if n else np.nan,
                fault_induced_false=frame.sender_fault_induced_false.sum(),
                same_fault_fn=frame.sender_same_fault_fn.sum(),
                frame_age_mean_s=np.average(frame.frame_age_mean_s, weights=frame.duration_s),
                finite_age_mean_s=np.average(frame.finite_value_age_mean_s, weights=frame.duration_s),
                mean_run_p95_age_s=frame.finite_value_age_p95_s.mean(),
                event_samples=frame.event_samples.sum(), nonevent_samples=frame.nonevent_samples.sum(),
                event_seconds=frame.event_seconds.sum(), nonevent_seconds=frame.nonevent_seconds.sum(),
                important_edges_unreported=frame.important_edges_unreported.sum())


def seed_table(frame):
    return pd.DataFrame([dict(seed=s, method=m, **aggregate(g))
                         for (s, m), g in frame.groupby(['seed', 'method'])])


def holm(pvalues):
    p = np.asarray(pvalues)
    order = np.argsort(p)
    result = np.empty(len(p))
    result[order] = np.minimum(1, np.maximum.accumulate((len(p)-np.arange(len(p)))*p[order]))
    return result


def contrasts():
    names = list(FACTORS)
    out = {}
    for newer, older in [('A1', 'A0'), ('A2', 'A0'), ('A3', 'A0'),
                         ('A7', 'A4'), ('A7', 'A5'), ('A7', 'A6')]:
        out[newer+'-'+older] = np.array([int(n == newer)-int(n == older) for n in names])
    # Binary effects: average simple difference / average difference-in-differences.
    for label, axes in [('T', [0]), ('S', [1]), ('U', [2]), ('T:S', [0, 1]),
                        ('T:U', [0, 2]), ('S:U', [1, 2]), ('T:S:U', [0, 1, 2])]:
        out[label] = np.array([np.prod([2*FACTORS[n][axis]-1 for axis in axes]) /
                               2**(3-len(axes)) for n in names])
    return out


def inference(seeds, plan):
    rng = np.random.default_rng(plan['bootstrap_seed'])
    ids = sorted(seeds.seed.unique())
    draw = rng.integers(0, len(ids), size=(plan['bootstrap_draws'], len(ids)))
    signs = rng.choice([-1, 1], size=(plan['permutation_draws'], len(ids)))
    rows = []
    for metric in PRIMARY:
        matrix = seeds.pivot(index='seed', columns='method', values=metric).loc[ids, list(FACTORS)].to_numpy()
        assert np.isfinite(matrix).all()
        for name, weights in contrasts().items():
            delta = matrix @ weights
            point = delta.mean()
            lo, hi = np.percentile(delta[draw].mean(axis=1), [2.5, 97.5])
            p = (1+np.count_nonzero(abs(signs @ delta/len(ids)) >= abs(point)-1e-12))/(len(signs)+1)
            rows.append(dict(contrast=name, metric=metric, mean_seed_difference=point,
                             ci95_low=lo, ci95_high=hi, p_signflip=p, seeds=len(ids)))
    table = pd.DataFrame(rows)
    table['p_holm'] = holm(table.p_signflip)
    table['holm_below_005'] = table.p_holm < .05
    return table


def descriptive_pairs(frame, plan):
    rng = np.random.default_rng(plan['bootstrap_seed'])
    out = []
    for fault, group in frame.groupby('fault_kind'):
        seeds = seed_table(group)
        for metric in ['f1', 'recall', 'fault_induced_false', 'same_fault_fn']:
            pivot = seeds.pivot(index='seed', columns='method', values=metric)
            for a, b in [('A1', 'A0'), ('A7', 'A6')]:
                d = (pivot[a]-pivot[b]).dropna().to_numpy()
                if len(d):
                    draws = rng.integers(0, len(d), size=(plan['bootstrap_draws'], len(d)))
                    lo, hi = np.percentile(d[draws].mean(axis=1), [2.5, 97.5])
                    out.append(dict(fault_kind=fault, contrast=a+'-'+b, metric=metric,
                                    difference=d.mean(), ci95_low=lo, ci95_high=hi,
                                    seeds=len(d), inference='descriptive subgroup; no multiplicity correction'))
    return pd.DataFrame(out)


def figures(frame, events, seeds, effects, out, plan):
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.grid': True, 'grid.alpha': .18, 'savefig.dpi': 180})
    methods = list(FACTORS)+plan['baseline_ids']
    palette = {**COLORS, **BASELINE_COLORS}
    subtitle = f"{frame.seed.nunique()} paired seeds × {frame.scenario.nunique()} scenarios; synthetic; deadline 120 s"
    figdir = out/'figures'
    figdir.mkdir(exist_ok=True)

    def finish(fig, name, title, bottom=0):
        fig.suptitle(title+'\n'+subtitle, fontsize=12)
        fig.tight_layout(rect=(0, bottom, 1, .92))
        fig.savefig(figdir/(name+'.png'), metadata={'Software': 'TAIS ablation'})
        fig.savefig(figdir/(name+'.pdf'), metadata={'CreationDate': None, 'ModDate': None})
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 7))
    for i, method in enumerate(methods):
        g = seeds[seeds.method == method]
        ax.scatter(g.bytes.mean()/1e6, g.f1.mean(), color=palette[method], marker='o' if method in FACTORS else 's', label=method)
        ax.scatter(g.bytes/1e6, g.f1, color=palette[method], s=8, alpha=.17)
    ax.set(xlabel='Application Binary v1 MB per seed (1MB =10⁶ bytes)', ylabel='Sender F1 (mean of seed micro F1)', ylim=(0, 1))
    ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), fontsize=9, frameon=False)
    finish(fig, 'figure1_detection_cost', 'Detection Performance vs Communication Cost')

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    labels = ['F1', 'Application kB per seed', 'Restricted mean delay (s; misses=120s)']
    for ax, metric, label in zip(axes, ['f1', 'bytes', 'restricted_delay_s'], labels):
        rng = np.random.default_rng(plan['bootstrap_seed'])
        for i, method in enumerate(FACTORS):
            values = seeds.loc[seeds.method == method, metric].to_numpy()/(1000 if metric == 'bytes' else 1)
            draws = rng.integers(0, len(values), (plan['bootstrap_draws'], len(values)))
            lo, hi = np.percentile(values[draws].mean(axis=1), [2.5, 97.5])
            ax.bar(i, values.mean(), color=COLORS[method])
            ax.errorbar(i, values.mean(), yerr=[[max(0, values.mean()-lo)], [max(0, hi-values.mean())]], color='black', capsize=3)
        ax.set(xticks=range(8), xticklabels=list(FACTORS), ylabel=label)
    finish(fig, 'figure2_ablation', 'Module Ablation Results (95% seed bootstrap intervals)')

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for ax, metric, label in zip(axes, ['miss_rate', 'fp'], ['Miss rate', 'False positives per seed']):
        data = [seeds.loc[seeds.method == m, metric] for m in methods]
        bp = ax.boxplot(data, tick_labels=methods, patch_artist=True, showfliers=True)
        for patch, m in zip(bp['boxes'], methods):
            patch.set_facecolor(palette[m]); patch.set_alpha(.7)
        ax.set_ylabel(label)
        ax.tick_params(axis='x', rotation=80)
    finish(fig, 'figure3_misses_false', 'Miss Rate and False Positives (whole-seed distributions)')

    fig, axes = plt.subplots(1, 2, figsize=(13, 6))
    for m in list(FACTORS)+['Fixed-20', 'GateOnly', 'JO-SU-40']:
        g = events[(events.method == m) & (events.side == 'sender')]
        delays = np.sort(g.loc[g.matched, 'delay_s'])
        # Denominator includes ALL truth events, so each plateau shows recall.
        axes[0].step(np.r_[0, delays, plan['deadline_s']],
                     np.r_[0, np.arange(1, len(delays)+1)/len(g), len(delays)/len(g)],
                     where='post', label=m, color=palette[m], alpha=.85)
    axes[0].set(xlabel='Delay (s)', ylabel='Fraction of ALL events detected', ylim=(0, 1), xlim=(0, 120))
    axes[0].legend(ncol=2, fontsize=8)
    data = [events.loc[(events.method == m) & (events.side == 'sender') & events.matched, 'delay_s'] for m in methods]
    axes[1].boxplot(data, tick_labels=methods, showfliers=False)
    axes[1].set_ylabel('Delay conditional on detection (s); misses excluded here')
    axes[1].tick_params(axis='x', rotation=80)
    finish(fig, 'figure4_delay', 'Detection Delay Comparison; left denominator retains misses')

    fig, axes = plt.subplots(1, 3, figsize=(15, 6))
    for m in methods:
        g = seeds[seeds.method == m]
        axes[0].scatter(g.bytes.mean()/1000, g.finite_age_mean_s.mean(), color=palette[m], marker='o' if m in FACTORS else 's', label=m)
    axes[0].set(xlabel='Application kB per seed', ylabel='Mean age of latest finite received value (s)')
    summary = {m: aggregate(frame[frame.method == m]) for m in FACTORS}
    for ax, numerator, denominator, label in [
        (axes[1], 'event_samples', 'event_seconds', 'Samples/min during truth events'),
        (axes[2], 'nonevent_samples', 'nonevent_seconds', 'Samples/min outside truth events')]:
        ax.bar(list(FACTORS), [60*summary[m][numerator]/summary[m][denominator] for m in FACTORS], color=list(COLORS.values()))
        ax.set_ylabel(label)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=4, fontsize=9, frameon=False)
    finish(fig, 'figure5_freshness_sampling', 'Data Freshness and Sampling Behavior; per-source-second exposure', bottom=.22)

    fig, axes = plt.subplots(1, 3, figsize=(14, 6))
    names = ['T', 'S', 'U', 'T:S', 'T:U', 'S:U', 'T:S:U']
    for ax, metric, scale, label in zip(axes, ['f1', 'bytes', 'restricted_delay_s'],
                                       [100, .001, 1], ['F1 effect (percentage points)', 'Byte effect (kB per seed)', 'Restricted delay effect (s)']):
        g = effects[effects.metric == metric].set_index('contrast').loc[names]
        y = np.arange(len(names));x = g.mean_seed_difference.to_numpy()*scale
        ax.errorbar(x, y, xerr=[(g.mean_seed_difference-g.ci95_low)*scale,
                               (g.ci95_high-g.mean_seed_difference)*scale], fmt='o', color='#4477aa', capsize=3)
        ax.axvline(0, color='black', lw=.8)
        ax.set(yticks=y, yticklabels=names, xlabel=label)
    finish(fig, 'figure6_contributions', 'Module Contribution Analysis; T=trust, S=sampling, U=upload (95% descriptive CI)')


def analyze(root, phase):
    source = root/phase
    manifest = json.loads((source/'manifest.json').read_text())
    assert manifest['status'] == 'COMPLETE'
    for name, expected in manifest['outputs'].items():
        assert hashlib.sha256((source/name).read_bytes()).hexdigest() == expected, name
    plan = json.loads((root/'sources/configs/module-ablation.json').read_text()) if (root/'freeze.json').exists() else json.loads((ROOT/'configs/module-ablation.json').read_text())
    frame, events = pd.read_csv(source/'metrics.csv'), pd.read_csv(source/'events.csv')
    expected = len(manifest['seeds'])*len(manifest['cases'])*len(manifest['methods'])
    assert len(frame) == expected and not frame.duplicated(['seed', 'scenario', 'method']).any()
    assert frame.groupby(['seed', 'scenario']).observed_sha256.nunique().eq(1).all()
    assert frame.groupby(['seed', 'method']).scenario.nunique().eq(len(manifest['cases'])).all()
    out = source/'analysis'
    out.mkdir(exist_ok=True)
    seeds = seed_table(frame)
    seeds.to_csv(out/'seed_metrics.csv', index=False)
    summary = []
    for (cohort, method), group in frame.groupby(['cohort', 'method']):
        summary.append(dict(group=cohort, method=method, **aggregate(group)))
    for method, group in frame.groupby('method'):
        row = dict(group='all', method=method, **aggregate(group))
        ee = events[(events.method == method) & (events.side == 'sender')]
        for metric in ['delay_s', 'frame_age_at_onset_s', 'sample_age_at_onset_s', 'finite_value_age_at_onset_s']:
            values = ee[metric].dropna()
            for name, fn in [('mean', np.mean), ('median', np.median), ('p95', lambda x: np.percentile(x, 95))]:
                row[metric+'_'+name] = float(fn(values)) if len(values) else np.nan
        summary.append(row)
    baseline = next(r['bytes'] for r in summary if r['group'] == 'all' and r['method'] == 'Fixed-20')
    for row in summary:
        if row['group'] == 'all':
            row['byte_change_vs_fixed20'] = row['bytes']/baseline-1
    pd.DataFrame(summary).to_csv(out/'summary.csv', index=False)
    effects = inference(seeds, plan)
    effects.to_csv(out/'paired_effects.csv', index=False)
    descriptive_pairs(frame, plan).to_csv(out/'fault_trust_effects.csv', index=False)
    distribution = seeds.groupby('method').agg({k: ['mean', 'median', 'std', 'min', 'max'] for k in PRIMARY+['receiver_f1', 'samples', 'frame_age_mean_s', 'mean_run_p95_age_s']})
    distribution.to_csv(out/'distributions.csv')
    groups = [dict(fault_kind=f, method=m, **aggregate(g)) for (f, m), g in frame.groupby(['fault_kind', 'method'])]
    pd.DataFrame(groups).to_csv(out/'fault_summary.csv', index=False)
    # Qualify budgets separately: actual sampling gaps do not establish causal
    # quality superiority, even if a post-hoc gap happens to be small.
    budgets = []
    for a in manifest['methods']:
        for b in ['A0', 'A7', 'Fixed-20', 'GateOnly', 'JO-SU-40']:
            if a == b:
                continue
            x = frame[frame.method == a].sort_values(['seed', 'scenario'])
            y = frame[frame.method == b].sort_values(['seed', 'scenario'])
            budgets.append(dict(method=a, reference=b,
                                sample_gap=x.samples.sum()/y.samples.sum()-1,
                                within_5pct=abs(x.samples.sum()/y.samples.sum()-1) <= plan['budget_tolerance'],
                                exact_same_sample_times=(x.sample_schedule_sha256.to_numpy() == y.sample_schedule_sha256.to_numpy()).all(),
                                interpretation='resource qualification only; no test-time calibration'))
    pd.DataFrame(budgets).to_csv(out/'budget_comparisons.csv', index=False)
    # Delay differences on identical truth events detected by BOTH methods.
    delay_rows = []
    e = events[events.side == 'sender']
    for a, b in [('A1', 'A0'), ('A2', 'A0'), ('A3', 'A0'), ('A7', 'A4'), ('A7', 'A5'), ('A7', 'A6')]:
        both = e[e.method == a].merge(e[e.method == b], on=['seed', 'scenario', 'channel', 'truth_start'], suffixes=('_a', '_b'))
        both = both[both.matched_a & both.matched_b]
        for s, g in both.groupby('seed'):
            delay_rows.append(dict(contrast=a+'-'+b, seed=s, events=len(g),
                                   mean_delay_difference_s=(g.delay_s_a-g.delay_s_b).mean()))
    pd.DataFrame(delay_rows).to_csv(out/'matched_in_both_delays.csv', index=False)
    figures(frame, events, seeds, effects, out, plan)
    files = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'analysis_manifest.json')
    (out/'analysis_manifest.json').write_text(json.dumps(dict(
        inputs=manifest['outputs'], analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        bootstrap_draws=plan['bootstrap_draws'], bootstrap_unit='whole paired seed',
        inference='mean of seed micro metrics; sign-flip exchangeability assumption; Holm across78 prespecified tests; subgroup CI descriptive',
        outputs={str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}), indent=2)+'\n')
    print(out, 'analysis complete;', len(frame), 'runs;', len(events), 'side-specific event records')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT/'results/module-ablation')
    parser.add_argument('--phase', choices=['engineering', 'test'], default='test')
    args = parser.parse_args()
    analyze(args.root, args.phase)

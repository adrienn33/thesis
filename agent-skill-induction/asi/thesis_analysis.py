#!/usr/bin/env python3
"""
Thesis Analysis Script - Agent Skill Induction (ASI) on WebArena
================================================================
Produces all tables, figures, and statistical tests for the thesis.

Usage:
    python3 thesis_analysis.py [--cohort COHORT_DIR] [--pre-es COHORT_DIR] [--output-dir DIR]

Defaults:
    --cohort   results/final/cohort_25
    --pre-es   results/final/cohort_23   (pre-Elasticsearch MCP baseline)
    --output-dir thesis_outputs
"""

import json
import csv
import os
import sys
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.patches import Patch, FancyArrowPatch

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONDITIONS = ['Vanilla', 'Vanilla+ASI', 'MCP', 'MCP+ASI']
CONDITION_COLORS = {
    'Vanilla': '#6c757d',
    'Vanilla+ASI': '#17a2b8',
    'MCP': '#28a745',
    'MCP+ASI': '#007bff',
}
CONDITION_SHORT = {
    'Vanilla': 'Van',
    'Vanilla+ASI': 'Van+ASI',
    'MCP': 'MCP',
    'MCP+ASI': 'MCP+ASI',
}
N_BOOTSTRAP = 10_000
ALPHA = 0.05
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Data Loading
# ---------------------------------------------------------------------------

def load_cohort(cohort_dir: str) -> dict[str, list[dict]]:
    """Load all research_metrics.json from a cohort directory.

    Returns: {condition_name: [metrics_dict, ...]} keyed by task_id internally.
    """
    cohort_path = Path(cohort_dir)
    data = {}
    for cond in CONDITIONS:
        cond_path = cohort_path / cond
        if not cond_path.exists():
            continue
        records = []
        for f in sorted(cond_path.glob('webarena.*_research_metrics.json')):
            with open(f) as fh:
                records.append(json.load(fh))
        data[cond] = records
    return data


def load_taxonomy(taxonomy_path: str) -> pd.DataFrame:
    """Load thesis_taxonomy.csv."""
    df = pd.read_csv(taxonomy_path)
    # Normalize column names
    df.columns = [c.strip() for c in df.columns]
    # Ensure Task # is string for matching
    if 'Task #' in df.columns:
        df['task_id'] = df['Task #'].astype(str).str.strip()
    return df


def records_to_df(data: dict[str, list[dict]]) -> pd.DataFrame:
    """Flatten condition->records into a single DataFrame."""
    rows = []
    for cond, records in data.items():
        for r in records:
            rows.append({
                'condition': cond,
                'task_id': str(r['task_id']),
                'success': r['task_execution']['success'],
                'reward': r['task_execution']['reward'],
                'steps': r['task_execution']['steps'],
                'total_steps': r['task_execution']['total_steps'],
                'elapsed_time': r['task_execution']['elapsed_time'],
                'agent_elapsed_time': r['task_execution']['agent_elapsed_time'],
                'terminated': r['task_execution']['terminated'],
                'truncated': r['task_execution']['truncated'],
                'total_input_tokens': r.get('token_usage', {}).get('total_input_tokens', 0),
                'mcp_call_count': r.get('mcp_call_count', 0),
                'browser_action_count': r.get('browser_action_count', 0),
                'skill_call_count': r.get('skill_call_count', 0),
                'skills_reused_count': r.get('skills_reused_count', 0),
                'skills_induced_count': r.get('skills_induced_count', 0),
                'mcp_enabled': r.get('configuration', {}).get('mcp_enabled', False),
                'asi_enabled': r.get('configuration', {}).get('asi_enabled', False),
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Confidence Intervals
# ---------------------------------------------------------------------------

def bootstrap_ci(values, stat_fn=np.mean, n_boot=N_BOOTSTRAP, alpha=ALPHA, seed=RANDOM_SEED):
    """Bootstrap CI for continuous metrics (tokens, steps)."""
    rng = np.random.RandomState(seed)
    arr = np.asarray(values)
    boot_stats = np.array([stat_fn(rng.choice(arr, size=len(arr), replace=True)) for _ in range(n_boot)])
    lo = np.percentile(boot_stats, 100 * alpha / 2)
    hi = np.percentile(boot_stats, 100 * (1 - alpha / 2))
    return stat_fn(arr), lo, hi


def proportion_ci(successes, n, alpha=ALPHA):
    """Normal approximation 95% CI for a proportion.

    p ± z * sqrt(p*(1-p)/n)  where z=1.96 for 95%.
    """
    p = successes / n if n > 0 else 0.0
    z = stats.norm.ppf(1 - alpha / 2)
    se = np.sqrt(p * (1 - p) / n) if n > 0 else 0.0
    return p, max(0.0, p - z * se), min(1.0, p + z * se)


# ---------------------------------------------------------------------------
# Table 1: Success Rate across 4 conditions
# ---------------------------------------------------------------------------

def table_success_rate(df: pd.DataFrame) -> pd.DataFrame:
    """Table 1: Success rate with 95% CI (normal approximation)."""
    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        n = len(sub)
        s = int(sub['success'].sum())
        mean, lo, hi = proportion_ci(s, n)
        rows.append({
            'Condition': cond,
            'N': n,
            'Successes': s,
            'Success Rate': f'{mean:.1%}',
            '95% CI': f'[{lo:.1%}, {hi:.1%}]',
            '_rate': mean,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Table 2: Adjusted (strict + functional) success rate
# ---------------------------------------------------------------------------

def table_adjusted_success(df: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Table 2: Adjusted success rate using secondary_label from taxonomy."""
    if 'secondary_label' not in taxonomy.columns:
        print("  [SKIP] Table 2: No 'secondary_label' column in taxonomy. "
              "Add it per Phase 5 instructions to enable this table.")
        return pd.DataFrame()

    # Build set of task_ids that are functional_success
    functional_tasks = set(
        taxonomy[taxonomy['secondary_label'] == 'functional_success']['task_id'].values
    )

    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        n = len(sub)
        strict_sum = int(sub['success'].sum())
        adjusted_sum = sum(
            1 if row['success'] or row['task_id'] in functional_tasks else 0
            for _, row in sub.iterrows()
        )
        s_mean, s_lo, s_hi = proportion_ci(strict_sum, n)
        a_mean, a_lo, a_hi = proportion_ci(adjusted_sum, n)
        rows.append({
            'Condition': cond,
            'N': len(strict),
            'Strict Rate': f'{s_mean:.1%}',
            'Strict CI': f'[{s_lo:.1%}, {s_hi:.1%}]',
            'Adjusted Rate': f'{a_mean:.1%}',
            'Adjusted CI': f'[{a_lo:.1%}, {a_hi:.1%}]',
            'Recovered': int(adjusted.sum() - strict.sum()),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Table 3: Step count
# ---------------------------------------------------------------------------

def table_step_count(df: pd.DataFrame) -> pd.DataFrame:
    """Table 3: Step count across conditions."""
    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        vals = sub['steps'].values
        mean, lo, hi = bootstrap_ci(vals, stat_fn=np.mean)
        med, med_lo, med_hi = bootstrap_ci(vals, stat_fn=np.median)
        rows.append({
            'Condition': cond,
            'Mean Steps': f'{mean:.2f}',
            'Mean CI': f'[{lo:.2f}, {hi:.2f}]',
            'Median Steps': f'{med:.1f}',
            'Median CI': f'[{med_lo:.1f}, {med_hi:.1f}]',
            'Std': f'{np.std(vals):.2f}',
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Table 4: Token usage
# ---------------------------------------------------------------------------

def table_token_usage(df: pd.DataFrame) -> pd.DataFrame:
    """Table 4: Token usage across conditions."""
    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        vals = sub['total_input_tokens'].values
        mean, lo, hi = bootstrap_ci(vals, stat_fn=np.mean)
        med, med_lo, med_hi = bootstrap_ci(vals, stat_fn=np.median)
        rows.append({
            'Condition': cond,
            'Mean Tokens': f'{mean:,.0f}',
            'Mean CI': f'[{lo:,.0f}, {hi:,.0f}]',
            'Median Tokens': f'{med:,.0f}',
            'Median CI': f'[{med_lo:,.0f}, {med_hi:,.0f}]',
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Table 5: Per-task paired comparison
# ---------------------------------------------------------------------------

def table_per_task(df: pd.DataFrame) -> pd.DataFrame:
    """Table 5: Per-task comparison (187 rows)."""
    pivot = df.pivot_table(
        index='task_id',
        columns='condition',
        values=['success', 'steps', 'total_input_tokens'],
        aggfunc='first'
    )
    # Flatten multi-index columns
    pivot.columns = [f'{metric}_{cond}' for metric, cond in pivot.columns]
    pivot = pivot.reset_index()
    pivot = pivot.sort_values('task_id', key=lambda x: x.astype(int))
    return pivot


# ---------------------------------------------------------------------------
# Table 6: Failure taxonomy frequency
# ---------------------------------------------------------------------------

def table_taxonomy_frequency(taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Table 6: Failure category counts."""
    if 'Category' not in taxonomy.columns:
        return pd.DataFrame()
    counts = taxonomy['Category'].value_counts().reset_index()
    counts.columns = ['Category', 'Count']
    counts['Percentage'] = (counts['Count'] / counts['Count'].sum() * 100).round(1)
    return counts


# ---------------------------------------------------------------------------
# Table 7: Semantic search impact (pre-ES vs post-ES)
# ---------------------------------------------------------------------------

def table_semantic_impact(df: pd.DataFrame, pre_es_df: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Table 7: Pre-ES vs post-ES on semantic-flagged tasks."""
    if taxonomy.empty or 'Semantic?' not in taxonomy.columns:
        return pd.DataFrame()

    semantic_tasks = set(
        taxonomy[taxonomy['Semantic?'].str.strip().str.lower() == 'yes']['task_id'].values
    )
    if not semantic_tasks:
        print("  [SKIP] Table 7: No Semantic?=Yes tasks in taxonomy.")
        return pd.DataFrame()

    # Get MCP results for these tasks
    mcp_post = df[(df['condition'] == 'MCP') & (df['task_id'].isin(semantic_tasks))]
    mcp_pre = pre_es_df[(pre_es_df['condition'] == 'MCP') & (pre_es_df['task_id'].isin(semantic_tasks))]

    rows = []
    for tid in sorted(semantic_tasks, key=int):
        pre_row = mcp_pre[mcp_pre['task_id'] == tid]
        post_row = mcp_post[mcp_post['task_id'] == tid]
        pre_success = bool(pre_row['success'].values[0]) if not pre_row.empty else None
        post_success = bool(post_row['success'].values[0]) if not post_row.empty else None
        cat = taxonomy[taxonomy['task_id'] == tid]['Category'].values
        rows.append({
            'Task ID': tid,
            'Category': cat[0] if len(cat) > 0 else '',
            'Pre-ES': 'Pass' if pre_success else ('Fail' if pre_success is not None else 'N/A'),
            'Post-ES': 'Pass' if post_success else ('Fail' if post_success is not None else 'N/A'),
            'Flipped': 'Yes' if (not pre_success and post_success) else '',
        })

    result_df = pd.DataFrame(rows)

    # Summary row
    pre_pass = sum(1 for r in rows if r['Pre-ES'] == 'Pass')
    post_pass = sum(1 for r in rows if r['Post-ES'] == 'Pass')
    flipped = sum(1 for r in rows if r['Flipped'] == 'Yes')
    print(f"  Semantic tasks: {len(rows)} | Pre-ES pass: {pre_pass} | Post-ES pass: {post_pass} | Flipped: {flipped}")

    # Also compute full benchmark comparison
    mcp_pre_all = pre_es_df[pre_es_df['condition'] == 'MCP']
    mcp_post_all = df[df['condition'] == 'MCP']
    if not mcp_pre_all.empty and not mcp_post_all.empty:
        pre_rate = mcp_pre_all['success'].mean()
        post_rate = mcp_post_all['success'].mean()
        print(f"  Full benchmark: Pre-ES {pre_rate:.1%} ({int(mcp_pre_all['success'].sum())}/187) -> "
              f"Post-ES {post_rate:.1%} ({int(mcp_post_all['success'].sum())}/187)")

    return result_df


# ---------------------------------------------------------------------------
# Table 8: ASI interaction effect
# ---------------------------------------------------------------------------

def table_asi_interaction(df: pd.DataFrame) -> pd.DataFrame:
    """Table 8: 2x2 ASI interaction (does ASI help MCP more than browser?)."""
    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        rate = sub['success'].mean()
        rows.append({
            'Condition': cond,
            'MCP': 'Yes' if 'MCP' in cond else 'No',
            'ASI': 'Yes' if 'ASI' in cond else 'No',
            'Success Rate': rate,
            'N': len(sub),
        })
    result = pd.DataFrame(rows)

    # Compute interaction
    rates = {r['Condition']: r['Success Rate'] for r in rows}
    if all(c in rates for c in CONDITIONS):
        asi_effect_vanilla = rates['Vanilla+ASI'] - rates['Vanilla']
        asi_effect_mcp = rates['MCP+ASI'] - rates['MCP']
        interaction = asi_effect_mcp - asi_effect_vanilla
        print(f"  ASI effect (Vanilla): {asi_effect_vanilla:+.1%}")
        print(f"  ASI effect (MCP):     {asi_effect_mcp:+.1%}")
        print(f"  Interaction:          {interaction:+.1%} "
              f"({'MCP benefits more' if interaction > 0 else 'Vanilla benefits more'})")

    return result


# ---------------------------------------------------------------------------
# Statistical Tests
# ---------------------------------------------------------------------------

def mcnemar_test(df: pd.DataFrame, cond_a: str, cond_b: str) -> dict:
    """McNemar's test for paired binary outcomes."""
    a = df[df['condition'] == cond_a].set_index('task_id')['success']
    b = df[df['condition'] == cond_b].set_index('task_id')['success']
    common = a.index.intersection(b.index)
    a, b = a.loc[common].astype(int), b.loc[common].astype(int)

    # Contingency: b=1,a=0 (b wins) vs b=0,a=1 (a wins)
    b_wins = ((b == 1) & (a == 0)).sum()  # discordant: B success, A fail
    a_wins = ((a == 1) & (b == 0)).sum()  # discordant: A success, B fail

    n_discordant = b_wins + a_wins
    if n_discordant == 0:
        return {'comparison': f'{cond_a} vs {cond_b}', 'statistic': 0, 'p_value': 1.0,
                'b_wins': int(b_wins), 'a_wins': int(a_wins), 'n': len(common)}

    # Use exact binomial test (more appropriate for small discordant counts)
    # Under H0, discordant pairs are equally likely to favor either condition
    p_value = stats.binomtest(int(b_wins), int(n_discordant), 0.5).pvalue

    return {
        'comparison': f'{cond_a} vs {cond_b}',
        'statistic': float((b_wins - a_wins)**2 / n_discordant),
        'p_value': float(p_value),
        f'{cond_b}_wins': int(b_wins),
        f'{cond_a}_wins': int(a_wins),
        'n_discordant': int(n_discordant),
        'n': len(common),
    }


def wilcoxon_test(df: pd.DataFrame, cond_a: str, cond_b: str, metric: str) -> dict:
    """Wilcoxon signed-rank test for paired continuous outcomes."""
    a = df[df['condition'] == cond_a].set_index('task_id')[metric]
    b = df[df['condition'] == cond_b].set_index('task_id')[metric]
    common = a.index.intersection(b.index)
    a_vals, b_vals = a.loc[common].values, b.loc[common].values

    diff = b_vals - a_vals
    # Remove zeros for Wilcoxon
    nonzero = diff != 0
    if nonzero.sum() < 10:
        return {'comparison': f'{cond_a} vs {cond_b}', 'metric': metric,
                'statistic': np.nan, 'p_value': np.nan, 'note': 'too few non-zero diffs'}

    stat, p = stats.wilcoxon(a_vals[nonzero], b_vals[nonzero])
    return {
        'comparison': f'{cond_a} vs {cond_b}',
        'metric': metric,
        'statistic': float(stat),
        'p_value': float(p),
        'mean_diff': float(np.mean(diff)),
        'median_diff': float(np.median(diff)),
        'n': int(nonzero.sum()),
    }


def run_all_statistical_tests(df: pd.DataFrame) -> dict:
    """Run all pairwise statistical tests."""
    results = {'mcnemar': [], 'wilcoxon_tokens': [], 'wilcoxon_steps': []}

    pairs = [
        ('Vanilla', 'MCP'),
        ('Vanilla', 'Vanilla+ASI'),
        ('MCP', 'MCP+ASI'),
        ('Vanilla', 'MCP+ASI'),
        ('Vanilla+ASI', 'MCP+ASI'),
        ('Vanilla+ASI', 'MCP'),
    ]

    for a, b in pairs:
        if df[df['condition'] == a].empty or df[df['condition'] == b].empty:
            continue
        results['mcnemar'].append(mcnemar_test(df, a, b))
        results['wilcoxon_tokens'].append(wilcoxon_test(df, a, b, 'total_input_tokens'))
        results['wilcoxon_steps'].append(wilcoxon_test(df, a, b, 'steps'))

    return results


# ---------------------------------------------------------------------------
# Additional Analyses
# ---------------------------------------------------------------------------

def analysis_win_loss_tie(df: pd.DataFrame) -> pd.DataFrame:
    """Win/loss/tie counts for each condition pair."""
    pairs = [
        ('MCP', 'Vanilla'),
        ('MCP+ASI', 'Vanilla+ASI'),
        ('MCP+ASI', 'Vanilla'),
        ('MCP+ASI', 'MCP'),
        ('Vanilla+ASI', 'Vanilla'),
    ]
    rows = []
    for a, b in pairs:
        sa = df[df['condition'] == a].set_index('task_id')['success']
        sb = df[df['condition'] == b].set_index('task_id')['success']
        common = sa.index.intersection(sb.index)
        sa, sb = sa.loc[common].astype(int), sb.loc[common].astype(int)
        wins = int((sa > sb).sum())
        losses = int((sa < sb).sum())
        ties = int((sa == sb).sum())
        rows.append({'Comparison': f'{a} vs {b}', f'{a} Wins': wins, f'{b} Wins': losses, 'Ties': ties})
    return pd.DataFrame(rows)


def analysis_cost_per_success(df: pd.DataFrame) -> pd.DataFrame:
    """Tokens per successful task by condition."""
    rows = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        successes = sub[sub['success']]
        total_tokens = sub['total_input_tokens'].sum()
        n_success = len(successes)
        tokens_per_success = total_tokens / n_success if n_success > 0 else float('inf')
        rows.append({
            'Condition': cond,
            'Total Tokens': f'{total_tokens:,.0f}',
            'Successes': n_success,
            'Tokens/Success': f'{tokens_per_success:,.0f}',
            'Mean Tokens (all)': f'{sub["total_input_tokens"].mean():,.0f}',
            'Mean Tokens (success only)': f'{successes["total_input_tokens"].mean():,.0f}' if n_success > 0 else 'N/A',
        })
    return pd.DataFrame(rows)


def analysis_task_difficulty(df: pd.DataFrame) -> dict:
    """Task difficulty analysis."""
    results = {}
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        one_shot = (sub['steps'] == 1).sum()
        results[cond] = {
            'one_shot_count': int(one_shot),
            'one_shot_pct': one_shot / len(sub),
            'mean_steps': sub['steps'].mean(),
            'truncated_count': int(sub['truncated'].sum()),
            'truncated_pct': sub['truncated'].mean(),
        }

    # Floor/ceiling analysis across all conditions
    pivot = df.pivot_table(index='task_id', columns='condition', values='success', aggfunc='first')
    all_pass = (pivot.sum(axis=1) == len(CONDITIONS))
    all_fail = (pivot.sum(axis=1) == 0)
    results['_summary'] = {
        'ceiling_tasks': int(all_pass.sum()),
        'ceiling_pct': float(all_pass.mean()),
        'floor_tasks': int(all_fail.sum()),
        'floor_pct': float(all_fail.mean()),
        'differentiating_tasks': int((~all_pass & ~all_fail).sum()),
    }
    return results


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------

def fig_efficiency_frontier(df: pd.DataFrame, taxonomy: pd.DataFrame, output_dir: str):
    """Figure 1 (Hero Figure): Efficiency frontier - success rate vs token cost.

    X-axis shows tokens saved relative to Vanilla baseline so that right = cheaper = better,
    keeping the standard left-to-right increasing convention.
    Uses adjusted success rate if secondary_label is available in taxonomy,
    otherwise falls back to strict success rate.
    """
    import matplotlib as mpl

    # Determine whether we can use adjusted success
    has_adjusted = 'secondary_label' in taxonomy.columns if not taxonomy.empty else False
    functional_tasks = set()
    if has_adjusted:
        functional_tasks = set(
            taxonomy[taxonomy['secondary_label'] == 'functional_success']['task_id'].values
        )
    rate_label = 'Adjusted Success Rate' if has_adjusted else 'Success Rate'

    CONDITION_MARKERS = {
        'Vanilla': 's',       # square
        'Vanilla+ASI': 'D',   # diamond
        'MCP': '^',           # triangle up
        'MCP+ASI': 'o',       # circle
    }

    # First pass: compute stats for all conditions
    condition_stats = {}
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        n = len(sub)
        if has_adjusted:
            s = sum(1 if row['success'] or row['task_id'] in functional_tasks else 0
                    for _, row in sub.iterrows())
        else:
            s = int(sub['success'].sum())
        sr_mean, sr_lo, sr_hi = proportion_ci(s, n)
        tk_mean, tk_lo, tk_hi = bootstrap_ci(sub['total_input_tokens'].values, stat_fn=np.mean)
        condition_stats[cond] = dict(
            tk_mean=tk_mean, tk_lo=tk_lo, tk_hi=tk_hi,
            sr_mean=sr_mean, sr_lo=sr_lo, sr_hi=sr_hi,
        )

    vanilla_baseline = condition_stats.get('Vanilla', {}).get('tk_mean', 0)

    # Use serif font to match LaTeX paper typography
    rc_overrides = {
        'font.family': 'serif',
        'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
    }
    with mpl.rc_context(rc_overrides):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        points = {}  # cond -> (tokens_saved, sr_pct)

        for cond in CONDITIONS:
            if cond not in condition_stats:
                continue
            st = condition_stats[cond]
            tokens_saved = vanilla_baseline - st['tk_mean']
            sr_mean = st['sr_mean']
            points[cond] = (tokens_saved, sr_mean * 100)

            ax.errorbar(
                tokens_saved, sr_mean * 100,
                xerr=[[st['tk_mean'] - st['tk_lo']], [st['tk_hi'] - st['tk_mean']]],
                yerr=[[sr_mean * 100 - st['sr_lo'] * 100], [st['sr_hi'] * 100 - sr_mean * 100]],
                fmt=CONDITION_MARKERS[cond], markersize=14, capsize=6, capthick=2,
                color=CONDITION_COLORS[cond],
                label=f'{cond}  ({sr_mean:.1%}, {st["tk_mean"]/1000:.0f}k tok)',
                linewidth=2, markeredgecolor='white', markeredgewidth=1.5,
                zorder=5,
            )

        # Draw straight dashed arrows showing architectural upgrade paths
        arrow_pairs = [
            ('Vanilla', 'Vanilla+ASI'),
            ('Vanilla', 'MCP'),
            ('MCP', 'MCP+ASI'),
        ]
        for a, b in arrow_pairs:
            if a in points and b in points:
                ax.annotate('', xy=points[b], xytext=points[a],
                            arrowprops=dict(arrowstyle='->', color='#bbbbbb', lw=1.5,
                                            linestyle='dashed',
                                            connectionstyle='arc3,rad=0.0'),
                            zorder=1)

        ax.set_xlabel('Tokens Saved vs. Vanilla Baseline', fontsize=14)
        ax.set_ylabel(f'{rate_label} (%)', fontsize=14)
        ax.legend(fontsize=12, loc='lower left', framealpha=0.9)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f'{x/1000:.0f}k'))
        ax.grid(True, alpha=0.25, linestyle='--')
        ax.tick_params(labelsize=12)

        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, 'fig1_efficiency_frontier.pdf'), bbox_inches='tight')
        plt.close(fig)


def fig_token_reduction(df: pd.DataFrame, output_dir: str):
    """Figure 2: Per-task token reduction (MCP vs Vanilla) - violin/box plot."""
    import matplotlib as mpl

    van = df[df['condition'] == 'Vanilla'].set_index('task_id')['total_input_tokens']
    mcp = df[df['condition'] == 'MCP'].set_index('task_id')['total_input_tokens']
    common = van.index.intersection(mcp.index)

    reduction_pct = ((van.loc[common].values - mcp.loc[common].values) / van.loc[common].values) * 100

    rc_overrides = {
        'font.family': 'serif',
        'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
    }
    with mpl.rc_context(rc_overrides):
        import seaborn as sns
        fig, ax = plt.subplots(figsize=(7, 4.5))

        # Seaborn violin with cut=0 to clamp KDE exactly at data bounds (no >100% bleed)
        sns.violinplot(
            y=reduction_pct, color=CONDITION_COLORS['MCP'],
            inner='box', cut=0, linewidth=1.2, ax=ax,
        )
        # Soften the violin fill alpha after the fact
        for art in ax.collections:
            art.set_alpha(0.55)

        # Baseline: bold horizontal reference with subtle win/loss region shading
        data_min = float(np.min(reduction_pct))
        data_max = float(np.max(reduction_pct))
        ax.axhline(y=0, color='#CC3333', linestyle='--', linewidth=1.8, zorder=2)
        ax.fill_between([-0.5, 0.5], 0, data_max, color='#2ca02c', alpha=0.035)
        ax.fill_between([-0.5, 0.5], data_min, 0, color='#CC3333', alpha=0.035)

        ax.set_ylabel('Token Reduction vs. Vanilla (%)', fontsize=14)
        ax.set_xticks([0])
        ax.set_xticklabels(['MCP vs. Vanilla'], fontsize=14)
        ax.tick_params(labelsize=12)
        ax.grid(True, alpha=0.25, axis='y', linestyle='--')

        mean_red = float(np.mean(reduction_pct))
        med_red = float(np.median(reduction_pct))
        ax.annotate(f'Mean: {mean_red:.1f}%\nMedian: {med_red:.1f}%',
                    xy=(0.97, 0.97), xycoords='axes fraction',
                    ha='right', va='top', fontsize=12,
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#cccccc', alpha=0.85))

        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, 'fig2_token_reduction.pdf'), bbox_inches='tight')
        plt.close(fig)


def fig_taxonomy_breakdown(taxonomy: pd.DataFrame, output_dir: str):
    """Figure 3: Failure taxonomy breakdown - horizontal bar chart."""
    if 'Category' not in taxonomy.columns:
        print("  [SKIP] Figure 3: No Category column in taxonomy.")
        return

    counts = taxonomy['Category'].value_counts()
    # Merge small categories
    threshold = 2
    main = counts[counts >= threshold]
    other_count = counts[counts < threshold].sum()
    if other_count > 0:
        main = pd.concat([main, pd.Series({'Other': other_count})])

    fig, ax = plt.subplots(figsize=(10, max(6, len(main) * 0.5)))
    bars = ax.barh(range(len(main)), main.values, color='#2c3e50', alpha=0.8)
    ax.set_yticks(range(len(main)))
    ax.set_yticklabels(main.index, fontsize=10)
    ax.set_xlabel('Count', fontsize=12)
    ax.set_title('Failure Taxonomy: Category Frequency', fontsize=14, fontweight='bold')
    ax.invert_yaxis()

    for bar, val in zip(bars, main.values):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va='center', fontsize=10)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'fig3_taxonomy_breakdown.pdf'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(output_dir, 'fig3_taxonomy_breakdown.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)


def fig_strict_vs_adjusted(df: pd.DataFrame, taxonomy: pd.DataFrame, output_dir: str):
    """Figure 4: Strict vs adjusted success - grouped bar chart."""
    if 'secondary_label' not in taxonomy.columns:
        print("  [SKIP] Figure 4: No secondary_label column. Generating strict-only bar chart.")
        # Compute rates + CIs
        cond_stats = {}
        for cond in CONDITIONS:
            sub = df[df['condition'] == cond]
            if sub.empty:
                continue
            mean, lo, hi = proportion_ci(int(sub['success'].sum()), len(sub))
            cond_stats[cond] = {'mean': mean * 100, 'lo': lo * 100, 'hi': hi * 100}

        # McNemar p-values vs Vanilla for significance stars
        sig_stars = {}
        van_data = df[df['condition'] == 'Vanilla']
        for cond in CONDITIONS:
            if cond == 'Vanilla':
                continue
            result = mcnemar_test(df, 'Vanilla', cond)
            p = result['p_value']
            sig_stars[cond] = '***' if p < 0.001 else ('**' if p < 0.01 else ('*' if p < 0.05 else 'ns'))

        import matplotlib as mpl
        CONDITION_MARKERS = {'Vanilla': 's', 'Vanilla+ASI': 'D', 'MCP': '^', 'MCP+ASI': 'o'}
        rc_overrides = {
            'font.family': 'serif',
            'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
        }
        with mpl.rc_context(rc_overrides):
            fig, ax = plt.subplots(figsize=(7, 4.5))

            x = np.arange(len(CONDITIONS))
            vanilla_rate = cond_stats.get('Vanilla', {}).get('mean', 0)
            y_lo = min(s['lo'] for s in cond_stats.values()) - 2
            y_hi = max(s['hi'] for s in cond_stats.values()) + 10

            # Background group shading
            ax.axvspan(-0.5, 1.5, alpha=0.04, color='#888888', zorder=0)
            ax.axvspan(1.5, 4.3, alpha=0.06, color='#28a745', zorder=0)
            ax.text(0.5, y_hi - 0.8, 'Browser-based', ha='center', va='top',
                    fontsize=12, color='#666666', style='italic')
            ax.text(2.5, y_hi - 0.8, 'MCP-enhanced', ha='center', va='top',
                    fontsize=12, color='#1a7a2e', style='italic')

            # Vanilla baseline reference
            ax.axhline(vanilla_rate, color='#999999', linewidth=1.2,
                       linestyle='--', alpha=0.7, zorder=2)

            # Point plot: dots with 95% CI error bars (truncated y-axis is valid for position encodings)
            for i, cond in enumerate(CONDITIONS):
                if cond not in cond_stats:
                    continue
                s = cond_stats[cond]
                ax.errorbar(
                    i, s['mean'],
                    yerr=[[s['mean'] - s['lo']], [s['hi'] - s['mean']]],
                    fmt=CONDITION_MARKERS[cond], markersize=13, capsize=6, capthick=2,
                    color=CONDITION_COLORS[cond], linewidth=2,
                    markeredgecolor='white', markeredgewidth=1.5, zorder=5,
                )

            # Rate labels above each point only
            for i, cond in enumerate(CONDITIONS):
                if cond not in cond_stats:
                    continue
                s = cond_stats[cond]
                ax.text(i, s['hi'] + 0.6, f'{s["mean"]:.1f}%',
                        ha='center', va='bottom', fontsize=12, fontweight='bold')

            ax.set_xlim(-0.6, 3.6)
            ax.set_ylim(y_lo, y_hi)
            ax.set_xticks(x)
            ax.set_xticklabels(CONDITIONS, fontsize=14)
            ax.set_ylabel('Success Rate (%)', fontsize=14)
            ax.tick_params(labelsize=12)
            ax.grid(True, alpha=0.2, axis='y', linestyle='--', zorder=0)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

            fig.tight_layout()
            fig.savefig(os.path.join(output_dir, 'fig4_success_rates.pdf'), bbox_inches='tight')
            plt.close(fig)
        return

    functional_tasks = set(
        taxonomy[taxonomy['secondary_label'] == 'functional_success']['task_id'].values
    )

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = np.arange(len(CONDITIONS))
    width = 0.35

    strict_rates = []
    adjusted_rates = []
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            strict_rates.append(0)
            adjusted_rates.append(0)
            continue
        strict = sub['success'].mean() * 100
        adjusted_vals = [
            1 if row['success'] or row['task_id'] in functional_tasks else 0
            for _, row in sub.iterrows()
        ]
        adjusted = np.mean(adjusted_vals) * 100
        strict_rates.append(strict)
        adjusted_rates.append(adjusted)

    bars1 = ax.bar(x - width / 2, strict_rates, width, label='Strict', alpha=0.85,
                   color=[CONDITION_COLORS[c] for c in CONDITIONS])
    bars2 = ax.bar(x + width / 2, adjusted_rates, width, label='Adjusted (+ functional)',
                   alpha=0.5, color=[CONDITION_COLORS[c] for c in CONDITIONS],
                   edgecolor=[CONDITION_COLORS[c] for c in CONDITIONS], linewidth=2)

    ax.set_xticks(x)
    ax.set_xticklabels(CONDITIONS, fontsize=14)
    ax.set_ylabel('Success Rate (%)', fontsize=14)
    ax.set_title('Strict vs Adjusted Success Rate', fontsize=14, fontweight='bold')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3, axis='y')

    for bar, rate in zip(bars1, strict_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f'{rate:.1f}%', ha='center', va='bottom', fontsize=12)
    for bar, rate in zip(bars2, adjusted_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f'{rate:.1f}%', ha='center', va='bottom', fontsize=12)

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'fig4_strict_vs_adjusted.pdf'), dpi=300)
    fig.savefig(os.path.join(output_dir, 'fig4_strict_vs_adjusted.png'), dpi=300)
    plt.close(fig)


def fig_step_distribution(df: pd.DataFrame, output_dir: str):
    """Figure 5: Step count distribution by condition - violin/box plot."""
    import matplotlib as mpl
    import seaborn as sns

    plot_df = df[df['condition'].isin(CONDITIONS)][['condition', 'steps']].copy()

    rc_overrides = {
        'font.family': 'serif',
        'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
        'text.usetex': False,   # prevents + in label names being parsed as math
    }
    with mpl.rc_context(rc_overrides):
        fig, ax = plt.subplots(figsize=(7, 4.5))

        sns.violinplot(
            data=plot_df, x='condition', y='steps',
            order=CONDITIONS,
            hue='condition', hue_order=CONDITIONS,
            palette=CONDITION_COLORS, legend=False,
            inner='box', cut=0, linewidth=1.2, ax=ax,
        )
        for art in ax.collections:
            art.set_alpha(0.6)

        ax.set_xlabel('')
        ax.set_ylabel('Steps per Task', fontsize=14)
        ax.tick_params(axis='x', labelsize=14)
        ax.tick_params(axis='y', labelsize=12)
        ax.grid(True, alpha=0.25, axis='y', linestyle='--')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, 'fig5_step_distribution.pdf'), bbox_inches='tight')
        plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 6: Money Math
# ---------------------------------------------------------------------------

def fig_money_math(df: pd.DataFrame, output_dir: str,
                   price_per_1m: float = 3.00,
                   model_name: str = 'claude-sonnet-4-6'):
    """Figure 6: Cost vs success trade-off across all 4 conditions.

    Shows cost per 1,000 tasks and success count per 1,000 tasks side-by-side,
    with the MCP -> MCP+ASI trade-off highlighted.
    """
    TASKS = 1_000

    # Gather per-condition stats
    cond_data = {}
    for cond in CONDITIONS:
        sub = df[df['condition'] == cond]
        if sub.empty:
            continue
        mean_tokens = sub['total_input_tokens'].mean()
        cost_per_task = mean_tokens / 1_000_000 * price_per_1m
        cost_per_1k = cost_per_task * TASKS
        success_per_1k = sub['success'].mean() * TASKS
        cond_data[cond] = {
            'mean_tokens': mean_tokens,
            'cost_per_1k': cost_per_1k,
            'success_per_1k': success_per_1k,
        }

    conds = [c for c in CONDITIONS if c in cond_data]
    costs = [cond_data[c]['cost_per_1k'] for c in conds]
    successes = [cond_data[c]['success_per_1k'] for c in conds]
    colors = [CONDITION_COLORS[c] for c in conds]

    fig, (ax_cost, ax_succ) = plt.subplots(1, 2, figsize=(12, 6))
    fig.suptitle(
        f'Cost–Success Trade-off per 1,000 Tasks\n'
        f'Model: {model_name}  |  Pricing: ${price_per_1m:.2f} / 1M input tokens',
        fontsize=14, fontweight='bold', y=1.01,
    )

    x = np.arange(len(conds))
    bar_w = 0.55

    # --- Left panel: Cost ---
    bars_cost = ax_cost.bar(x, costs, width=bar_w, color=colors, alpha=0.85,
                            edgecolor='white', linewidth=1.2)
    ax_cost.set_xticks(x)
    ax_cost.set_xticklabels(conds, fontsize=11)
    ax_cost.set_ylabel('USD per 1,000 Tasks', fontsize=12)
    ax_cost.set_title('API Cost', fontsize=13, fontweight='bold')
    ax_cost.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'${v:,.0f}'))
    ax_cost.grid(True, alpha=0.25, axis='y', linestyle='--')

    for bar, val in zip(bars_cost, costs):
        ax_cost.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 8,
                     f'${val:,.0f}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Highlight savings: MCP -> MCP+ASI
    if 'MCP' in cond_data and 'MCP+ASI' in cond_data:
        savings = cond_data['MCP']['cost_per_1k'] - cond_data['MCP+ASI']['cost_per_1k']
        mcp_idx = conds.index('MCP')
        asi_idx = conds.index('MCP+ASI')
        y_bracket = max(costs) * 1.08
        ax_cost.annotate(
            '', xy=(asi_idx, y_bracket), xytext=(mcp_idx, y_bracket),
            arrowprops=dict(arrowstyle='<->', color='#333333', lw=1.8),
        )
        ax_cost.text((mcp_idx + asi_idx) / 2, y_bracket * 1.02,
                     f'Save ${savings:,.0f}', ha='center', va='bottom',
                     fontsize=11, fontweight='bold', color='#333333')

    # --- Right panel: Successes per 1k ---
    bars_succ = ax_succ.bar(x, successes, width=bar_w, color=colors, alpha=0.85,
                             edgecolor='white', linewidth=1.2)
    ax_succ.set_xticks(x)
    ax_succ.set_xticklabels(conds, fontsize=11)
    ax_succ.set_ylabel('Successful Tasks out of 1,000', fontsize=12)
    ax_succ.set_title('Task Success', fontsize=13, fontweight='bold')
    ax_succ.grid(True, alpha=0.25, axis='y', linestyle='--')
    # Y range: start below minimum so differences are visible
    y_min = min(successes) * 0.88
    y_max = max(successes) * 1.12
    ax_succ.set_ylim(y_min, y_max)

    for bar, val in zip(bars_succ, successes):
        ax_succ.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + (y_max - y_min) * 0.01,
                     f'{val:.0f} tasks', ha='center', va='bottom', fontsize=11, fontweight='bold')

    fig.tight_layout()
    fig.savefig(os.path.join(output_dir, 'fig6_money_math.pdf'), dpi=300, bbox_inches='tight')
    fig.savefig(os.path.join(output_dir, 'fig6_money_math.png'), dpi=300, bbox_inches='tight')
    plt.close(fig)


# ---------------------------------------------------------------------------
# Figure 7: SOTA Progression Infographic
# ---------------------------------------------------------------------------

def fig_sota_progression(output_dir: str):
    """Figure 7: Chronological SOTA progression on WebArena Shopping.

    Compares prior-art results (Inducing Programmatic Skills paper) against
    thesis DOM and MCP conditions.
    """
    import matplotlib as mpl

    # Prior art bars use desaturated grays; thesis bars use the established palette
    BARS = [
        ('Vanilla',     32.6, '#c0c0c0'),                    # Wang et al. — light gray
        ('Vanilla+ASI', 40.1, '#888888'),                    # Wang et al. — mid gray
        ('Vanilla',     51.3, CONDITION_COLORS['Vanilla']),
        ('Vanilla+ASI', 54.0, CONDITION_COLORS['Vanilla+ASI']),
        ('MCP',         60.4, CONDITION_COLORS['MCP']),
        ('MCP+ASI',     56.1, CONDITION_COLORS['MCP+ASI']),
    ]

    BAR_W = 0.70
    LEFTS = [0.0, 0.85, 2.35, 3.20, 4.70, 5.55]
    CENTERS = [l + BAR_W / 2 for l in LEFTS]
    group_centers = [
        (CENTERS[0] + CENTERS[1]) / 2,
        (CENTERS[2] + CENTERS[3]) / 2,
        (CENTERS[4] + CENTERS[5]) / 2,
    ]
    sep_x = [
        (LEFTS[1] + BAR_W + LEFTS[2]) / 2,
        (LEFTS[3] + BAR_W + LEFTS[4]) / 2,
    ]

    # Group headers: (title line, subtitle/model line)
    GROUP_HEADERS = [
        ('Wang et al. (2025)',  'Claude 3.5 Sonnet'),
        ('DOM Regime',          'Claude 4.6 Sonnet'),
        ('MCP Regime',          'Claude 4.6 Sonnet'),
    ]

    rc_overrides = {
        'font.family': 'serif',
        'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
        'text.usetex': False,
    }
    with mpl.rc_context(rc_overrides):
        fig, ax = plt.subplots(figsize=(7, 4.5))

        # Bars + rate labels
        for left, center, (label, rate, color) in zip(LEFTS, CENTERS, BARS):
            ax.bar(left, rate, width=BAR_W, color=color, alpha=0.92,
                   edgecolor='white', linewidth=1.8, zorder=3, align='edge')
            ax.text(center, rate + 0.8, f'{rate}%',
                    ha='center', va='bottom', fontsize=12, fontweight='bold', color='#111111',
                    zorder=10)

        # Axes
        ax.set_ylim(0, 96)
        ax.set_xlim(-0.5, LEFTS[-1] + BAR_W + 0.6)
        ax.set_yticks(range(0, 71, 10))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f'{v:.0f}%'))
        ax.set_ylabel('Task Success Rate (%)', fontsize=14, labelpad=10)
        ax.tick_params(axis='y', labelsize=12)
        ax.set_xticks(CENTERS)
        ax.set_xticklabels([b[0] for b in BARS], fontsize=12, ha='center')
        ax.tick_params(axis='x', length=0, pad=6)
        ax.grid(True, alpha=0.25, axis='y', linestyle='--', zorder=0)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_color('#cccccc')

        # Group separator lines
        for xv in sep_x:
            ax.axvline(xv, ymin=0, ymax=1, color='#cccccc', linewidth=1.2, zorder=1)

        # Clean group headers — plain text, no boxes
        for gc, (title, subtitle) in zip(group_centers, GROUP_HEADERS):
            ax.text(gc, 94, title,
                    ha='center', va='top', fontsize=12, fontweight='bold', color='#333333')
            ax.text(gc, 89.5, subtitle,
                    ha='center', va='top', fontsize=11, color='#777777', style='italic')

        fig.tight_layout()
        fig.savefig(os.path.join(output_dir, 'fig7_sota_progression.pdf'), bbox_inches='tight')
        plt.close(fig)


# ---------------------------------------------------------------------------
# Printing Helpers
# ---------------------------------------------------------------------------

def print_table(title: str, tbl: pd.DataFrame, number: int = None):
    prefix = f"Table {number}: " if number else ""
    print(f"\n{'='*80}")
    print(f"{prefix}{title}")
    print('='*80)
    if tbl.empty:
        print("  (no data)")
    else:
        # Drop internal columns starting with _
        display_cols = [c for c in tbl.columns if not c.startswith('_')]
        print(tbl[display_cols].to_string(index=False))


def print_stat_results(results: dict):
    print(f"\n{'='*80}")
    print("Statistical Tests")
    print('='*80)

    print("\n--- McNemar's Test (Success Rate, paired binary) ---")
    for r in results['mcnemar']:
        sig = '*' if r['p_value'] < ALPHA else ''
        print(f"  {r['comparison']:30s}  chi2={r['statistic']:.2f}  p={r['p_value']:.4f} {sig}  "
              f"n_discordant={r.get('n_discordant', 'N/A')}")

    print("\n--- Wilcoxon Signed-Rank (Input Tokens, paired continuous) ---")
    for r in results['wilcoxon_tokens']:
        if np.isnan(r.get('p_value', np.nan)):
            print(f"  {r['comparison']:30s}  {r.get('note', '')}")
            continue
        sig = '*' if r['p_value'] < ALPHA else ''
        print(f"  {r['comparison']:30s}  W={r['statistic']:.0f}  p={r['p_value']:.4e} {sig}  "
              f"mean_diff={r['mean_diff']:+,.0f}  median_diff={r['median_diff']:+,.0f}")

    print("\n--- Wilcoxon Signed-Rank (Steps, paired continuous) ---")
    for r in results['wilcoxon_steps']:
        if np.isnan(r.get('p_value', np.nan)):
            print(f"  {r['comparison']:30s}  {r.get('note', '')}")
            continue
        sig = '*' if r['p_value'] < ALPHA else ''
        print(f"  {r['comparison']:30s}  W={r['statistic']:.0f}  p={r['p_value']:.4e} {sig}  "
              f"mean_diff={r['mean_diff']:+.2f}  median_diff={r['median_diff']:+.1f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Thesis analysis script')
    parser.add_argument('--cohort', default='results/final/cohort_25',
                        help='Path to the main cohort directory')
    parser.add_argument('--pre-es', default='results/final/cohort_23',
                        help='Path to pre-ES cohort (for semantic comparison)')
    parser.add_argument('--taxonomy', default='thesis_taxonomy.csv',
                        help='Path to thesis_taxonomy.csv')
    parser.add_argument('--output-dir', default='thesis_outputs',
                        help='Directory for output figures and CSVs')
    args = parser.parse_args()

    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"Thesis Analysis Script")
    print(f"Cohort:    {args.cohort}")
    print(f"Pre-ES:    {args.pre_es}")
    print(f"Taxonomy:  {args.taxonomy}")
    print(f"Output:    {output_dir}")

    # --- Load data ---
    print("\nLoading data...")
    data = load_cohort(args.cohort)
    for cond, records in data.items():
        print(f"  {cond}: {len(records)} tasks")
    df = records_to_df(data)

    pre_es_data = load_cohort(args.pre_es)
    pre_es_df = records_to_df(pre_es_data) if pre_es_data else pd.DataFrame()
    if not pre_es_df.empty:
        for cond, records in pre_es_data.items():
            print(f"  Pre-ES {cond}: {len(records)} tasks")

    taxonomy = load_taxonomy(args.taxonomy) if os.path.exists(args.taxonomy) else pd.DataFrame()
    if not taxonomy.empty:
        print(f"  Taxonomy: {len(taxonomy)} entries")

    # --- Tables ---
    t1 = table_success_rate(df)
    print_table("Success Rate across Conditions (187 tasks, 95% CI, normal approx)", t1, 1)
    t1.to_csv(os.path.join(output_dir, 'table1_success_rate.csv'), index=False)

    t2 = table_adjusted_success(df, taxonomy)
    if not t2.empty:
        print_table("Adjusted Success Rate (Strict + Functional)", t2, 2)
        t2.to_csv(os.path.join(output_dir, 'table2_adjusted_success.csv'), index=False)

    t3 = table_step_count(df)
    print_table("Step Count across Conditions", t3, 3)
    t3.to_csv(os.path.join(output_dir, 'table3_step_count.csv'), index=False)

    t4 = table_token_usage(df)
    print_table("Token Usage across Conditions", t4, 4)
    t4.to_csv(os.path.join(output_dir, 'table4_token_usage.csv'), index=False)

    t5 = table_per_task(df)
    print_table("Per-Task Paired Comparison (first 10 rows shown)", t5.head(10), 5)
    t5.to_csv(os.path.join(output_dir, 'table5_per_task.csv'), index=False)
    print(f"  Full table saved: {output_dir}/table5_per_task.csv ({len(t5)} rows)")

    t6 = table_taxonomy_frequency(taxonomy)
    if not t6.empty:
        print_table("Failure Taxonomy Frequency", t6, 6)
        t6.to_csv(os.path.join(output_dir, 'table6_taxonomy_frequency.csv'), index=False)

    t7 = table_semantic_impact(df, pre_es_df, taxonomy)
    if not t7.empty:
        print_table("Semantic Search Impact (Pre-ES vs Post-ES)", t7, 7)
        t7.to_csv(os.path.join(output_dir, 'table7_semantic_impact.csv'), index=False)

    t8 = table_asi_interaction(df)
    print_table("ASI Interaction Effect (2x2)", t8, 8)
    t8.to_csv(os.path.join(output_dir, 'table8_asi_interaction.csv'), index=False)

    # --- Statistical Tests ---
    stat_results = run_all_statistical_tests(df)
    print_stat_results(stat_results)

    # Save stat results as JSON
    with open(os.path.join(output_dir, 'statistical_tests.json'), 'w') as f:
        json.dump(stat_results, f, indent=2, default=str)

    # --- Additional Analyses ---
    print(f"\n{'='*80}")
    print("Additional Analyses")
    print('='*80)

    wlt = analysis_win_loss_tie(df)
    print("\n--- Win/Loss/Tie (Success) ---")
    print(wlt.to_string(index=False))
    wlt.to_csv(os.path.join(output_dir, 'win_loss_tie.csv'), index=False)

    cps = analysis_cost_per_success(df)
    print("\n--- Cost per Success (Tokens) ---")
    print(cps.to_string(index=False))
    cps.to_csv(os.path.join(output_dir, 'cost_per_success.csv'), index=False)

    td = analysis_task_difficulty(df)
    print("\n--- Task Difficulty ---")
    for cond in CONDITIONS:
        if cond in td:
            d = td[cond]
            print(f"  {cond:15s}  one-shot: {d['one_shot_count']:3d} ({d['one_shot_pct']:.1%})  "
                  f"truncated: {d['truncated_count']:3d} ({d['truncated_pct']:.1%})  "
                  f"mean_steps: {d['mean_steps']:.2f}")
    s = td['_summary']
    print(f"\n  Ceiling tasks (all 4 pass):  {s['ceiling_tasks']} ({s['ceiling_pct']:.1%})")
    print(f"  Floor tasks (all 4 fail):    {s['floor_tasks']} ({s['floor_pct']:.1%})")
    print(f"  Differentiating tasks:       {s['differentiating_tasks']}")

    with open(os.path.join(output_dir, 'task_difficulty.json'), 'w') as f:
        json.dump(td, f, indent=2, default=str)

    # --- Figures ---
    print(f"\n{'='*80}")
    print("Generating Figures")
    print('='*80)

    fig_efficiency_frontier(df, taxonomy, output_dir)
    print("  Figure 1: Efficiency frontier (Hero) -> fig1_efficiency_frontier.pdf")

    fig_token_reduction(df, output_dir)
    print("  Figure 2: Token reduction    -> fig2_token_reduction.pdf")

    fig_taxonomy_breakdown(taxonomy, output_dir)
    print("  Figure 3: Taxonomy breakdown -> fig3_taxonomy_breakdown.pdf")

    fig_strict_vs_adjusted(df, taxonomy, output_dir)
    print("  Figure 4: Strict vs adjusted -> fig4_*.pdf")

    fig_step_distribution(df, output_dir)
    print("  Figure 5: Step distribution  -> fig5_step_distribution.pdf")

    fig_money_math(df, output_dir)
    print("  Figure 6: Money math         -> fig6_money_math.pdf")

    fig_sota_progression(output_dir)
    print("  Figure 7: SOTA progression   -> fig7_sota_progression.pdf")

    print(f"\nAll outputs saved to: {output_dir}/")
    print("Done.")


if __name__ == '__main__':
    main()

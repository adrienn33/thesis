#!/usr/bin/env python3
"""
Research Dashboard Generator for Agent Skill Induction (ASI) Experiments
Creates a professional HTML dashboard with KPIs for academic publication
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

def collect_experiment_data(results_dir="results"):
    """Collect all research metrics from experiment directories"""
    experiments = []
    results_path = Path(results_dir)
    
    for exp_dir in results_path.iterdir():
        if exp_dir.is_dir() and exp_dir.name.startswith("webarena."):
            metrics_file = exp_dir / "research_metrics.json"
            if metrics_file.exists():
                try:
                    with open(metrics_file) as f:
                        data = json.load(f)
                    experiments.append(data)
                except Exception as e:
                    print(f"Warning: Could not load {metrics_file}: {e}")
    
    return experiments

def collect_cohort_data(cohort_path):
    """Collect experiment data from a specific cohort directory"""
    experiments = []
    cohort_dir = Path(cohort_path)
    
    if not cohort_dir.exists():
        return experiments
    
    # Check for organized structure (Vanilla/Vanilla+ASI/MCP/MCP+ASI subdirs)
    condition_dirs = ['Vanilla', 'Vanilla+ASI', 'MCP', 'MCP+ASI']
    has_organized_structure = any((cohort_dir / d).exists() for d in condition_dirs)
    
    if has_organized_structure:
        # Organized structure with 4 conditions
        for condition_dir in condition_dirs:
            cond_path = cohort_dir / condition_dir
            if cond_path.exists():
                for metrics_file in cond_path.glob("*_research_metrics.json"):
                    try:
                        with open(metrics_file) as f:
                            data = json.load(f)
                        experiments.append(data)
                    except Exception as e:
                        print(f"Warning: Could not load {metrics_file}: {e}")
    else:
        # Legacy flat structure
        for metrics_file in cohort_dir.glob("*_research_metrics.json"):
            try:
                with open(metrics_file) as f:
                    data = json.load(f)
                experiments.append(data)
            except Exception as e:
                print(f"Warning: Could not load {metrics_file}: {e}")
    
    return experiments

def analyze_experiments(experiments):
    """Analyze experiments and calculate KPIs"""
    
    # Group experiments by configuration (2x2 factorial design)
    groups = {
        'Vanilla': [],
        'Vanilla+ASI': [],
        'MCP': [],
        'MCP+ASI': []
    }
    
    for exp in experiments:
        config = exp.get('configuration', {})
        name = config.get('name', 'Unknown')
        
        # Normalize config names (2x2 factorial design only)
        if name in ['Vanilla', 'vanilla']:
            groups['Vanilla'].append(exp)
        elif name in ['Vanilla+ASI', 'vanilla+asi']:
            groups['Vanilla+ASI'].append(exp)
        elif name in ['MCP', 'mcp']:
            groups['MCP'].append(exp)
        elif name in ['MCP+ASI', 'mcp+asi']:
            groups['MCP+ASI'].append(exp)
    
    # Calculate KPIs for each group
    results = {}
    
    for group_name, group_exps in groups.items():
        if not group_exps:
            results[group_name] = None
            continue
            
        # Core success metrics
        successes = [exp['task_execution']['success'] for exp in group_exps]
        success_rate = sum(successes) / len(successes) if successes else 0
        
        # Performance metrics
        steps = [exp['task_execution']['steps'] for exp in group_exps]
        agent_times = [exp['task_execution']['agent_elapsed_time'] for exp in group_exps]
        total_times = [exp['task_execution']['elapsed_time'] for exp in group_exps]
        
        # Skill metrics (for ASI experiments)
        runs_with_reuse = 0
        skills_reused = []
        skills_induced = []
        
        for exp in group_exps:
            reused_count = exp.get('skills_reused_count', 0)
            if reused_count > 0:
                runs_with_reuse += 1
                
            skills_reused.append(reused_count)
            skills_induced.append(exp.get('skills_induced_count', 0))
        
        # Token usage
        token_usage = [exp.get('token_usage', {}).get('total_input_tokens', 0) for exp in group_exps]
        
        # Calculate percentage of runs that had any skill reuse
        skill_reuse_run_pct = (runs_with_reuse / len(group_exps)) if len(group_exps) > 0 else 0
        
        results[group_name] = {
            'count': len(group_exps),
            'success_rate': success_rate,
            'avg_steps': statistics.mean(steps) if steps else 0,
            'std_steps': statistics.stdev(steps) if len(steps) > 1 else 0,
            'avg_agent_time': statistics.mean(agent_times) if agent_times else 0,
            'avg_total_time': statistics.mean(total_times) if total_times else 0,
            'skill_reuse_run_pct': skill_reuse_run_pct,
            'avg_skills_reused': statistics.mean(skills_reused) if skills_reused else 0,
            'avg_skills_induced': statistics.mean(skills_induced) if skills_induced else 0,
            'avg_tokens': statistics.mean(token_usage) if token_usage else 0
        }
    
    return results

def calculate_statistical_significance(results):
    """Calculate effect sizes and statistical indicators"""
    vanilla = results.get('Vanilla')
    vanilla_asi = results.get('Vanilla+ASI')
    mcp = results.get('MCP') 
    mcp_asi = results.get('MCP+ASI')
    
    comparisons = {}
    
    if vanilla and mcp:
        # MCP vs Vanilla
        success_lift = ((mcp['success_rate'] - vanilla['success_rate']) / vanilla['success_rate'] * 100) if vanilla['success_rate'] > 0 else 0
        step_efficiency = ((vanilla['avg_steps'] - mcp['avg_steps']) / vanilla['avg_steps'] * 100) if vanilla['avg_steps'] > 0 else 0
        
        comparisons['MCP_vs_Vanilla'] = {
            'success_lift_pct': success_lift,
            'step_efficiency_pct': step_efficiency,
            'sample_size_adequate': mcp['count'] >= 10 and vanilla['count'] >= 10
        }
    
    if vanilla and vanilla_asi:
        # Vanilla+ASI vs Vanilla (pure ASI effect)  
        success_lift = ((vanilla_asi['success_rate'] - vanilla['success_rate']) / vanilla['success_rate'] * 100) if vanilla['success_rate'] > 0 else 0
        step_efficiency = ((vanilla['avg_steps'] - vanilla_asi['avg_steps']) / vanilla['avg_steps'] * 100) if vanilla['avg_steps'] > 0 else 0
        
        comparisons['VanillaASI_vs_Vanilla'] = {
            'success_lift_pct': success_lift,
            'step_efficiency_pct': step_efficiency,
            'skill_reuse_rate': vanilla_asi['skill_reuse_run_pct'],
            'sample_size_adequate': vanilla_asi['count'] >= 10 and vanilla['count'] >= 10
        }
    
    if mcp and mcp_asi:
        # MCP+ASI vs MCP (ASI effect with MCP tools)
        success_lift = ((mcp_asi['success_rate'] - mcp['success_rate']) / mcp['success_rate'] * 100) if mcp['success_rate'] > 0 else 0
        step_efficiency = ((mcp['avg_steps'] - mcp_asi['avg_steps']) / mcp['avg_steps'] * 100) if mcp['avg_steps'] > 0 else 0
        
        comparisons['MCPASI_vs_MCP'] = {
            'success_lift_pct': success_lift, 
            'step_efficiency_pct': step_efficiency,
            'skill_induction_effect': mcp_asi['avg_skills_induced'],
            'sample_size_adequate': mcp_asi['count'] >= 10 and mcp['count'] >= 10
        }
    
    if vanilla and mcp_asi:
        # MCP+ASI vs Vanilla (full system effect)
        success_lift = ((mcp_asi['success_rate'] - vanilla['success_rate']) / vanilla['success_rate'] * 100) if vanilla['success_rate'] > 0 else 0
        step_efficiency = ((vanilla['avg_steps'] - mcp_asi['avg_steps']) / vanilla['avg_steps'] * 100) if vanilla['avg_steps'] > 0 else 0
        
        comparisons['MCPASI_vs_Vanilla'] = {
            'success_lift_pct': success_lift,
            'step_efficiency_pct': step_efficiency,
            'skill_reuse_rate': mcp_asi['skill_reuse_run_pct'],
            'sample_size_adequate': mcp_asi['count'] >= 10 and vanilla['count'] >= 10
        }
    
    return comparisons

def generate_html_dashboard(results, comparisons, total_experiments, cohort_name=None):
    """Generate professional HTML dashboard"""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title_suffix = f" - {cohort_name}" if cohort_name else ""
    data_source = f"{cohort_name}" if cohort_name else "All Experiments"
    
    # Determine research status
    def get_status_badge(comparison_key, metric):
        if comparison_key not in comparisons:
            return '<span class="badge insufficient">Insufficient Data</span>'
        
        comp = comparisons[comparison_key]
        if not comp['sample_size_adequate']:
            return '<span class="badge insufficient">Small Sample</span>'
            
        value = comp.get(metric, 0)
        if metric.endswith('_pct'):
            if value > 10:
                return '<span class="badge positive">Significant Improvement</span>'
            elif value > 0:
                return '<span class="badge neutral">Slight Improvement</span>'
            else:
                return '<span class="badge negative">No Improvement</span>'
        else:
            if value > 0.1:  # 10% skill reuse rate
                return '<span class="badge positive">Active Skill Reuse</span>'
            else:
                return '<span class="badge negative">Limited Skill Reuse</span>'

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Agent Skill Induction Research Dashboard</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f8f9fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.2em;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }}
        .meta-info {{
            display: flex;
            justify-content: space-between;
            background: #ecf0f1;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 20px;
            margin-bottom: 30px;
            max-width: 800px;
            margin-left: auto;
            margin-right: auto;
        }}
        @media (max-width: 768px) {{
            .kpi-grid {{
                grid-template-columns: 1fr;
                max-width: 400px;
            }}
        }}
        .kpi-card {{
            background: #ffffff;
            border: 1px solid #e9ecef;
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            position: relative;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            transition: all 0.2s ease;
        }}
        .kpi-card:hover {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transform: translateY(-1px);
        }}
        .kpi-card.vanilla {{
            border-left: 4px solid #6c757d;
        }}
        .kpi-card.vanilla-asi {{
            border-left: 4px solid #17a2b8;
        }}
        .kpi-card.mcp {{
            border-left: 4px solid #28a745;
        }}
        .kpi-card.mcp-asi {{
            border-left: 4px solid #007bff;
        }}
        .kpi-card h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 1.1em;
        }}
        .kpi-value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .kpi-value.success {{ color: #27ae60; }}
        .kpi-value.warning {{ color: #f39c12; }}
        .kpi-value.danger {{ color: #e74c3c; }}
        .kpi-label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        .comparison-table th {{
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .comparison-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        .comparison-table tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge.positive {{ background: #d4edda; color: #155724; }}
        .badge.negative {{ background: #f8d7da; color: #721c24; }}
        .badge.neutral {{ background: #fff3cd; color: #856404; }}
        .badge.insufficient {{ background: #e9ecef; color: #6c757d; }}
        .hypothesis-section {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 8px;
            margin: 25px 0;
        }}
        .hypothesis-section h3 {{
            color: #2c3e50;
            margin-bottom: 20px;
        }}
        .metric-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 5px;
        }}
        .footnote {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e9ecef;
            color: #6c757d;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Agent Skill Induction Research Dashboard{title_suffix}</h1>
        <div class="subtitle">WebArena E-commerce Task Performance Analysis</div>
        
        <div class="meta-info">
            <div><strong>Analysis Date:</strong> {timestamp}</div>
            <div><strong>Data Source:</strong> {data_source}</div>
            <div><strong>Total Experiments:</strong> {total_experiments}</div>
            <div><strong>Task Domain:</strong> Shopping (Magento)</div>
        </div>

        <!-- Core KPIs -->
        <div class="kpi-grid">"""
    
    # Vanilla card
    vanilla_data = results.get('Vanilla')
    vanilla_success = vanilla_data['success_rate']*100 if vanilla_data else 0
    vanilla_count = vanilla_data['count'] if vanilla_data else 0
    vanilla_steps = vanilla_data['avg_steps'] if vanilla_data else 0
    vanilla_class = 'danger' if not vanilla_data else ('success' if vanilla_data['success_rate'] > 0.2 else 'warning')
    
    html += f"""
            <div class="kpi-card vanilla">
                <h3>Vanilla (Control)</h3>
                <div class="kpi-value {vanilla_class}">{vanilla_success:.1f}%</div>
                <div class="kpi-label">Task Success Rate</div>
                <div style="margin-top: 10px;">
                    <small>n = {vanilla_count} | Avg Steps: {vanilla_steps:.1f}</small>
                </div>
            </div>"""
    
    # MCP card  
    mcp_data = results.get('MCP')
    mcp_success = mcp_data['success_rate']*100 if mcp_data else 0
    mcp_count = mcp_data['count'] if mcp_data else 0
    mcp_steps = mcp_data['avg_steps'] if mcp_data else 0
    mcp_class = 'danger' if not mcp_data else ('success' if mcp_data['success_rate'] > 0.2 else 'warning')
    
    html += f"""
            <div class="kpi-card mcp">
                <h3>MCP Tools Only</h3>
                <div class="kpi-value {mcp_class}">{mcp_success:.1f}%</div>
                <div class="kpi-label">Task Success Rate</div>
                <div style="margin-top: 10px;">
                    <small>n = {mcp_count} | Avg Steps: {mcp_steps:.1f}</small>
                </div>
            </div>"""
    
    # Vanilla+ASI card
    vanilla_asi_data = results.get('Vanilla+ASI')
    vanilla_asi_success = vanilla_asi_data['success_rate']*100 if vanilla_asi_data else 0
    vanilla_asi_count = vanilla_asi_data['count'] if vanilla_asi_data else 0
    vanilla_asi_steps = vanilla_asi_data['avg_steps'] if vanilla_asi_data else 0
    vanilla_asi_reuse = vanilla_asi_data['skill_reuse_run_pct']*100 if vanilla_asi_data else 0
    vanilla_asi_class = 'danger' if not vanilla_asi_data else ('success' if vanilla_asi_data['success_rate'] > 0.2 else 'warning')
    
    html += f"""
            <div class="kpi-card vanilla-asi">
                <h3>Vanilla + ASI</h3>
                <div class="kpi-value {vanilla_asi_class}">{vanilla_asi_success:.1f}%</div>
                <div class="kpi-label">Task Success Rate</div>
                <div style="margin-top: 10px;">
                    <small>n = {vanilla_asi_count} | Avg Steps: {vanilla_asi_steps:.1f} | Skill Reuse: {vanilla_asi_reuse:.1f}%</small>
                </div>
            </div>"""
    
    # MCP+ASI card
    mcp_asi_data = results.get('MCP+ASI')
    mcp_asi_success = mcp_asi_data['success_rate']*100 if mcp_asi_data else 0
    mcp_asi_count = mcp_asi_data['count'] if mcp_asi_data else 0
    mcp_asi_steps = mcp_asi_data['avg_steps'] if mcp_asi_data else 0
    mcp_asi_reuse = mcp_asi_data['skill_reuse_run_pct']*100 if mcp_asi_data else 0
    mcp_asi_class = 'danger' if not mcp_asi_data else ('success' if mcp_asi_data['success_rate'] > 0.2 else 'warning')
    
    html += f"""
            <div class="kpi-card mcp-asi">
                <h3>MCP + ASI</h3>
                <div class="kpi-value {mcp_asi_class}">{mcp_asi_success:.1f}%</div>
                <div class="kpi-label">Task Success Rate</div>
                <div style="margin-top: 10px;">
                    <small>n = {mcp_asi_count} | Avg Steps: {mcp_asi_steps:.1f} | Skill Reuse: {mcp_asi_reuse:.1f}%</small>
                </div>
            </div>
        </div>

        <!-- Research Hypotheses Analysis -->
        <div class="hypothesis-section">
            <h3>Research Hypothesis Validation</h3>
            
            <div class="metric-row">
                <div><strong>H1: MCP tooling improves task success rate</strong></div>
                <div>{get_status_badge('MCP_vs_Vanilla', 'success_lift_pct')}</div>
            </div>
            
            <div class="metric-row">
                <div><strong>H2: ASI improves success rate (Vanilla baseline)</strong></div>
                <div>{get_status_badge('VanillaASI_vs_Vanilla', 'success_lift_pct')}</div>
            </div>
            
            <div class="metric-row">
                <div><strong>H3: ASI improves success rate (MCP baseline)</strong></div>
                <div>{get_status_badge('MCPASI_vs_MCP', 'success_lift_pct')}</div>
            </div>
            
            <div class="metric-row">
                <div><strong>H4: Full system (MCP+ASI) outperforms Vanilla</strong></div>
                <div>{get_status_badge('MCPASI_vs_Vanilla', 'success_lift_pct')}</div>
            </div>
            
            <div class="metric-row">
                <div><strong>H5: ASI demonstrates skill reuse capabilities</strong></div>
                <div>{get_status_badge('VanillaASI_vs_Vanilla', 'skill_reuse_rate')}</div>
            </div>
        </div>

        <!-- Detailed Performance Comparison -->
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Configuration</th>
                    <th>Success Rate</th>
                    <th>Avg Steps</th>
                    <th>Avg Time (s)</th>
                    <th>Skills Reused</th>
                    <th>Skills Induced</th>
                    <th>Token Usage</th>
                </tr>
            </thead>
            <tbody>"""

    for config_name in ['Vanilla', 'Vanilla+ASI', 'MCP', 'MCP+ASI']:
        data = results.get(config_name)
        if data:
            # Use dashes for non-ASI conditions since they don't do skill induction/reuse
            if config_name in ['Vanilla', 'MCP']:
                skills_reused_display = "—"
                skills_induced_display = "—"
            else:
                skills_reused_display = f"{data['avg_skills_reused']:.1f}"
                skills_induced_display = f"{data['avg_skills_induced']:.1f}"
            
            html += f"""
                <tr>
                    <td><strong>{config_name}</strong> (n={data['count']})</td>
                    <td>{data['success_rate']*100:.1f}%</td>
                    <td>{data['avg_steps']:.1f} ± {data['std_steps']:.1f}</td>
                    <td>{data['avg_agent_time']:.1f}s</td>
                    <td>{skills_reused_display}</td>
                    <td>{skills_induced_display}</td>
                    <td>{data['avg_tokens']:,.0f}</td>
                </tr>"""
        else:
            html += f"""
                <tr>
                    <td><strong>{config_name}</strong></td>
                    <td colspan="6" style="text-align: center; color: #6c757d;">No experiments available</td>
                </tr>"""

    html += """
            </tbody>
        </table>

        <!-- Effect Size Analysis -->"""
    
    if comparisons:
        html += """
        <div class="hypothesis-section">
            <h3>Effect Size Analysis</h3>"""
        
        for comp_name, comp_data in comparisons.items():
            friendly_name = comp_name.replace('_vs_', ' vs ').replace('_', ' ')
            html += f"""
            <div class="metric-row">
                <div><strong>{friendly_name}</strong></div>
                <div>
                    Success: {comp_data.get('success_lift_pct', 0):+.1f}% | 
                    Efficiency: {comp_data.get('step_efficiency_pct', 0):+.1f}%
                </div>
            </div>"""
        
        html += "</div>"

    html += f"""
        <div class="footnote">
            <p><strong>Methodology:</strong> Analysis based on WebArena shopping task experiments. Success rate = tasks achieving reward ≥ 1.0. 
            Effect sizes calculated as percentage improvement over baseline. Sample size adequacy threshold = 10 experiments per condition.</p>
            <p><strong>Generated:</strong> {timestamp} | <strong>Data Source:</strong> ASI Research Metrics v1.0</p>
        </div>
    </div>
</body>
</html>"""

    return html

def main():
    """Generate and save the research dashboard"""
    import sys
    
    # Check if cohort path is provided as argument
    if len(sys.argv) > 1:
        cohort_path = sys.argv[1]
        if cohort_path.startswith("--cohort="):
            cohort_path = cohort_path[9:]
        
        cohort_name = Path(cohort_path).name
        experiments = collect_cohort_data(cohort_path)
        
        if not experiments:
            print(f"No experiment data found in cohort: {cohort_path}")
            return
        
        print(f"Found {len(experiments)} experiments in cohort: {cohort_name}")
        
        results = analyze_experiments(experiments)
        comparisons = calculate_statistical_significance(results)
        
        html = generate_html_dashboard(results, comparisons, len(experiments), cohort_name)
        
        output_file = f"research_dashboard_{cohort_name}.html"
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"Cohort dashboard generated: {output_file}")
        print(f"Open file://{os.path.abspath(output_file)} in your browser to view")
    else:
        # Default: analyze all experiments
        experiments = collect_experiment_data()
        
        if not experiments:
            print("No experiment data found. Please run some experiments first.")
            return
        
        print(f"Found {len(experiments)} experiments")
        
        results = analyze_experiments(experiments)
        comparisons = calculate_statistical_significance(results)
        
        html = generate_html_dashboard(results, comparisons, len(experiments))
        
        output_file = "research_dashboard.html"
        with open(output_file, 'w') as f:
            f.write(html)
        
        print(f"Research dashboard generated: {output_file}")
        print(f"Open file://{os.path.abspath(output_file)} in your browser to view")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
MCP Research Hypothesis Tracker
Tests specific hypotheses about MCP tooling effectiveness:
1. MCP tooling improves success rate
2. MCP tooling improves skill induction efficacy (reuse, efficiency)
"""

import json
import os
import glob
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics

class MCPResearchTracker:
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.experiments = []
        
    def load_experiments(self) -> List[Dict[str, Any]]:
        """Load all research_metrics.json files"""
        pattern = os.path.join(self.results_dir, "webarena.*/research_metrics.json")
        files = glob.glob(pattern)
        
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    data['experiment_dir'] = os.path.dirname(file_path)
                    self.experiments.append(data)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                
        return self.experiments

    def categorize_experiments(self) -> Dict[str, List[Dict]]:
        """Categorize experiments by MCP usage for hypothesis testing"""
        categories = {
            'mcp_enabled': [],
            'mcp_disabled': [],
            'mcp_high_usage': [],  # >2 MCP calls
            'mcp_low_usage': [],   # 1-2 MCP calls
            'mcp_no_usage': []     # 0 MCP calls
        }
        
        for exp in self.experiments:
            # MCP enabled/disabled
            if exp.get('configuration', {}).get('mcp_enabled', False):
                categories['mcp_enabled'].append(exp)
            else:
                categories['mcp_disabled'].append(exp)
            
            # MCP usage levels
            mcp_calls = exp.get('mcp_call_count', 0)
            if mcp_calls == 0:
                categories['mcp_no_usage'].append(exp)
            elif mcp_calls <= 2:
                categories['mcp_low_usage'].append(exp)
            else:
                categories['mcp_high_usage'].append(exp)
        
        return categories

    def test_hypothesis_1_success_rate(self) -> Dict[str, Any]:
        """Test H1: MCP tooling improves success rate"""
        categories = self.categorize_experiments()
        
        def calc_success_rate(experiments):
            if not experiments:
                return 0.0
            return sum(1 for exp in experiments if exp['task_execution']['success']) / len(experiments)
        
        results = {
            'mcp_enabled_success': calc_success_rate(categories['mcp_enabled']),
            'mcp_disabled_success': calc_success_rate(categories['mcp_disabled']),
            'mcp_high_usage_success': calc_success_rate(categories['mcp_high_usage']),
            'mcp_low_usage_success': calc_success_rate(categories['mcp_low_usage']),
            'mcp_no_usage_success': calc_success_rate(categories['mcp_no_usage']),
            'sample_sizes': {
                'mcp_enabled': len(categories['mcp_enabled']),
                'mcp_disabled': len(categories['mcp_disabled']),
                'mcp_high_usage': len(categories['mcp_high_usage']),
                'mcp_low_usage': len(categories['mcp_low_usage']),
                'mcp_no_usage': len(categories['mcp_no_usage'])
            }
        }
        
        # Calculate improvements
        if len(categories['mcp_disabled']) > 0:
            results['mcp_enabled_improvement'] = results['mcp_enabled_success'] - results['mcp_disabled_success']
        else:
            results['mcp_enabled_improvement'] = None
            
        # Usage level comparison
        usage_rates = [
            ('no_usage', results['mcp_no_usage_success']),
            ('low_usage', results['mcp_low_usage_success']),
            ('high_usage', results['mcp_high_usage_success'])
        ]
        results['usage_trend'] = sorted(usage_rates, key=lambda x: x[1], reverse=True)
        
        return results

    def test_hypothesis_2_skill_induction(self) -> Dict[str, Any]:
        """Test H2: MCP tooling improves skill induction efficacy"""
        categories = self.categorize_experiments()
        
        def analyze_skill_metrics(experiments, name):
            if not experiments:
                return {'name': name, 'count': 0}
            
            # Filter for ASI-enabled experiments only
            asi_experiments = [exp for exp in experiments if exp.get('configuration', {}).get('asi_enabled', False)]
            
            if not asi_experiments:
                return {'name': name, 'count': 0, 'asi_experiments': 0}
            
            return {
                'name': name,
                'count': len(experiments),
                'asi_experiments': len(asi_experiments),
                'skill_reuse_rate': sum(1 for exp in asi_experiments if exp['skills_reused_count'] > 0) / len(asi_experiments),
                'avg_skills_reused': statistics.mean([exp['skills_reused_count'] for exp in asi_experiments]),
                'avg_skills_induced': statistics.mean([exp['skills_induced_count'] for exp in asi_experiments]),
                'avg_steps': statistics.mean([exp['task_execution']['steps'] for exp in asi_experiments]),
                'avg_success_rate': sum(1 for exp in asi_experiments if exp['task_execution']['success']) / len(asi_experiments),
                'skill_induction_rate': sum(1 for exp in asi_experiments if exp['skill_induction']) / len(asi_experiments),
                'avg_skill_library_growth': statistics.mean([
                    exp['skill_library_size_after'] - exp['skill_library_size_before'] 
                    for exp in asi_experiments
                ])
            }
        
        results = {
            'mcp_enabled': analyze_skill_metrics(categories['mcp_enabled'], 'MCP Enabled'),
            'mcp_disabled': analyze_skill_metrics(categories['mcp_disabled'], 'MCP Disabled'),
            'mcp_high_usage': analyze_skill_metrics(categories['mcp_high_usage'], 'High MCP Usage'),
            'mcp_low_usage': analyze_skill_metrics(categories['mcp_low_usage'], 'Low MCP Usage'),
            'mcp_no_usage': analyze_skill_metrics(categories['mcp_no_usage'], 'No MCP Usage')
        }
        
        # Calculate improvements
        mcp_enabled_valid = results['mcp_enabled'].get('asi_experiments', 0) > 0
        mcp_disabled_valid = results['mcp_disabled'].get('asi_experiments', 0) > 0
        
        if mcp_disabled_valid and mcp_enabled_valid:
            results['skill_reuse_improvement'] = (
                results['mcp_enabled']['skill_reuse_rate'] - results['mcp_disabled']['skill_reuse_rate']
            )
            results['step_efficiency_improvement'] = (
                results['mcp_disabled']['avg_steps'] - results['mcp_enabled']['avg_steps']
            )
        else:
            results['skill_reuse_improvement'] = None
            results['step_efficiency_improvement'] = None
        
        return results

    def analyze_mcp_server_impact(self) -> Dict[str, Any]:
        """Analyze impact of different MCP servers"""
        server_impact = defaultdict(lambda: {
            'experiments': 0,
            'successes': 0,
            'avg_skill_reuse': 0,
            'avg_steps': 0,
            'skill_reuse_experiments': 0
        })
        
        for exp in self.experiments:
            # Get connected servers
            connected_servers = {server['name'] for server in exp.get('mcp_connected', [])}
            
            for server_name in connected_servers:
                server_impact[server_name]['experiments'] += 1
                
                if exp['task_execution']['success']:
                    server_impact[server_name]['successes'] += 1
                
                server_impact[server_name]['avg_steps'] += exp['task_execution']['steps']
                
                if exp['skills_reused_count'] > 0:
                    server_impact[server_name]['skill_reuse_experiments'] += 1
                    server_impact[server_name]['avg_skill_reuse'] += exp['skills_reused_count']
        
        # Calculate averages and rates
        for server_name in server_impact:
            data = server_impact[server_name]
            if data['experiments'] > 0:
                data['success_rate'] = data['successes'] / data['experiments']
                data['avg_steps'] = data['avg_steps'] / data['experiments']
                data['skill_reuse_rate'] = data['skill_reuse_experiments'] / data['experiments']
                data['avg_skill_reuse'] = data['avg_skill_reuse'] / data['skill_reuse_experiments'] if data['skill_reuse_experiments'] > 0 else 0
        
        return dict(server_impact)

    def generate_batch_comparison(self, previous_results_file: str = None) -> Dict[str, Any]:
        """Compare current batch with previous results if available"""
        if not previous_results_file or not os.path.exists(previous_results_file):
            return {'comparison_available': False}
        
        try:
            with open(previous_results_file, 'r') as f:
                previous = json.load(f)
            
            current_h1 = self.test_hypothesis_1_success_rate()
            current_h2 = self.test_hypothesis_2_skill_induction()
            
            comparison = {
                'comparison_available': True,
                'success_rate_changes': {},
                'skill_metrics_changes': {}
            }
            
            # Compare H1 results
            if 'hypothesis_1' in previous:
                prev_h1 = previous['hypothesis_1']
                comparison['success_rate_changes'] = {
                    'mcp_enabled': current_h1['mcp_enabled_success'] - prev_h1.get('mcp_enabled_success', 0),
                    'mcp_disabled': current_h1['mcp_disabled_success'] - prev_h1.get('mcp_disabled_success', 0),
                    'sample_size_change': current_h1['sample_sizes']['mcp_enabled'] - prev_h1.get('sample_sizes', {}).get('mcp_enabled', 0)
                }
            
            # Compare H2 results
            if 'hypothesis_2' in previous:
                prev_h2 = previous['hypothesis_2']
                if current_h2['mcp_enabled']['asi_experiments'] > 0 and prev_h2.get('mcp_enabled', {}).get('asi_experiments', 0) > 0:
                    comparison['skill_metrics_changes'] = {
                        'skill_reuse_rate': current_h2['mcp_enabled']['skill_reuse_rate'] - prev_h2['mcp_enabled'].get('skill_reuse_rate', 0),
                        'avg_steps': current_h2['mcp_enabled']['avg_steps'] - prev_h2['mcp_enabled'].get('avg_steps', 0)
                    }
            
            return comparison
            
        except Exception as e:
            return {'comparison_available': False, 'error': str(e)}

    def generate_research_summary(self) -> str:
        """Generate focused research summary for hypothesis testing"""
        self.load_experiments()
        
        h1_results = self.test_hypothesis_1_success_rate()
        h2_results = self.test_hypothesis_2_skill_induction()
        server_impact = self.analyze_mcp_server_impact()
        
        report = []
        report.append("=" * 80)
        report.append("MCP RESEARCH HYPOTHESIS TRACKER")
        report.append("=" * 80)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Experiments: {len(self.experiments)}")
        report.append("")
        
        # Hypothesis 1 Results
        report.append("🎯 HYPOTHESIS 1: MCP tooling improves success rate")
        report.append("-" * 60)
        
        if h1_results['sample_sizes']['mcp_disabled'] > 0:
            improvement = h1_results['mcp_enabled_improvement']
            report.append(f"MCP Enabled:  {h1_results['mcp_enabled_success']:.1%} success ({h1_results['sample_sizes']['mcp_enabled']} experiments)")
            report.append(f"MCP Disabled: {h1_results['mcp_disabled_success']:.1%} success ({h1_results['sample_sizes']['mcp_disabled']} experiments)")
            report.append(f"Improvement:  {improvement:+.1%} ({'+' if improvement > 0 else ''}{'SUPPORTS' if improvement > 0 else 'CONTRADICTS'} hypothesis)")
        else:
            report.append(f"MCP Enabled:  {h1_results['mcp_enabled_success']:.1%} success ({h1_results['sample_sizes']['mcp_enabled']} experiments)")
            report.append("MCP Disabled: No data available")
            report.append("Result: Cannot test hypothesis - no control group")
        
        report.append("")
        report.append("Success Rate by MCP Usage Level:")
        for usage_type, success_rate in h1_results['usage_trend']:
            sample_size = h1_results['sample_sizes'][f'mcp_{usage_type}']
            report.append(f"  {usage_type.replace('_', ' ').title()}: {success_rate:.1%} ({sample_size} experiments)")
        report.append("")
        
        # Hypothesis 2 Results
        report.append("🧠 HYPOTHESIS 2: MCP tooling improves skill induction efficacy")
        report.append("-" * 60)
        
        mcp_enabled = h2_results['mcp_enabled']
        mcp_disabled = h2_results['mcp_disabled']
        
        if mcp_enabled.get('asi_experiments', 0) > 0:
            report.append(f"MCP Enabled Skill Metrics ({mcp_enabled['asi_experiments']} ASI experiments):")
            report.append(f"  Skill Reuse Rate:     {mcp_enabled['skill_reuse_rate']:.1%}")
            report.append(f"  Avg Skills Reused:    {mcp_enabled['avg_skills_reused']:.1f}")
            report.append(f"  Avg Steps per Task:   {mcp_enabled['avg_steps']:.1f}")
            report.append(f"  Success Rate:         {mcp_enabled['avg_success_rate']:.1%}")
            report.append("")
            
            if mcp_disabled.get('asi_experiments', 0) > 0:
                report.append(f"MCP Disabled Skill Metrics ({mcp_disabled['asi_experiments']} ASI experiments):")
                report.append(f"  Skill Reuse Rate:     {mcp_disabled['skill_reuse_rate']:.1%}")
                report.append(f"  Avg Skills Reused:    {mcp_disabled['avg_skills_reused']:.1f}")
                report.append(f"  Avg Steps per Task:   {mcp_disabled['avg_steps']:.1f}")
                report.append(f"  Success Rate:         {mcp_disabled['avg_success_rate']:.1%}")
                report.append("")
                
                # Improvements
                reuse_improvement = h2_results['skill_reuse_improvement']
                step_improvement = h2_results['step_efficiency_improvement']
                
                report.append("Hypothesis 2 Results:")
                report.append(f"  Skill Reuse Improvement: {reuse_improvement:+.1%} ({'SUPPORTS' if reuse_improvement > 0 else 'CONTRADICTS'} hypothesis)")
                report.append(f"  Step Efficiency Gain:    {step_improvement:+.1f} steps ({'SUPPORTS' if step_improvement > 0 else 'CONTRADICTS'} hypothesis)")
            else:
                report.append("MCP Disabled: No ASI experiments available for comparison")
        else:
            report.append("No ASI experiments with MCP enabled - cannot test hypothesis")
        
        report.append("")
        
        # MCP Server Impact
        if server_impact:
            report.append("🔧 MCP SERVER EFFECTIVENESS")
            report.append("-" * 60)
            # Sort servers by success rate
            sorted_servers = sorted(server_impact.items(), key=lambda x: x[1]['success_rate'], reverse=True)
            
            for server_name, metrics in sorted_servers[:5]:  # Top 5 servers
                report.append(f"{server_name}:")
                report.append(f"  Success Rate:      {metrics['success_rate']:.1%} ({metrics['successes']}/{metrics['experiments']})")
                report.append(f"  Skill Reuse Rate:  {metrics['skill_reuse_rate']:.1%}")
                report.append(f"  Avg Steps:         {metrics['avg_steps']:.1f}")
                report.append("")
        
        # Research Recommendations
        report.append("📋 RESEARCH STATUS & RECOMMENDATIONS")
        report.append("-" * 60)
        
        # Overall assessment
        h1_improvement = h1_results.get('mcp_enabled_improvement')
        h1_supported = h1_improvement is not None and h1_improvement > 0
        
        h2_reuse_improvement = h2_results.get('skill_reuse_improvement')
        h2_reuse_supported = h2_reuse_improvement is not None and h2_reuse_improvement > 0
        
        h2_efficiency_improvement = h2_results.get('step_efficiency_improvement')
        h2_efficiency_supported = h2_efficiency_improvement is not None and h2_efficiency_improvement > 0
        
        report.append("Hypothesis Status:")
        report.append(f"  H1 (Success Rate):     {'✓ SUPPORTED' if h1_supported else '✗ NOT SUPPORTED'}")
        report.append(f"  H2a (Skill Reuse):     {'✓ SUPPORTED' if h2_reuse_supported else '✗ NOT SUPPORTED'}")
        report.append(f"  H2b (Step Efficiency): {'✓ SUPPORTED' if h2_efficiency_supported else '✗ NOT SUPPORTED'}")
        report.append("")
        
        # Actionable recommendations
        if not h1_supported:
            report.append("🔍 H1 NOT SUPPORTED: Consider investigating:")
            report.append("   • Task complexity vs MCP capability mismatch")
            report.append("   • MCP call overhead reducing performance")
            report.append("   • Need for MCP optimization or selective usage")
        
        if not h2_reuse_supported:
            report.append("🔍 H2a NOT SUPPORTED: Skill reuse not improving with MCP")
            report.append("   • Investigate skill-MCP integration quality")
            report.append("   • Consider MCP-aware skill induction strategies")
        
        if not h2_efficiency_supported:
            report.append("🔍 H2b NOT SUPPORTED: Step efficiency not improving with MCP")
            report.append("   • Analyze if MCP adds unnecessary complexity")
            report.append("   • Consider direct vs MCP-mediated task completion")
        
        return "\n".join(report)

    def save_results(self, filename: str = None):
        """Save results for batch comparison"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(self.results_dir, f"mcp_research_results_{timestamp}.json")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'total_experiments': len(self.experiments),
            'hypothesis_1': self.test_hypothesis_1_success_rate(),
            'hypothesis_2': self.test_hypothesis_2_skill_induction(),
            'server_impact': self.analyze_mcp_server_impact()
        }
        
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
        
        return filename

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory '{results_dir}' not found")
        sys.exit(1)
    
    tracker = MCPResearchTracker(results_dir)
    
    # Generate and display summary
    summary = tracker.generate_research_summary()
    print(summary)
    
    # Save results for future comparison
    results_file = tracker.save_results()
    print(f"\n📊 Results saved for batch comparison: {results_file}")

if __name__ == "__main__":
    main()
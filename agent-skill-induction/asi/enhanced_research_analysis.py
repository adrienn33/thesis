#!/usr/bin/env python3
"""
Enhanced WebArena Research Metrics Analysis
Provides deeper insights and correlations between success and various factors
"""

import json
import os
import glob
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any, Tuple
import statistics

class EnhancedWebArenaAnalyzer:
    def __init__(self, results_dir: str):
        self.results_dir = results_dir
        self.experiments = []
        
    def load_experiments(self) -> List[Dict[str, Any]]:
        """Load all research_metrics.json files"""
        pattern = os.path.join(self.results_dir, "webarena.*/research_metrics.json")
        files = glob.glob(pattern)
        
        print(f"Found {len(files)} research_metrics.json files")
        
        for file_path in files:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    data['experiment_dir'] = os.path.dirname(file_path)
                    self.experiments.append(data)
            except Exception as e:
                print(f"Error loading {file_path}: {e}")
                
        print(f"Successfully loaded {len(self.experiments)} experiments")
        return self.experiments
    
    def analyze_success_factors(self) -> Dict[str, Any]:
        """Analyze what factors correlate with success"""
        successful = [exp for exp in self.experiments if exp['task_execution']['success']]
        failed = [exp for exp in self.experiments if not exp['task_execution']['success']]
        
        def compare_metric(metric_func, name):
            success_values = [metric_func(exp) for exp in successful]
            failed_values = [metric_func(exp) for exp in failed]
            
            return {
                'successful': {
                    'avg': statistics.mean(success_values) if success_values else 0,
                    'median': statistics.median(success_values) if success_values else 0,
                    'count': len(success_values)
                },
                'failed': {
                    'avg': statistics.mean(failed_values) if failed_values else 0,
                    'median': statistics.median(failed_values) if failed_values else 0,
                    'count': len(failed_values)
                },
                'difference': {
                    'avg_diff': (statistics.mean(success_values) - statistics.mean(failed_values)) if success_values and failed_values else 0,
                    'success_advantage': ((statistics.mean(success_values) / statistics.mean(failed_values)) - 1) * 100 if success_values and failed_values and statistics.mean(failed_values) != 0 else 0
                }
            }
        
        factors = {
            'mcp_calls': compare_metric(lambda x: x['mcp_call_count'], 'MCP Calls'),
            'skill_calls': compare_metric(lambda x: x['skill_call_count'], 'Skill Calls'),
            'browser_actions': compare_metric(lambda x: x['browser_action_count'], 'Browser Actions'),
            'steps_taken': compare_metric(lambda x: x['task_execution']['steps'], 'Steps Taken'),
            'execution_time': compare_metric(lambda x: x['task_execution']['elapsed_time'], 'Execution Time'),
            'agent_time': compare_metric(lambda x: x['task_execution']['agent_elapsed_time'], 'Agent Time'),
            'total_tokens': compare_metric(lambda x: x['token_usage']['total_input_tokens'], 'Total Tokens'),
            'available_skills': compare_metric(lambda x: len(x.get('available_skills', [])), 'Available Skills'),
            'skill_library_size': compare_metric(lambda x: x['skill_library_size_before'], 'Skill Library Size')
        }
        
        return factors
    
    def analyze_task_patterns(self) -> Dict[str, Any]:
        """Analyze patterns by task type/ID"""
        task_performance = defaultdict(lambda: {'total': 0, 'success': 0, 'task_ids': []})
        
        for exp in self.experiments:
            task_id = exp['task_id']
            task_performance[task_id]['total'] += 1
            task_performance[task_id]['task_ids'].append(task_id)
            if exp['task_execution']['success']:
                task_performance[task_id]['success'] += 1
        
        # Calculate success rates
        for task_id in task_performance:
            stats = task_performance[task_id]
            stats['success_rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 0
        
        # Find best and worst performing tasks
        sorted_tasks = sorted(task_performance.items(), key=lambda x: x[1]['success_rate'], reverse=True)
        
        return {
            'total_unique_tasks': len(task_performance),
            'best_performing': sorted_tasks[:10],
            'worst_performing': sorted_tasks[-10:],
            'never_succeeded': [(task, stats) for task, stats in task_performance.items() if stats['success'] == 0],
            'always_succeeded': [(task, stats) for task, stats in task_performance.items() if stats['success'] == stats['total'] and stats['total'] > 1]
        }
    
    def analyze_skill_effectiveness(self) -> Dict[str, Any]:
        """Analyze which skills are most effective"""
        # Skills vs Success
        experiments_with_skills = [exp for exp in self.experiments if len(exp.get('available_skills', [])) > 0]
        experiments_without_skills = [exp for exp in self.experiments if len(exp.get('available_skills', [])) == 0]
        
        skill_success_rate = sum(1 for exp in experiments_with_skills if exp['task_execution']['success']) / len(experiments_with_skills) if experiments_with_skills else 0
        no_skill_success_rate = sum(1 for exp in experiments_without_skills if exp['task_execution']['success']) / len(experiments_without_skills) if experiments_without_skills else 0
        
        # Skill induction vs success
        induction_experiments = [exp for exp in self.experiments if exp['skill_induction']]
        no_induction_experiments = [exp for exp in self.experiments if not exp['skill_induction']]
        
        induction_success_rate = sum(1 for exp in induction_experiments if exp['task_execution']['success']) / len(induction_experiments) if induction_experiments else 0
        no_induction_success_rate = sum(1 for exp in no_induction_experiments if exp['task_execution']['success']) / len(no_induction_experiments) if no_induction_experiments else 0
        
        # Skill reuse vs success
        reuse_experiments = [exp for exp in self.experiments if exp['skills_reused_count'] > 0]
        no_reuse_experiments = [exp for exp in self.experiments if exp['skills_reused_count'] == 0]
        
        reuse_success_rate = sum(1 for exp in reuse_experiments if exp['task_execution']['success']) / len(reuse_experiments) if reuse_experiments else 0
        no_reuse_success_rate = sum(1 for exp in no_reuse_experiments if exp['task_execution']['success']) / len(no_reuse_experiments) if no_reuse_experiments else 0
        
        return {
            'skills_available': {
                'with_skills': {'count': len(experiments_with_skills), 'success_rate': skill_success_rate},
                'without_skills': {'count': len(experiments_without_skills), 'success_rate': no_skill_success_rate},
                'advantage': skill_success_rate - no_skill_success_rate
            },
            'skill_induction': {
                'with_induction': {'count': len(induction_experiments), 'success_rate': induction_success_rate},
                'without_induction': {'count': len(no_induction_experiments), 'success_rate': no_induction_success_rate},
                'advantage': induction_success_rate - no_induction_success_rate
            },
            'skill_reuse': {
                'with_reuse': {'count': len(reuse_experiments), 'success_rate': reuse_success_rate},
                'without_reuse': {'count': len(no_reuse_experiments), 'success_rate': no_reuse_success_rate},
                'advantage': reuse_success_rate - no_reuse_success_rate
            }
        }
    
    def analyze_efficiency_patterns(self) -> Dict[str, Any]:
        """Analyze efficiency patterns - tokens, time, steps per success"""
        successful = [exp for exp in self.experiments if exp['task_execution']['success']]
        
        if not successful:
            return {'message': 'No successful experiments to analyze'}
            
        # Efficiency metrics for successful experiments
        tokens_per_success = [exp['token_usage']['total_input_tokens'] for exp in successful]
        time_per_success = [exp['task_execution']['elapsed_time'] for exp in successful]
        steps_per_success = [exp['task_execution']['steps'] for exp in successful]
        
        # Compare with overall averages
        all_tokens = [exp['token_usage']['total_input_tokens'] for exp in self.experiments]
        all_time = [exp['task_execution']['elapsed_time'] for exp in self.experiments]
        all_steps = [exp['task_execution']['steps'] for exp in self.experiments]
        
        return {
            'successful_experiments': {
                'avg_tokens': statistics.mean(tokens_per_success),
                'avg_time': statistics.mean(time_per_success),
                'avg_steps': statistics.mean(steps_per_success),
                'median_tokens': statistics.median(tokens_per_success),
                'median_time': statistics.median(time_per_success),
                'median_steps': statistics.median(steps_per_success)
            },
            'all_experiments': {
                'avg_tokens': statistics.mean(all_tokens),
                'avg_time': statistics.mean(all_time),
                'avg_steps': statistics.mean(all_steps)
            },
            'efficiency_comparison': {
                'token_efficiency': (statistics.mean(all_tokens) - statistics.mean(tokens_per_success)) / statistics.mean(all_tokens) * 100,
                'time_efficiency': (statistics.mean(all_time) - statistics.mean(time_per_success)) / statistics.mean(all_time) * 100,
                'step_efficiency': (statistics.mean(all_steps) - statistics.mean(steps_per_success)) / statistics.mean(all_steps) * 100
            }
        }
    
    def generate_research_insights(self) -> List[str]:
        """Generate research-focused insights"""
        insights = []
        
        # Load data
        self.load_experiments()
        success_factors = self.analyze_success_factors()
        task_patterns = self.analyze_task_patterns()
        skill_effectiveness = self.analyze_skill_effectiveness()
        efficiency = self.analyze_efficiency_patterns()
        
        # High-level findings
        total_success_rate = sum(1 for exp in self.experiments if exp['task_execution']['success']) / len(self.experiments)
        insights.append(f"🎯 RESEARCH FINDING: {total_success_rate:.1%} overall success rate across {len(self.experiments)} experiments")
        
        # Success factor analysis
        most_important_factors = []
        for factor_name, factor_data in success_factors.items():
            advantage = factor_data['difference']['success_advantage']
            if abs(advantage) > 10:  # More than 10% difference
                direction = "higher" if advantage > 0 else "lower"
                most_important_factors.append((factor_name.replace('_', ' ').title(), advantage, direction))
        
        if most_important_factors:
            insights.append("📊 SUCCESS FACTORS (>10% difference):")
            for factor, advantage, direction in sorted(most_important_factors, key=lambda x: abs(x[1]), reverse=True)[:5]:
                insights.append(f"   • Successful experiments have {direction} {factor} ({advantage:+.1f}%)")
        
        # Task difficulty insights
        never_succeeded = len(task_patterns['never_succeeded'])
        always_succeeded = len(task_patterns['always_succeeded'])
        total_unique = task_patterns['total_unique_tasks']
        
        insights.append(f"📋 TASK ANALYSIS: {never_succeeded}/{total_unique} tasks never succeeded, {always_succeeded} always succeeded")
        
        if task_patterns['best_performing']:
            best_task = task_patterns['best_performing'][0]
            insights.append(f"   • Best performing task: {best_task[0]} ({best_task[1]['success_rate']:.1%} success)")
        
        # Skill effectiveness
        skill_data = skill_effectiveness
        if skill_data['skills_available']['advantage'] != 0:
            advantage = skill_data['skills_available']['advantage'] * 100
            insights.append(f"🛠️ SKILL IMPACT: Having available skills {'improves' if advantage > 0 else 'hurts'} success by {abs(advantage):.1f}%")
        
        if skill_data['skill_reuse']['advantage'] != 0:
            reuse_advantage = skill_data['skill_reuse']['advantage'] * 100
            insights.append(f"   • Skill reuse {'improves' if reuse_advantage > 0 else 'hurts'} success by {abs(reuse_advantage):.1f}%")
        
        # Efficiency insights
        if 'efficiency_comparison' in efficiency:
            token_eff = efficiency['efficiency_comparison']['token_efficiency']
            time_eff = efficiency['efficiency_comparison']['time_efficiency']
            step_eff = efficiency['efficiency_comparison']['step_efficiency']
            
            insights.append("⚡ EFFICIENCY: Successful experiments are:")
            if abs(token_eff) > 5:
                insights.append(f"   • {abs(token_eff):.1f}% {'more' if token_eff < 0 else 'less'} token-efficient")
            if abs(time_eff) > 5:
                insights.append(f"   • {abs(time_eff):.1f}% {'faster' if time_eff > 0 else 'slower'} in execution")
            if abs(step_eff) > 5:
                insights.append(f"   • {abs(step_eff):.1f}% {'fewer' if step_eff > 0 else 'more'} steps on average")
        
        # MCP and ASI insights
        mcp_experiments = [exp for exp in self.experiments if exp.get('mcp_calls', False)]
        asi_experiments = [exp for exp in self.experiments if exp.get('configuration', {}).get('asi_enabled', False)]
        
        if mcp_experiments:
            mcp_success = sum(1 for exp in mcp_experiments if exp['task_execution']['success']) / len(mcp_experiments)
            insights.append(f"🔌 MCP USAGE: {len(mcp_experiments)} experiments used MCP with {mcp_success:.1%} success rate")
        
        if asi_experiments:
            asi_success = sum(1 for exp in asi_experiments if exp['task_execution']['success']) / len(asi_experiments)
            insights.append(f"🧠 ASI IMPACT: {len(asi_experiments)} experiments used ASI with {asi_success:.1%} success rate")
        
        return insights
    
    def generate_detailed_report(self) -> str:
        """Generate a comprehensive research-focused report"""
        self.load_experiments()
        
        report = []
        report.append("=" * 80)
        report.append("ENHANCED WEBARENA RESEARCH ANALYSIS")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Dataset: {len(self.experiments)} experiments analyzed")
        report.append("")
        
        # Research Insights
        report.append("🔬 KEY RESEARCH FINDINGS")
        report.append("-" * 50)
        for insight in self.generate_research_insights():
            if insight.startswith(('🎯', '📊', '📋', '🛠️', '⚡', '🔌', '🧠')):
                report.append(insight)
            else:
                report.append(f"  {insight}")
        report.append("")
        
        # Detailed Success Factor Analysis
        success_factors = self.analyze_success_factors()
        report.append("📈 DETAILED SUCCESS FACTOR ANALYSIS")
        report.append("-" * 50)
        
        for factor_name, data in success_factors.items():
            if abs(data['difference']['success_advantage']) > 5:  # Only show significant differences
                report.append(f"\n{factor_name.replace('_', ' ').title()}:")
                report.append(f"  Successful: {data['successful']['avg']:.2f} avg, {data['successful']['median']:.2f} median")
                report.append(f"  Failed: {data['failed']['avg']:.2f} avg, {data['failed']['median']:.2f} median")
                report.append(f"  Advantage: {data['difference']['success_advantage']:+.1f}%")
        
        report.append("")
        
        # Task Analysis
        task_patterns = self.analyze_task_patterns()
        report.append("📋 TASK DIFFICULTY ANALYSIS")
        report.append("-" * 50)
        report.append(f"Total unique tasks: {task_patterns['total_unique_tasks']}")
        report.append(f"Tasks that never succeeded: {len(task_patterns['never_succeeded'])}")
        report.append(f"Tasks that always succeeded: {len(task_patterns['always_succeeded'])}")
        report.append("")
        
        if task_patterns['best_performing']:
            report.append("Top 5 Best Performing Tasks:")
            for task, stats in task_patterns['best_performing'][:5]:
                report.append(f"  Task {task}: {stats['success_rate']:.1%} ({stats['success']}/{stats['total']})")
            report.append("")
        
        if task_patterns['worst_performing']:
            report.append("Bottom 5 Worst Performing Tasks:")
            for task, stats in task_patterns['worst_performing'][:5]:
                if stats['total'] > 1:  # Only show tasks attempted multiple times
                    report.append(f"  Task {task}: {stats['success_rate']:.1%} ({stats['success']}/{stats['total']})")
            report.append("")
        
        # Skill Effectiveness
        skill_eff = self.analyze_skill_effectiveness()
        report.append("🛠️ SKILL SYSTEM EFFECTIVENESS")
        report.append("-" * 50)
        
        skills_data = skill_eff['skills_available']
        report.append(f"With Skills Available: {skills_data['with_skills']['success_rate']:.1%} success ({skills_data['with_skills']['count']} experiments)")
        report.append(f"Without Skills: {skills_data['without_skills']['success_rate']:.1%} success ({skills_data['without_skills']['count']} experiments)")
        report.append(f"Skills Advantage: {skills_data['advantage']*100:+.1f} percentage points")
        report.append("")
        
        reuse_data = skill_eff['skill_reuse']
        report.append(f"With Skill Reuse: {reuse_data['with_reuse']['success_rate']:.1%} success ({reuse_data['with_reuse']['count']} experiments)")
        report.append(f"Without Skill Reuse: {reuse_data['without_reuse']['success_rate']:.1%} success ({reuse_data['without_reuse']['count']} experiments)")
        report.append(f"Reuse Advantage: {reuse_data['advantage']*100:+.1f} percentage points")
        report.append("")
        
        # Efficiency Analysis
        efficiency = self.analyze_efficiency_patterns()
        if 'successful_experiments' in efficiency:
            report.append("⚡ EFFICIENCY COMPARISON")
            report.append("-" * 50)
            succ = efficiency['successful_experiments']
            all_exp = efficiency['all_experiments']
            comp = efficiency['efficiency_comparison']
            
            report.append("Successful vs All Experiments:")
            report.append(f"  Tokens: {succ['avg_tokens']:,.0f} vs {all_exp['avg_tokens']:,.0f} ({comp['token_efficiency']:+.1f}% efficiency)")
            report.append(f"  Time: {succ['avg_time']:.1f}s vs {all_exp['avg_time']:.1f}s ({comp['time_efficiency']:+.1f}% efficiency)")
            report.append(f"  Steps: {succ['avg_steps']:.1f} vs {all_exp['avg_steps']:.1f} ({comp['step_efficiency']:+.1f}% efficiency)")
        
        return "\n".join(report)

def main():
    """Main entry point for enhanced analysis"""
    import sys
    
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory '{results_dir}' not found")
        print(f"Usage: {sys.argv[0]} [results_directory]")
        sys.exit(1)
    
    analyzer = EnhancedWebArenaAnalyzer(results_dir)
    report = analyzer.generate_detailed_report()
    print(report)
    
    # Save to file
    output_file = os.path.join(results_dir, "enhanced_analysis_report.txt")
    with open(output_file, 'w') as f:
        f.write(report)
    print(f"\nDetailed report saved to: {output_file}")

if __name__ == "__main__":
    main()
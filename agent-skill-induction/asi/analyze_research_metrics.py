#!/usr/bin/env python3
"""
WebArena Research Metrics Analysis
Analyzes research_metrics.json files across all experiment directories
"""

import json
import os
import glob
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any
import statistics

class WebArenaAnalyzer:
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
    
    def analyze_success_rates(self) -> Dict[str, Any]:
        """Analyze task success rates"""
        total_tasks = len(self.experiments)
        successful_tasks = sum(1 for exp in self.experiments if exp['task_execution']['success'])
        
        # Success by configuration
        config_success = defaultdict(lambda: {'total': 0, 'success': 0})
        for exp in self.experiments:
            config_name = exp['configuration']['name']
            config_success[config_name]['total'] += 1
            if exp['task_execution']['success']:
                config_success[config_name]['success'] += 1
                
        # Success by website
        website_success = defaultdict(lambda: {'total': 0, 'success': 0})
        for exp in self.experiments:
            website = exp['website']
            website_success[website]['total'] += 1
            if exp['task_execution']['success']:
                website_success[website]['success'] += 1
        
        return {
            'overall': {
                'total_tasks': total_tasks,
                'successful_tasks': successful_tasks,
                'success_rate': successful_tasks / total_tasks if total_tasks > 0 else 0
            },
            'by_configuration': {
                config: {
                    'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0,
                    **stats
                }
                for config, stats in config_success.items()
            },
            'by_website': {
                website: {
                    'success_rate': stats['success'] / stats['total'] if stats['total'] > 0 else 0,
                    **stats
                }
                for website, stats in website_success.items()
            }
        }
    
    def analyze_mcp_usage(self) -> Dict[str, Any]:
        """Analyze MCP server usage"""
        mcp_enabled_experiments = [exp for exp in self.experiments if exp.get('configuration', {}).get('mcp_enabled', False)]
        
        # MCP server connections
        server_connections = Counter()
        for exp in mcp_enabled_experiments:
            for server in exp.get('mcp_connected', []):
                server_connections[server['name']] += 1
                
        # MCP call statistics
        mcp_calls = [exp['mcp_call_count'] for exp in mcp_enabled_experiments]
        
        return {
            'mcp_enabled_experiments': len(mcp_enabled_experiments),
            'total_experiments': len(self.experiments),
            'mcp_adoption_rate': len(mcp_enabled_experiments) / len(self.experiments) if self.experiments else 0,
            'server_usage': dict(server_connections),
            'mcp_call_stats': {
                'total_calls': sum(mcp_calls),
                'avg_calls_per_experiment': statistics.mean(mcp_calls) if mcp_calls else 0,
                'max_calls': max(mcp_calls) if mcp_calls else 0,
                'experiments_with_calls': sum(1 for calls in mcp_calls if calls > 0),
                'call_distribution': Counter(mcp_calls)
            }
        }
    
    def analyze_skill_induction(self) -> Dict[str, Any]:
        """Analyze skill induction patterns"""
        asi_experiments = [exp for exp in self.experiments if exp.get('configuration', {}).get('asi_enabled', False)]
        
        # Skill statistics
        total_skills_induced = sum(exp['skills_induced_count'] for exp in asi_experiments)
        total_skills_reused = sum(exp['skills_reused_count'] for exp in asi_experiments)
        
        # Library size changes
        library_sizes_before = [exp['skill_library_size_before'] for exp in asi_experiments]
        library_sizes_after = [exp['skill_library_size_after'] for exp in asi_experiments]
        
        # Most common skills
        all_induced_skills = []
        all_reused_skills = []
        all_available_skills = []
        
        for exp in asi_experiments:
            all_induced_skills.extend(exp.get('skills_induced_names', []))
            all_reused_skills.extend(exp.get('skills_reused_names', []))
            all_available_skills.extend(exp.get('available_skills', []))
            
        return {
            'asi_enabled_experiments': len(asi_experiments),
            'skill_induction_stats': {
                'total_skills_induced': total_skills_induced,
                'total_skills_reused': total_skills_reused,
                'avg_skills_induced': statistics.mean([exp['skills_induced_count'] for exp in asi_experiments]) if asi_experiments else 0,
                'avg_skills_reused': statistics.mean([exp['skills_reused_count'] for exp in asi_experiments]) if asi_experiments else 0,
                'experiments_with_induction': sum(1 for exp in asi_experiments if exp['skill_induction']),
                'experiments_with_reuse': sum(1 for exp in asi_experiments if exp['skills_reused_count'] > 0)
            },
            'skill_library_stats': {
                'avg_library_size_before': statistics.mean(library_sizes_before) if library_sizes_before else 0,
                'avg_library_size_after': statistics.mean(library_sizes_after) if library_sizes_after else 0,
                'max_library_size': max(library_sizes_after) if library_sizes_after else 0
            },
            'most_common_skills': {
                'induced': Counter(all_induced_skills).most_common(10),
                'reused': Counter(all_reused_skills).most_common(10),
                'available': Counter(all_available_skills).most_common(10)
            }
        }
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze execution performance metrics"""
        # Time statistics
        elapsed_times = [exp['task_execution']['elapsed_time'] for exp in self.experiments]
        agent_times = [exp['task_execution']['agent_elapsed_time'] for exp in self.experiments]
        
        # Step statistics
        steps = [exp['task_execution']['steps'] for exp in self.experiments]
        total_steps = [exp['task_execution']['total_steps'] for exp in self.experiments]
        
        # Token usage
        total_tokens = [exp['token_usage']['total_input_tokens'] for exp in self.experiments]
        
        # Action type distribution
        browser_actions = [exp['browser_action_count'] for exp in self.experiments]
        skill_calls = [exp['skill_call_count'] for exp in self.experiments]
        
        return {
            'timing': {
                'avg_elapsed_time': statistics.mean(elapsed_times),
                'avg_agent_time': statistics.mean(agent_times),
                'max_elapsed_time': max(elapsed_times),
                'min_elapsed_time': min(elapsed_times)
            },
            'steps': {
                'avg_steps': statistics.mean(steps),
                'avg_total_steps': statistics.mean(total_steps),
                'max_steps': max(steps),
                'completion_rate': statistics.mean([s / ts for s, ts in zip(steps, total_steps) if ts > 0])
            },
            'token_usage': {
                'avg_total_tokens': statistics.mean(total_tokens),
                'max_total_tokens': max(total_tokens),
                'total_tokens_consumed': sum(total_tokens)
            },
            'action_distribution': {
                'avg_browser_actions': statistics.mean(browser_actions),
                'avg_skill_calls': statistics.mean(skill_calls),
                'total_browser_actions': sum(browser_actions),
                'total_skill_calls': sum(skill_calls)
            }
        }
    
    def generate_insights(self) -> List[str]:
        """Generate key insights from the data"""
        insights = []
        
        success_data = self.analyze_success_rates()
        mcp_data = self.analyze_mcp_usage()
        skill_data = self.analyze_skill_induction()
        perf_data = self.analyze_performance()
        
        # Success rate insights
        overall_success = success_data['overall']['success_rate']
        insights.append(f"Overall task success rate: {overall_success:.1%}")
        
        # Configuration comparison
        config_rates = success_data['by_configuration']
        if len(config_rates) > 1:
            best_config = max(config_rates.items(), key=lambda x: x[1]['success_rate'])
            insights.append(f"Best performing configuration: {best_config[0]} ({best_config[1]['success_rate']:.1%} success rate)")
        
        # MCP adoption and effectiveness
        mcp_adoption = mcp_data['mcp_adoption_rate']
        insights.append(f"MCP adoption rate: {mcp_adoption:.1%} of experiments")
        
        if mcp_data['mcp_call_stats']['experiments_with_calls'] > 0:
            insights.append(f"Average MCP calls per experiment: {mcp_data['mcp_call_stats']['avg_calls_per_experiment']:.1f}")
        
        # Skill induction insights
        if skill_data['asi_enabled_experiments'] > 0:
            induction_rate = skill_data['skill_induction_stats']['experiments_with_induction'] / skill_data['asi_enabled_experiments']
            insights.append(f"Skill induction occurred in {induction_rate:.1%} of ASI-enabled experiments")
            
            if skill_data['skill_induction_stats']['total_skills_reused'] > 0:
                reuse_rate = skill_data['skill_induction_stats']['experiments_with_reuse'] / skill_data['asi_enabled_experiments']
                insights.append(f"Skill reuse occurred in {reuse_rate:.1%} of ASI-enabled experiments")
        
        # Performance insights
        avg_time = perf_data['timing']['avg_elapsed_time']
        insights.append(f"Average task execution time: {avg_time:.1f} seconds")
        
        completion_rate = perf_data['steps']['completion_rate']
        insights.append(f"Average task completion rate: {completion_rate:.1%}")
        
        return insights
    
    def generate_report(self) -> str:
        """Generate a comprehensive analysis report"""
        self.load_experiments()
        
        report = []
        report.append("=" * 80)
        report.append("WebArena Research Metrics Analysis Report")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total experiments analyzed: {len(self.experiments)}")
        report.append("")
        
        # Key Insights
        report.append("KEY INSIGHTS")
        report.append("-" * 40)
        for insight in self.generate_insights():
            report.append(f"• {insight}")
        report.append("")
        
        # Success Analysis
        success_data = self.analyze_success_rates()
        report.append("TASK SUCCESS ANALYSIS")
        report.append("-" * 40)
        report.append(f"Overall Success Rate: {success_data['overall']['success_rate']:.1%}")
        report.append(f"Successful Tasks: {success_data['overall']['successful_tasks']}/{success_data['overall']['total_tasks']}")
        report.append("")
        
        if success_data['by_configuration']:
            report.append("Success by Configuration:")
            for config, stats in success_data['by_configuration'].items():
                report.append(f"  {config}: {stats['success_rate']:.1%} ({stats['success']}/{stats['total']})")
            report.append("")
        
        # MCP Analysis
        mcp_data = self.analyze_mcp_usage()
        report.append("MCP USAGE ANALYSIS")
        report.append("-" * 40)
        report.append(f"MCP Adoption: {mcp_data['mcp_adoption_rate']:.1%} ({mcp_data['mcp_enabled_experiments']}/{mcp_data['total_experiments']})")
        report.append(f"Total MCP Calls: {mcp_data['mcp_call_stats']['total_calls']}")
        report.append(f"Average Calls/Experiment: {mcp_data['mcp_call_stats']['avg_calls_per_experiment']:.1f}")
        report.append("")
        
        if mcp_data['server_usage']:
            report.append("Most Used MCP Servers:")
            for server, count in sorted(mcp_data['server_usage'].items(), key=lambda x: x[1], reverse=True):
                report.append(f"  {server}: {count} experiments")
            report.append("")
        
        # Skill Induction Analysis
        skill_data = self.analyze_skill_induction()
        if skill_data['asi_enabled_experiments'] > 0:
            report.append("SKILL INDUCTION ANALYSIS")
            report.append("-" * 40)
            stats = skill_data['skill_induction_stats']
            report.append(f"ASI-Enabled Experiments: {skill_data['asi_enabled_experiments']}")
            report.append(f"Total Skills Induced: {stats['total_skills_induced']}")
            report.append(f"Total Skills Reused: {stats['total_skills_reused']}")
            report.append(f"Avg Skills Induced/Experiment: {stats['avg_skills_induced']:.1f}")
            report.append(f"Experiments with Induction: {stats['experiments_with_induction']}")
            report.append(f"Experiments with Reuse: {stats['experiments_with_reuse']}")
            report.append("")
            
            if skill_data['most_common_skills']['induced']:
                report.append("Most Commonly Induced Skills:")
                for skill, count in skill_data['most_common_skills']['induced'][:5]:
                    report.append(f"  {skill}: {count} times")
                report.append("")
        
        # Performance Analysis
        perf_data = self.analyze_performance()
        report.append("PERFORMANCE ANALYSIS")
        report.append("-" * 40)
        report.append(f"Average Execution Time: {perf_data['timing']['avg_elapsed_time']:.1f}s")
        report.append(f"Average Agent Time: {perf_data['timing']['avg_agent_time']:.1f}s")
        report.append(f"Average Steps: {perf_data['steps']['avg_steps']:.1f}")
        report.append(f"Average Completion Rate: {perf_data['steps']['completion_rate']:.1%}")
        report.append(f"Total Tokens Consumed: {perf_data['token_usage']['total_tokens_consumed']:,}")
        report.append(f"Average Tokens/Experiment: {perf_data['token_usage']['avg_total_tokens']:,.0f}")
        report.append("")
        
        # Recent Experiments
        recent_experiments = sorted(self.experiments, 
                                  key=lambda x: x.get('generated_at', ''), 
                                  reverse=True)[:10]
        
        report.append("RECENT EXPERIMENTS (Last 10)")
        report.append("-" * 40)
        for exp in recent_experiments:
            success = "✓" if exp['task_execution']['success'] else "✗"
            task_id = exp['task_id']
            config = exp['configuration']['name']
            steps = exp['task_execution']['steps']
            report.append(f"  {success} Task {task_id} ({config}) - {steps} steps")
        
        return "\n".join(report)

def main():
    """Main entry point for the script"""
    import sys
    
    # Default to results directory relative to script location
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        results_dir = os.path.join(script_dir, "results")
    
    if not os.path.exists(results_dir):
        print(f"Error: Results directory '{results_dir}' not found")
        print(f"Usage: {sys.argv[0]} [results_directory]")
        sys.exit(1)
    
    analyzer = WebArenaAnalyzer(results_dir)
    report = analyzer.generate_report()
    print(report)
    
    # Optionally save to file
    output_file = os.path.join(results_dir, "analysis_report.txt")
    with open(output_file, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {output_file}")

if __name__ == "__main__":
    main()
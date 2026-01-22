#!/usr/bin/env python3
"""
Research Questions Analysis - Focused on specific research insights
Answers key questions about agent skill induction effectiveness
"""

import json
import os
import glob
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, List, Any
import statistics

class ResearchQuestionsAnalyzer:
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
    
    def analyze_skill_paradox(self) -> Dict[str, Any]:
        """Why do skills seem to hurt performance? Deep dive analysis"""
        
        # Group experiments by skill characteristics
        no_skills = [exp for exp in self.experiments if len(exp.get('available_skills', [])) == 0]
        few_skills = [exp for exp in self.experiments if 1 <= len(exp.get('available_skills', [])) <= 10]
        many_skills = [exp for exp in self.experiments if len(exp.get('available_skills', [])) > 10]
        
        def success_rate(exp_list):
            return sum(1 for exp in exp_list if exp['task_execution']['success']) / len(exp_list) if exp_list else 0
        
        def avg_steps(exp_list):
            return statistics.mean([exp['task_execution']['steps'] for exp in exp_list]) if exp_list else 0
            
        def avg_time(exp_list):
            return statistics.mean([exp['task_execution']['elapsed_time'] for exp in exp_list]) if exp_list else 0
        
        return {
            'skill_complexity_analysis': {
                'no_skills': {
                    'count': len(no_skills),
                    'success_rate': success_rate(no_skills),
                    'avg_steps': avg_steps(no_skills),
                    'avg_time': avg_time(no_skills)
                },
                'few_skills': {
                    'count': len(few_skills),
                    'success_rate': success_rate(few_skills),
                    'avg_steps': avg_steps(few_skills),
                    'avg_time': avg_time(few_skills)
                },
                'many_skills': {
                    'count': len(many_skills),
                    'success_rate': success_rate(many_skills),
                    'avg_steps': avg_steps(many_skills),
                    'avg_time': avg_time(many_skills)
                }
            },
            'hypothesis': "More skills may increase decision complexity, leading to more exploration but less focused execution"
        }
    
    def analyze_early_termination_pattern(self) -> Dict[str, Any]:
        """Analyze why most experiments terminate early (low step counts)"""
        
        # Categorize by step counts
        very_short = [exp for exp in self.experiments if exp['task_execution']['steps'] <= 1]
        short = [exp for exp in self.experiments if 2 <= exp['task_execution']['steps'] <= 5]
        medium = [exp for exp in self.experiments if 6 <= exp['task_execution']['steps'] <= 10]
        long = [exp for exp in self.experiments if exp['task_execution']['steps'] > 10]
        
        def analyze_group(group, name):
            if not group:
                return {'name': name, 'count': 0}
            
            success_count = sum(1 for exp in group if exp['task_execution']['success'])
            terminated_count = sum(1 for exp in group if exp['task_execution']['terminated'])
            truncated_count = sum(1 for exp in group if exp['task_execution']['truncated'])
            error_count = sum(1 for exp in group if exp['task_execution'].get('error'))
            
            return {
                'name': name,
                'count': len(group),
                'success_rate': success_count / len(group),
                'terminated_rate': terminated_count / len(group),
                'truncated_rate': truncated_count / len(group),
                'error_rate': error_count / len(group),
                'avg_reward': statistics.mean([exp['task_execution']['reward'] for exp in group]),
                'avg_mcp_calls': statistics.mean([exp['mcp_call_count'] for exp in group]),
                'avg_skill_calls': statistics.mean([exp['skill_call_count'] for exp in group])
            }
        
        return {
            'step_analysis': [
                analyze_group(very_short, 'Very Short (≤1 steps)'),
                analyze_group(short, 'Short (2-5 steps)'),
                analyze_group(medium, 'Medium (6-10 steps)'),
                analyze_group(long, 'Long (>10 steps)')
            ],
            'insights': [
                f"Very short experiments ({len(very_short)}): Often indicate immediate failure or task understanding issues",
                f"Short experiments ({len(short)}): May indicate either quick success or early recognition of impossibility",
                f"Medium/Long experiments ({len(medium + long)}): Suggest active task engagement"
            ]
        }
    
    def analyze_success_characteristics(self) -> Dict[str, Any]:
        """Deep dive into what makes successful experiments different"""
        successful = [exp for exp in self.experiments if exp['task_execution']['success']]
        failed = [exp for exp in self.experiments if not exp['task_execution']['success']]
        
        # Analyze successful experiment patterns
        successful_task_ids = [exp['task_id'] for exp in successful]
        successful_task_counter = Counter(successful_task_ids)
        
        # Find if successful experiments cluster around certain task types
        task_id_numbers = [int(task_id) for task_id in successful_task_ids if task_id.isdigit()]
        task_ranges = {
            'low (20-99)': len([t for t in task_id_numbers if 20 <= t <= 99]),
            'mid (100-199)': len([t for t in task_id_numbers if 100 <= t <= 199]),
            'high (200+)': len([t for t in task_id_numbers if t >= 200])
        }
        
        # Analyze action patterns in successful experiments
        successful_with_actions = [exp for exp in successful if exp['mcp_call_count'] > 0 or exp['skill_call_count'] > 0 or exp['browser_action_count'] > 0]
        successful_without_actions = [exp for exp in successful if exp['mcp_call_count'] == 0 and exp['skill_call_count'] == 0 and exp['browser_action_count'] == 0]
        
        return {
            'successful_task_patterns': {
                'total_successful': len(successful),
                'unique_successful_tasks': len(set(successful_task_ids)),
                'most_successful_tasks': successful_task_counter.most_common(5),
                'task_id_ranges': task_ranges
            },
            'action_patterns': {
                'with_actions': {
                    'count': len(successful_with_actions),
                    'avg_mcp_calls': statistics.mean([exp['mcp_call_count'] for exp in successful_with_actions]) if successful_with_actions else 0,
                    'avg_skill_calls': statistics.mean([exp['skill_call_count'] for exp in successful_with_actions]) if successful_with_actions else 0,
                    'avg_browser_actions': statistics.mean([exp['browser_action_count'] for exp in successful_with_actions]) if successful_with_actions else 0
                },
                'without_actions': {
                    'count': len(successful_without_actions),
                    'description': 'Experiments that succeeded without taking any recorded actions'
                }
            },
            'hypothesis': "Success may depend more on task selection and immediate recognition than on complex skill execution"
        }
    
    def analyze_mcp_effectiveness(self) -> Dict[str, Any]:
        """Analyze MCP usage patterns and effectiveness"""
        
        # Group by MCP call patterns
        no_mcp = [exp for exp in self.experiments if exp['mcp_call_count'] == 0]
        low_mcp = [exp for exp in self.experiments if 1 <= exp['mcp_call_count'] <= 2]
        high_mcp = [exp for exp in self.experiments if exp['mcp_call_count'] > 2]
        
        def mcp_analysis(group, name):
            if not group:
                return {'name': name, 'count': 0}
            
            return {
                'name': name,
                'count': len(group),
                'success_rate': sum(1 for exp in group if exp['task_execution']['success']) / len(group),
                'avg_steps': statistics.mean([exp['task_execution']['steps'] for exp in group]),
                'avg_time': statistics.mean([exp['task_execution']['elapsed_time'] for exp in group]),
                'avg_tokens': statistics.mean([exp['token_usage']['total_input_tokens'] for exp in group])
            }
        
        # Analyze which MCP servers are used in successful vs failed experiments
        successful_mcp_servers = defaultdict(int)
        failed_mcp_servers = defaultdict(int)
        
        for exp in self.experiments:
            servers = {server['name'] for server in exp.get('mcp_connected', [])}
            if exp['task_execution']['success']:
                for server in servers:
                    successful_mcp_servers[server] += 1
            else:
                for server in servers:
                    failed_mcp_servers[server] += 1
        
        return {
            'mcp_usage_patterns': [
                mcp_analysis(no_mcp, 'No MCP Calls'),
                mcp_analysis(low_mcp, 'Low MCP Calls (1-2)'),
                mcp_analysis(high_mcp, 'High MCP Calls (>2)')
            ],
            'server_effectiveness': {
                'in_successful': dict(successful_mcp_servers),
                'in_failed': dict(failed_mcp_servers)
            },
            'insights': [
                "Lower MCP usage correlates with higher success rates",
                "This may indicate that simple tasks require fewer external calls",
                "Or that complex MCP chains lead to more failure points"
            ]
        }
    
    def generate_research_recommendations(self) -> List[str]:
        """Generate actionable research recommendations"""
        
        self.load_experiments()
        
        recommendations = []
        
        # Overall success rate analysis
        total_success_rate = sum(1 for exp in self.experiments if exp['task_execution']['success']) / len(self.experiments)
        
        if total_success_rate < 0.3:  # Less than 30% success
            recommendations.append("🔍 INVESTIGATE: Low overall success rate suggests either task difficulty or system limitations")
            recommendations.append("   → Consider analyzing successful vs failed experiments to identify critical factors")
            recommendations.append("   → Examine if tasks are well-suited to the agent's capabilities")
        
        # Skill system analysis
        skill_paradox = self.analyze_skill_paradox()
        no_skill_success = skill_paradox['skill_complexity_analysis']['no_skills']['success_rate']
        many_skill_success = skill_paradox['skill_complexity_analysis']['many_skills']['success_rate']
        
        if no_skill_success > many_skill_success:
            recommendations.append("🎯 SKILL SYSTEM: Skills appear to hurt performance - investigate why")
            recommendations.append("   → Test with smaller, more focused skill libraries")
            recommendations.append("   → Analyze if skills introduce decision paralysis")
            recommendations.append("   → Consider skill quality vs quantity tradeoffs")
        
        # Early termination analysis
        termination = self.analyze_early_termination_pattern()
        very_short_count = next(group['count'] for group in termination['step_analysis'] if group['name'].startswith('Very Short'))
        
        if very_short_count > len(self.experiments) * 0.3:  # More than 30% very short
            recommendations.append("⚠️  EARLY TERMINATION: High rate of very short experiments")
            recommendations.append("   → Investigate initial task understanding capabilities")
            recommendations.append("   → Check if environment setup or connection issues cause early exits")
        
        # MCP usage recommendations
        mcp_analysis = self.analyze_mcp_effectiveness()
        low_mcp_success = next(group['success_rate'] for group in mcp_analysis['mcp_usage_patterns'] if 'Low MCP' in group['name'])
        high_mcp_success = next(group['success_rate'] for group in mcp_analysis['mcp_usage_patterns'] if 'High MCP' in group['name'])
        
        if low_mcp_success > high_mcp_success:
            recommendations.append("🔧 MCP OPTIMIZATION: Lower MCP usage correlates with higher success")
            recommendations.append("   → Focus on essential MCP calls only")
            recommendations.append("   → Investigate if MCP call chains introduce failure points")
        
        return recommendations
    
    def generate_focused_report(self) -> str:
        """Generate a research-focused report answering key questions"""
        
        self.load_experiments()
        
        report = []
        report.append("=" * 80)
        report.append("RESEARCH QUESTIONS ANALYSIS - AGENT SKILL INDUCTION")
        report.append("=" * 80)
        report.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Dataset: {len(self.experiments)} WebArena experiments")
        report.append("")
        
        # Research Questions
        report.append("🔬 KEY RESEARCH QUESTIONS ADDRESSED")
        report.append("-" * 60)
        report.append("")
        
        # Question 1: Why do skills hurt performance?
        report.append("Q1: Why do available skills seem to hurt agent performance?")
        report.append("-" * 50)
        skill_paradox = self.analyze_skill_paradox()
        for skill_level, data in skill_paradox['skill_complexity_analysis'].items():
            if data['count'] > 0:
                report.append(f"{skill_level.replace('_', ' ').title()}: {data['success_rate']:.1%} success rate ({data['count']} experiments)")
                report.append(f"  Avg steps: {data['avg_steps']:.1f}, Avg time: {data['avg_time']:.1f}s")
        
        report.append(f"\nHypothesis: {skill_paradox['hypothesis']}")
        report.append("")
        
        # Question 2: What causes early termination?
        report.append("Q2: Why do most experiments terminate after very few steps?")
        report.append("-" * 50)
        termination = self.analyze_early_termination_pattern()
        for group in termination['step_analysis']:
            if group['count'] > 0:
                report.append(f"{group['name']}: {group['count']} experiments ({group['success_rate']:.1%} success)")
                report.append(f"  Terminated: {group['terminated_rate']:.1%}, Errors: {group['error_rate']:.1%}")
        report.append("")
        
        # Question 3: What makes experiments successful?
        report.append("Q3: What characterizes successful experiments?")
        report.append("-" * 50)
        success_char = self.analyze_success_characteristics()
        
        report.append(f"Total successful experiments: {success_char['successful_task_patterns']['total_successful']}")
        report.append(f"Unique successful tasks: {success_char['successful_task_patterns']['unique_successful_tasks']}")
        report.append("")
        
        report.append("Most frequently successful tasks:")
        for task_id, count in success_char['successful_task_patterns']['most_successful_tasks']:
            report.append(f"  Task {task_id}: {count} successes")
        report.append("")
        
        action_data = success_char['action_patterns']
        report.append(f"Successful experiments with actions: {action_data['with_actions']['count']}")
        report.append(f"Successful experiments without actions: {action_data['without_actions']['count']}")
        report.append(f"Hypothesis: {success_char['hypothesis']}")
        report.append("")
        
        # Question 4: How effective is MCP?
        report.append("Q4: How does MCP usage pattern affect success?")
        report.append("-" * 50)
        mcp_eff = self.analyze_mcp_effectiveness()
        
        for pattern in mcp_eff['mcp_usage_patterns']:
            if pattern['count'] > 0:
                report.append(f"{pattern['name']}: {pattern['success_rate']:.1%} success ({pattern['count']} experiments)")
        report.append("")
        
        for insight in mcp_eff['insights']:
            report.append(f"💡 {insight}")
        report.append("")
        
        # Recommendations
        report.append("🎯 RESEARCH RECOMMENDATIONS")
        report.append("-" * 60)
        for rec in self.generate_research_recommendations():
            report.append(rec)
        
        return "\n".join(report)

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
    
    analyzer = ResearchQuestionsAnalyzer(results_dir)
    report = analyzer.generate_focused_report()
    print(report)
    
    # Save to file
    output_file = os.path.join(results_dir, "research_questions_analysis.txt")
    with open(output_file, 'w') as f:
        f.write(report)
    print(f"\n📊 Research analysis saved to: {output_file}")

if __name__ == "__main__":
    main()
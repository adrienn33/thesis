#!/usr/bin/env python3
"""
Aggregate Performance Metrics Analysis for ASI Experiments
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

def analyze_experiments(base_path: str) -> Dict:
    """
    Analyze all experimental results and calculate aggregate metrics.
    
    Args:
        base_path: Path to the directory containing experiment folders
    
    Returns:
        Dictionary containing raw data and calculated metrics
    """
    
    # Raw experimental data
    experiments = {}
    
    # Find all summary_info.json files
    base_dir = Path(base_path)
    summary_files = list(base_dir.glob("*/summary_info.json"))
    
    print(f"Found {len(summary_files)} experiment summary files")
    
    # Load all experimental data
    for summary_file in summary_files:
        experiment_id = summary_file.parent.name
        
        try:
            with open(summary_file, 'r') as f:
                data = json.load(f)
                experiments[experiment_id] = data
                print(f"Loaded {experiment_id}: n_steps={data['n_steps']}, cum_reward={data['cum_reward']}, terminated={data['terminated']}, truncated={data['truncated']}")
        except Exception as e:
            print(f"Error loading {experiment_id}: {e}")
            continue
    
    # Calculate aggregate metrics
    total_experiments = len(experiments)
    successful_experiments = []
    failed_experiments = []
    terminated_experiments = []
    truncated_experiments = []
    
    all_steps = []
    successful_steps = []
    failed_steps = []
    
    error_experiments = []
    
    for exp_id, data in experiments.items():
        n_steps = data['n_steps']
        cum_reward = data['cum_reward']
        terminated = data['terminated']
        truncated = data['truncated']
        err_msg = data.get('err_msg')
        
        all_steps.append(n_steps)
        
        # Success is defined as cum_reward > 0
        if cum_reward > 0:
            successful_experiments.append(exp_id)
            successful_steps.append(n_steps)
        else:
            failed_experiments.append(exp_id)
            failed_steps.append(n_steps)
        
        # Termination patterns
        if terminated:
            terminated_experiments.append(exp_id)
        if truncated:
            truncated_experiments.append(exp_id)
            
        # Error tracking
        if err_msg is not None:
            error_experiments.append((exp_id, err_msg))
    
    # Calculate metrics
    success_rate = len(successful_experiments) / total_experiments * 100 if total_experiments > 0 else 0
    avg_steps_all = sum(all_steps) / len(all_steps) if all_steps else 0
    avg_steps_successful = sum(successful_steps) / len(successful_steps) if successful_steps else 0
    avg_steps_failed = sum(failed_steps) / len(failed_steps) if failed_steps else 0
    
    termination_rate = len(terminated_experiments) / total_experiments * 100 if total_experiments > 0 else 0
    truncation_rate = len(truncated_experiments) / total_experiments * 100 if total_experiments > 0 else 0
    
    # Prepare results
    results = {
        'raw_data': experiments,
        'summary_metrics': {
            'total_experiments': total_experiments,
            'successful_experiments': len(successful_experiments),
            'failed_experiments': len(failed_experiments),
            'success_rate_percent': round(success_rate, 2),
            'average_steps_all': round(avg_steps_all, 2),
            'average_steps_successful': round(avg_steps_successful, 2),
            'average_steps_failed': round(avg_steps_failed, 2),
            'terminated_experiments': len(terminated_experiments),
            'truncated_experiments': len(truncated_experiments),
            'termination_rate_percent': round(termination_rate, 2),
            'truncation_rate_percent': round(truncation_rate, 2),
            'experiments_with_errors': len(error_experiments)
        },
        'detailed_breakdown': {
            'successful_experiment_ids': successful_experiments,
            'failed_experiment_ids': failed_experiments,
            'terminated_experiment_ids': terminated_experiments,
            'truncated_experiment_ids': truncated_experiments,
            'error_experiments': error_experiments,
            'step_distribution': {
                'all_steps': all_steps,
                'successful_steps': successful_steps,
                'failed_steps': failed_steps,
                'min_steps_all': min(all_steps) if all_steps else 0,
                'max_steps_all': max(all_steps) if all_steps else 0,
                'min_steps_successful': min(successful_steps) if successful_steps else 0,
                'max_steps_successful': max(successful_steps) if successful_steps else 0,
                'min_steps_failed': min(failed_steps) if failed_steps else 0,
                'max_steps_failed': max(failed_steps) if failed_steps else 0
            }
        }
    }
    
    return results

def print_analysis_report(results: Dict):
    """Print a formatted analysis report."""
    
    print("\n" + "="*80)
    print("EXPERIMENTAL RESULTS ANALYSIS")
    print("="*80)
    
    metrics = results['summary_metrics']
    breakdown = results['detailed_breakdown']
    
    print(f"\n📊 OVERALL PERFORMANCE METRICS")
    print(f"   Total number of experiments: {metrics['total_experiments']}")
    print(f"   Overall success rate: {metrics['success_rate_percent']}% ({metrics['successful_experiments']}/{metrics['total_experiments']})")
    print(f"   Average number of steps (all): {metrics['average_steps_all']}")
    print(f"   Average steps for successful tasks: {metrics['average_steps_successful']}")
    print(f"   Average steps for failed tasks: {metrics['average_steps_failed']}")
    
    print(f"\n🏁 TERMINATION PATTERNS")
    print(f"   Terminated experiments: {metrics['termination_rate_percent']}% ({metrics['terminated_experiments']}/{metrics['total_experiments']})")
    print(f"   Truncated experiments: {metrics['truncation_rate_percent']}% ({metrics['truncated_experiments']}/{metrics['total_experiments']})")
    
    step_dist = breakdown['step_distribution']
    print(f"\n📈 STEP DISTRIBUTION")
    print(f"   Steps range (all): {step_dist['min_steps_all']} - {step_dist['max_steps_all']}")
    if step_dist['successful_steps']:
        print(f"   Steps range (successful): {step_dist['min_steps_successful']} - {step_dist['max_steps_successful']}")
    if step_dist['failed_steps']:
        print(f"   Steps range (failed): {step_dist['min_steps_failed']} - {step_dist['max_steps_failed']}")
    
    print(f"\n❌ ERROR ANALYSIS")
    print(f"   Experiments with errors: {metrics['experiments_with_errors']}")
    if breakdown['error_experiments']:
        for exp_id, err_msg in breakdown['error_experiments']:
            print(f"   - {exp_id}: {err_msg}")
    
    print(f"\n✅ SUCCESSFUL EXPERIMENTS")
    if breakdown['successful_experiment_ids']:
        print(f"   {', '.join(breakdown['successful_experiment_ids'])}")
    else:
        print("   None")
    
    print(f"\n❌ FAILED EXPERIMENTS")
    if breakdown['failed_experiment_ids']:
        print(f"   {', '.join(breakdown['failed_experiment_ids'])}")
    else:
        print("   None")
    
    print(f"\n🔍 NOTABLE PATTERNS")
    
    # Success pattern analysis
    successful_terminated = sum(1 for exp_id in breakdown['successful_experiment_ids'] 
                               if exp_id in breakdown['terminated_experiment_ids'])
    successful_truncated = sum(1 for exp_id in breakdown['successful_experiment_ids'] 
                              if exp_id in breakdown['truncated_experiment_ids'])
    
    if metrics['successful_experiments'] > 0:
        print(f"   Of successful experiments:")
        print(f"   - {successful_terminated} terminated naturally ({successful_terminated/metrics['successful_experiments']*100:.1f}%)")
        print(f"   - {successful_truncated} were truncated ({successful_truncated/metrics['successful_experiments']*100:.1f}%)")
    
    # Failure pattern analysis
    failed_terminated = sum(1 for exp_id in breakdown['failed_experiment_ids'] 
                           if exp_id in breakdown['terminated_experiment_ids'])
    failed_truncated = sum(1 for exp_id in breakdown['failed_experiment_ids'] 
                          if exp_id in breakdown['truncated_experiment_ids'])
    
    if metrics['failed_experiments'] > 0:
        print(f"   Of failed experiments:")
        print(f"   - {failed_terminated} terminated naturally ({failed_terminated/metrics['failed_experiments']*100:.1f}%)")
        print(f"   - {failed_truncated} were truncated ({failed_truncated/metrics['failed_experiments']*100:.1f}%)")
    
    # Step efficiency analysis
    if step_dist['successful_steps'] and step_dist['failed_steps']:
        if metrics['average_steps_successful'] < metrics['average_steps_failed']:
            print(f"   Successful tasks completed in fewer steps on average ({metrics['average_steps_successful']:.1f} vs {metrics['average_steps_failed']:.1f})")
        else:
            print(f"   Failed tasks used fewer steps on average ({metrics['average_steps_failed']:.1f} vs {metrics['average_steps_successful']:.1f})")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Analyze experiments
    base_path = "/Users/christopher.mason/wsu/thesis_v3/agent-skill-induction/asi/adrienne/raw_data/asi"
    results = analyze_experiments(base_path)
    
    # Print report
    print_analysis_report(results)
    
    # Save detailed results to JSON
    output_file = "experiment_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nDetailed results saved to: {output_file}")
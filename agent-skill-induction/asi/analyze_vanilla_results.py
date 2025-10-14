#!/usr/bin/env python3
"""
Analyze all experimental results in vanilla directory
"""
import json
import os
from pathlib import Path
import statistics

def analyze_vanilla_results():
    vanilla_dir = Path("/Users/christopher.mason/wsu/thesis_v3/agent-skill-induction/asi/adrienne/raw_data/vanilla")
    
    # Collect all experiment directories
    exp_dirs = [d for d in vanilla_dir.iterdir() if d.is_dir() and d.name.startswith("webarena.")]
    exp_dirs.sort(key=lambda x: int(x.name.split('.')[1]))
    
    print(f"Found {len(exp_dirs)} experiment directories")
    
    # Collect data from all experiments
    all_data = []
    successful_experiments = []
    failed_experiments = []
    
    for exp_dir in exp_dirs:
        summary_file = exp_dir / "summary_info.json"
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                data = json.load(f)
                
            # Extract key metrics
            exp_data = {
                'experiment': exp_dir.name,
                'task_id': int(exp_dir.name.split('.')[1]),
                'n_steps': data['n_steps'],
                'cum_reward': data['cum_reward'],
                'cum_raw_reward': data.get('cum_raw_reward', 0),
                'terminated': data['terminated'],
                'truncated': data['truncated'],
                'err_msg': data.get('err_msg'),
                'success': data['cum_reward'] > 0,
                'total_elapsed': data.get('stats.cum_step_elapsed', 0),
                'agent_elapsed': data.get('stats.cum_agent_elapsed', 0),
                'total_tokens': data.get('stats.cum_n_token_last_action', 0)
            }
            
            all_data.append(exp_data)
            
            if exp_data['success']:
                successful_experiments.append(exp_data)
            else:
                failed_experiments.append(exp_data)
        else:
            print(f"Warning: No summary_info.json found in {exp_dir}")
    
    # Calculate aggregate metrics
    total_experiments = len(all_data)
    successful_count = len(successful_experiments)
    failed_count = len(failed_experiments)
    success_rate = (successful_count / total_experiments) * 100 if total_experiments > 0 else 0
    
    # Steps analysis
    all_steps = [exp['n_steps'] for exp in all_data]
    successful_steps = [exp['n_steps'] for exp in successful_experiments]
    failed_steps = [exp['n_steps'] for exp in failed_experiments]
    
    avg_steps_all = statistics.mean(all_steps) if all_steps else 0
    avg_steps_success = statistics.mean(successful_steps) if successful_steps else 0
    avg_steps_failed = statistics.mean(failed_steps) if failed_steps else 0
    
    # Termination analysis
    terminated_count = sum(1 for exp in all_data if exp['terminated'])
    truncated_count = sum(1 for exp in all_data if exp['truncated'])
    
    # Time analysis
    all_elapsed = [exp['total_elapsed'] for exp in all_data if exp['total_elapsed'] > 0]
    avg_elapsed = statistics.mean(all_elapsed) if all_elapsed else 0
    
    # Print detailed results
    print("\n" + "="*80)
    print("VANILLA BASELINE RESULTS ANALYSIS")
    print("="*80)
    
    print(f"\n1. EXPERIMENT OVERVIEW:")
    print(f"   Total experiments: {total_experiments}")
    print(f"   Task IDs: {sorted([exp['task_id'] for exp in all_data])}")
    
    print(f"\n2. SUCCESS METRICS:")
    print(f"   Successful tasks: {successful_count}")
    print(f"   Failed tasks: {failed_count}")
    print(f"   Overall success rate: {success_rate:.2f}%")
    
    print(f"\n3. STEP ANALYSIS:")
    print(f"   Average steps (all): {avg_steps_all:.2f}")
    print(f"   Average steps (successful): {avg_steps_success:.2f}")
    print(f"   Average steps (failed): {avg_steps_failed:.2f}")
    print(f"   Min steps: {min(all_steps)}")
    print(f"   Max steps: {max(all_steps)}")
    
    print(f"\n4. TERMINATION PATTERNS:")
    print(f"   Terminated: {terminated_count} ({(terminated_count/total_experiments)*100:.1f}%)")
    print(f"   Truncated: {truncated_count} ({(truncated_count/total_experiments)*100:.1f}%)")
    
    print(f"\n5. TIMING:")
    print(f"   Average total elapsed time: {avg_elapsed:.2f} seconds")
    
    # Error analysis
    errors = [exp for exp in all_data if exp['err_msg'] is not None]
    print(f"\n6. ERROR ANALYSIS:")
    print(f"   Experiments with errors: {len(errors)}")
    if errors:
        for exp in errors:
            print(f"   - {exp['experiment']}: {exp['err_msg']}")
    
    print(f"\n7. DETAILED RESULTS BY EXPERIMENT:")
    print(f"   {'Exp':<12} {'Task':<4} {'Success':<7} {'Steps':<5} {'Term':<4} {'Trunc':<5} {'Reward':<6} {'Time':<6}")
    print(f"   {'-'*12} {'-'*4} {'-'*7} {'-'*5} {'-'*4} {'-'*5} {'-'*6} {'-'*6}")
    
    for exp in sorted(all_data, key=lambda x: x['task_id']):
        success_str = "✓" if exp['success'] else "✗"
        term_str = "✓" if exp['terminated'] else "✗"
        trunc_str = "✓" if exp['truncated'] else "✗"
        
        print(f"   {exp['experiment']:<12} {exp['task_id']:<4} {success_str:<7} {exp['n_steps']:<5} {term_str:<4} {trunc_str:<5} {exp['cum_reward']:<6.1f} {exp['total_elapsed']:<6.1f}")
    
    # Return structured data for further analysis
    return {
        'total_experiments': total_experiments,
        'success_rate': success_rate,
        'successful_count': successful_count,
        'failed_count': failed_count,
        'avg_steps_all': avg_steps_all,
        'avg_steps_success': avg_steps_success,
        'avg_steps_failed': avg_steps_failed,
        'min_steps': min(all_steps) if all_steps else 0,
        'max_steps': max(all_steps) if all_steps else 0,
        'terminated_count': terminated_count,
        'truncated_count': truncated_count,
        'avg_elapsed_time': avg_elapsed,
        'error_count': len(errors),
        'raw_data': all_data,
        'successful_experiments': successful_experiments,
        'failed_experiments': failed_experiments,
        'task_ids': sorted([exp['task_id'] for exp in all_data])
    }

if __name__ == "__main__":
    results = analyze_vanilla_results()
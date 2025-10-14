#!/usr/bin/env python3
"""
Create a summary table of all experiments for easy comparison
"""

import json
from pathlib import Path

def create_summary_table():
    """Create a summary table from the analysis results."""
    
    # Load the analysis results
    with open('experiment_analysis_results.json', 'r') as f:
        results = json.load(f)
    
    raw_data = results['raw_data']
    
    print("EXPERIMENT SUMMARY TABLE")
    print("=" * 100)
    print(f"{'Experiment':<15} {'Steps':<6} {'Success':<8} {'Reward':<8} {'Term.':<6} {'Trunc.':<7} {'Errors':<7}")
    print("-" * 100)
    
    # Sort experiments by ID for consistent ordering
    sorted_experiments = sorted(raw_data.items(), key=lambda x: x[0])
    
    for exp_id, data in sorted_experiments:
        success = "✅ YES" if data['cum_reward'] > 0 else "❌ NO"
        terminated = "✅" if data['terminated'] else "❌"
        truncated = "✅" if data['truncated'] else "❌"
        has_errors = "✅" if data.get('err_msg') is not None else "❌"
        
        print(f"{exp_id:<15} {data['n_steps']:<6} {success:<8} {data['cum_reward']:<8} {terminated:<6} {truncated:<7} {has_errors:<7}")
    
    print("-" * 100)
    print("\nLegend:")
    print("Term. = Terminated normally")
    print("Trunc. = Truncated (hit step limit)")  
    print("Errors = Has error messages")
    print("✅ = True/Yes, ❌ = False/No")

if __name__ == "__main__":
    create_summary_table()
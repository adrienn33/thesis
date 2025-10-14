#!/usr/bin/env python3
"""
Generate structured summary of vanilla results for comparison
"""
import json
from analyze_vanilla_results import analyze_vanilla_results

def generate_summary():
    results = analyze_vanilla_results()
    
    # Create structured summary
    summary = {
        "dataset": "vanilla_baseline",
        "analysis_date": "2025-09-19",
        "total_experiments": results['total_experiments'],
        "task_ids_tested": results['task_ids'],
        
        "success_metrics": {
            "total_successful": results['successful_count'],
            "total_failed": results['failed_count'],
            "success_rate_percent": results['success_rate'],
            "successful_task_ids": [exp['task_id'] for exp in results['successful_experiments']],
            "failed_task_ids": [exp['task_id'] for exp in results['failed_experiments']]
        },
        
        "step_metrics": {
            "average_steps_all_tasks": results['avg_steps_all'],
            "average_steps_successful_tasks": results['avg_steps_success'],
            "average_steps_failed_tasks": results['avg_steps_failed'],
            "min_steps": results['min_steps'],
            "max_steps": results['max_steps'],
            "step_distribution": {
                str(i): len([exp for exp in results['raw_data'] if exp['n_steps'] == i])
                for i in range(1, 11)
            }
        },
        
        "termination_metrics": {
            "terminated_count": results['terminated_count'],
            "truncated_count": results['truncated_count'],
            "terminated_percent": (results['terminated_count'] / results['total_experiments']) * 100,
            "truncated_percent": (results['truncated_count'] / results['total_experiments']) * 100
        },
        
        "timing_metrics": {
            "average_elapsed_time_seconds": results['avg_elapsed_time'],
            "total_time_all_experiments": sum(exp['total_elapsed'] for exp in results['raw_data'])
        },
        
        "error_metrics": {
            "experiments_with_errors": results['error_count'],
            "error_rate_percent": (results['error_count'] / results['total_experiments']) * 100
        },
        
        "detailed_results": [
            {
                "task_id": exp['task_id'], 
                "experiment_name": exp['experiment'],
                "success": exp['success'],
                "n_steps": exp['n_steps'],
                "cum_reward": exp['cum_reward'],
                "terminated": exp['terminated'],
                "truncated": exp['truncated'],
                "total_elapsed_time": exp['total_elapsed'],
                "error_message": exp['err_msg']
            }
            for exp in sorted(results['raw_data'], key=lambda x: x['task_id'])
        ]
    }
    
    # Save to JSON file
    output_file = "/Users/christopher.mason/wsu/thesis_v3/agent-skill-induction/asi/vanilla_results_summary.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\nStructured summary saved to: {output_file}")
    
    # Print key comparison metrics
    print("\n" + "="*60)
    print("KEY METRICS FOR COMPARISON WITH ASI RESULTS")
    print("="*60)
    print(f"Total experiments: {summary['total_experiments']}")
    print(f"Success rate: {summary['success_metrics']['success_rate_percent']:.2f}%")
    print(f"Average steps (all): {summary['step_metrics']['average_steps_all_tasks']:.2f}")
    print(f"Average steps (successful): {summary['step_metrics']['average_steps_successful_tasks']:.2f}")
    print(f"Average steps (failed): {summary['step_metrics']['average_steps_failed_tasks']:.2f}")
    print(f"Termination rate: {summary['termination_metrics']['terminated_percent']:.1f}%")
    print(f"Truncation rate: {summary['termination_metrics']['truncated_percent']:.1f}%")
    print(f"Error rate: {summary['error_metrics']['error_rate_percent']:.1f}%")
    print(f"Average time per experiment: {summary['timing_metrics']['average_elapsed_time_seconds']:.1f}s")
    
    print(f"\nSuccessful tasks: {summary['success_metrics']['successful_task_ids']}")
    print(f"Failed tasks: {summary['success_metrics']['failed_task_ids']}")
    
    return summary

if __name__ == "__main__":
    summary = generate_summary()
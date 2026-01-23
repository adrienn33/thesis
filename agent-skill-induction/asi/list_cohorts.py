#!/usr/bin/env python3
"""
Quick script to list available cohorts and their data
"""

import json
from pathlib import Path
from collections import Counter

def main():
    results_dir = Path("results/final")
    
    if not results_dir.exists():
        print("No cohorts found. Please save some cohorts first.")
        return
    
    print("📊 Available Research Cohorts")
    print("=" * 50)
    
    for cohort_dir in sorted(results_dir.iterdir()):
        if cohort_dir.is_dir() and cohort_dir.name.startswith("cohort_"):
            print(f"\n🔬 {cohort_dir.name}")
            
            # Check structure
            condition_dirs = ['Vanilla', 'MCP', 'ASI']
            has_organized_structure = any((cohort_dir / d).exists() for d in condition_dirs)
            
            experiments = []
            configs = Counter()
            
            if has_organized_structure:
                print("   Structure: Organized (Vanilla/MCP/ASI subdirs)")
                for condition_dir in condition_dirs:
                    cond_path = cohort_dir / condition_dir
                    if cond_path.exists():
                        count = len(list(cond_path.glob("*_research_metrics.json")))
                        if count > 0:
                            print(f"   ├─ {condition_dir}: {count} experiments")
                            configs[condition_dir] += count
                            
                            # Sample one experiment for details
                            for metrics_file in cond_path.glob("*_research_metrics.json"):
                                try:
                                    with open(metrics_file) as f:
                                        data = json.load(f)
                                    experiments.append(data)
                                    break
                                except:
                                    pass
            else:
                print("   Structure: Legacy (flat)")
                for metrics_file in cohort_dir.glob("*_research_metrics.json"):
                    try:
                        with open(metrics_file) as f:
                            data = json.load(f)
                        experiments.append(data)
                        config_name = data.get('configuration', {}).get('name', 'Unknown')
                        configs[config_name] += 1
                    except:
                        pass
                
                for config, count in configs.most_common():
                    print(f"   ├─ {config}: {count} experiments")
            
            total_experiments = sum(configs.values())
            print(f"   └─ Total: {total_experiments} experiments")
            
            # Show sample task IDs
            if experiments:
                task_ids = [exp.get('task_id', 'unknown') for exp in experiments[:5]]
                print(f"   Sample tasks: {', '.join(task_ids)}")
            
            # Dashboard generation commands
            print(f"   📈 Generate dashboard: python3 research_dashboard.py {cohort_dir}")
            print(f"   🌐 Web dashboard: http://localhost:5000/api/research-dashboard?cohort={cohort_dir.name}")

if __name__ == "__main__":
    main()
# Agent Skill Induction - Organized Results

This directory contains cleaned and organized experimental results for easy analysis.

## Directory Structure

### `vanilla_task21_run/`
Complete artifacts from a vanilla baseline run on WebArena Task 21
- **Result**: Failed (0% success rate)
- **Agent**: claude-3-haiku-20240307 
- **Purpose**: Establish baseline performance before skill induction

## How to Use

1. **Quick Overview**: Read `vanilla_task21_run/QUICK_SUMMARY.txt`
2. **Detailed Analysis**: Read `vanilla_task21_run/README.md`
3. **Raw Data**: Explore the organized subdirectories

## Experimental Pipeline Understanding

```
run_online.py --experiment vanilla --task_ids "21-21"
    ↓
Creates timestamped directory in results/
    ↓  
Runs agent for max 10 steps, saving:
- Screenshots at each step
- State snapshots  
- Execution log
- Configuration
    ↓
Renames directory to results/webarena.21
    ↓
Results copied & organized here for analysis
```

## Next Steps

1. Run more vanilla tasks (21-25) for robust baseline
2. Run ASI experiments and compare performance
3. Calculate success rates and efficiency metrics
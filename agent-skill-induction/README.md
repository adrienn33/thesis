# _ASI_: Inducing Programmatic Skills for Agentic Tasks

## Quick Start :rocket:

```bash
cd asi
python run_online.py --experiment "asi" --website "shopping" --task_ids "21-25"
```

## Step 0: Setup

```bash
# create a new conda environment
conda create -n agent python=3.10
conda activate agent

# install the necessary packages
pip install browsergym==0.10.2
pip install gymnasium
pip install playwright==1.49.0
playwright install chromium

# to run webarena tasks
pip install browsergym-webarena==0.10.2
```

```bash
# setup litellm
export LITELLM_BASE_URL="your-base-url"
export LITELLM_API_KEY="your-api-key"
```


## Step 1: Solving WebArena Tasks

```bash
cd asi
```

Make sure you set the WEBSITE urls before running WebArena tasks.

```bash
BASE_URL="your-base-url"
export WA_SHOPPING="$BASE_URL:7770/"
export WA_SHOPPING_ADMIN="$BASE_URL:7780/admin"
export WA_REDDIT="$BASE_URL:9999"
export WA_GITLAB="$BASE_URL:8023"
export WA_WIKIPEDIA="$BASE_URL:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export WA_MAP="$BASE_URL:3000"
export WA_HOMEPAGE="$BASE_URL:4399"
```

To solve a particular webarena task (e.g., example 21), run the following command:

```bash
python run_demo.py --task_name "webarena.21" --websites "shopping" # to load website-specific induced actions
```

## Step 2: Evaluate Trajectory Correctness

```bash
python -m autoeval.evaluate_trajectory --result_dir "results/webarena.21"
```

## Step 3: Inducing Workflow Actions

To clean an episode, run:

```bash
python -m results.calc_valid_step --clean_and_store --result_id results/webarena.21
```

To induce workflow actions for a template group, run:

```bash
python induce_actions.py --result_id_list 21 --website "shopping"
```

This would generate workflow actions and write to `awa_actions/map.py` (by default), generate test cases and write to `debug_actions/test_{i}.txt`, then write and run the bash script `debug_actions/run_tests.sh` to verify the correctness of the induced actions.

If all test cases succeed, the induced actions are valid and added to the action space. Otherwise, the newly induced actions are discarded.

Repeat step 1-3 until all tasks are solved.

Instead of running the above command, you can also run the following command to induce actions for all tasks in a single command:

```bash
python run_online.py --experiment "asi" --website "shopping" --task_ids "21-25"
```

Switch the `--experiment` setting to "awm" or "vanilla" to try the baselines.

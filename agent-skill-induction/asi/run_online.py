import os
import json
import argparse
import subprocess
import logging
from subprocess import Popen
from pathlib import Path
from metrics import generate_research_metrics

logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
def load_env_file():
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Load .env on import
load_env_file()

def parse_task_ids(task_id_str: str) -> list[str]:
    chunks = [c.strip() for c in task_id_str.split(",")]
    task_id_list = []
    for c in chunks:
        if "-" in c:
            # Range format: "21-23"
            s, e = [int(n.strip()) for n in c.split("-")]
            task_id_list.extend([str(i) for i in range(s, e+1)])
        else:
            # Single ID: "21"
            task_id_list.append(c)
    return task_id_list

def run_vanilla():
    """Run vanilla experiments - no MCP, no ASI"""
    task_id_list = parse_task_ids(args.task_ids)

    for task_index, tid in enumerate(task_id_list, start=1+args.task_index_offset):
        # step 1: task solving
        cmd = [
            "venv/bin/python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--headless",
        ]
        
        # VANILLA: No MCP config at all - creates true control group
        # Don't add any --mcp_config parameter
        
        process = Popen(cmd)
        try:
            stdout, stderr = process.communicate(timeout=200)
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)
        
        # Generate research metrics after task completion (Vanilla: no MCP, no ASI)
        generate_research_metrics(tid, args.website, task_index, asi_enabled=False, mcp_enabled=False, skill_induction_attempted=False)

def run_mcp():
    """Run MCP-only experiments - MCP enabled, no ASI"""
    task_id_list = parse_task_ids(args.task_ids)

    for task_index, tid in enumerate(task_id_list, start=1+args.task_index_offset):
        # step 1: task solving
        cmd = [
            "venv/bin/python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--websites", args.website,
            "--headless"
        ]
        
        # Add MCP config if available
        mcp_config_file = f"config_files/{tid}-mcp-container.json"
        if os.path.exists(mcp_config_file):
            cmd.extend(["--mcp_config", mcp_config_file])
        else:
            regular_config = f"config_files/{tid}.json"
            if os.path.exists(regular_config):
                cmd.extend(["--mcp_config", regular_config])
        
        process = Popen(cmd)
        try:
            stdout, stderr = process.communicate(timeout=200)
            print("Process completed successfully:")
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)
        
        # Generate research metrics after task completion (MCP enabled, ASI disabled)
        generate_research_metrics(tid, args.website, task_index, asi_enabled=False, mcp_enabled=True, skill_induction_attempted=False)

def run_asi():
    task_id_list = parse_task_ids(args.task_ids)
    for task_index, tid in enumerate(task_id_list, start=1+args.task_index_offset):
        # step 1: task solving
        cmd = [
            "venv/bin/python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--websites", args.website,
            "--headless"
        ]
        
        # Add MCP config if available
        mcp_config_file = f"config_files/{tid}-mcp-container.json"
        if os.path.exists(mcp_config_file):
            cmd.extend(["--mcp_config", mcp_config_file])
        else:
            regular_config = f"config_files/{tid}.json"
            if os.path.exists(regular_config):
                cmd.extend(["--mcp_config", regular_config])
        
        process = Popen(cmd)
        try:
            stdout, stderr = process.communicate(timeout=300)
            print("Process completed successfully:")
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)
            continue
        # input("[1] Completed task solving")
        path = f"results/webarena.{tid}/summary_info.json"
        if not os.path.exists(path):
            print(f"Warning: {path} not found, skipping task {tid}")
            continue
        
        summary = json.load(open(path, 'r'))
        
        # Check if task should proceed with skill induction
        should_induce = True
        if summary["n_steps"] < 1: 
            print(f"Task {tid} only had {summary['n_steps']} steps (< 1 required), skipping skill induction")
            should_induce = False
        elif summary.get("cum_reward", 0) < 1.0:
            print(f"Task {tid} did not achieve reward >= 1.0 (got {summary.get('cum_reward', 0)}), skipping skill induction")
            should_induce = False
        
        if not should_induce:
            # Generate metrics even for failed tasks (ASI: MCP enabled, ASI enabled but no induction attempted)
            generate_research_metrics(tid, args.website, task_index, asi_enabled=True, mcp_enabled=True, skill_induction_attempted=False)
            continue

        # step 2: eval traj
        # This section introduces a bug where a LLM may decide that a trajectory has failed
        # regardless of if reward was acheived.
        # We have opted to remove this step from the pipeline in favor of validating
        # against ground truth

        # process = Popen([
        #     "python3", "-m", "autoeval.evaluate_trajectory",
        #     "--result_dir", f"results/webarena.{tid}",
        # ])
        # process.wait()
        # path = f"results/webarena.{tid}/claude-3-5-sonnet-20241022_autoeval.json"
        # is_correct = json.load(open(path))[0]["rm"]  # bool
        # if not is_correct: continue
        # input("[2.1] Completed evaluated trajectory (true)")
        
        process = Popen([
            "venv/bin/python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[2.2] Completed clean trajectory")

        # step 3: induce actions
        logger.info(f"[ASI] Starting skill induction for task {tid}...")
        print(f"[ASI] Starting skill induction for task {tid}...")
        process = Popen([
            "venv/bin/python3", "-m", "induce.induce_actions",
            "--website", args.website,
            "--result_id_list", tid,
            "--mcp_enabled", "true",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        induced_skills_count = 0
        induced_skills_names = []
        
        try:
            stdout, stderr = process.communicate(timeout=200)
            output_str = stdout.decode() if isinstance(stdout, bytes) else stdout
            
            if stdout:
                logger.info(f"[ASI] Skill induction output:\n{output_str}")
                print(f"[ASI] Skill induction output:\n{output_str}")
                
                # Parse induced skills from output: "Induced #2|2 Actions, [...] ['skill1', 'skill2']"
                import re
                match = re.search(r'Induced #(\d+)\|\d+ Actions.*?\[(.*?)\]\s*\[(.*?)\]', output_str, re.DOTALL)
                if match:
                    induced_skills_count = int(match.group(1))
                    names_str = match.group(3)
                    if names_str:
                        induced_skills_names = [n.strip().strip("'\"") for n in names_str.split(',') if n.strip()]
                
            if stderr:
                err_str = stderr.decode() if isinstance(stderr, bytes) else stderr
                logger.warning(f"[ASI] Skill induction errors:\n{err_str}")
                print(f"[ASI] Skill induction errors:\n{err_str}")
            
            logger.info(f"[ASI] Skill induction completed for task {tid}")
            print(f"[ASI] Skill induction completed for task {tid}")
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            logger.error(f"[ASI] ERROR: Skill induction timed out after {e.timeout} seconds for task {tid}")
            print(f"[ASI] ERROR: Skill induction timed out after {e.timeout} seconds for task {tid}")
            if stderr:
                err_str = stderr.decode() if isinstance(stderr, bytes) else stderr
                logger.error(f"[ASI] Partial stderr:\n{err_str}")
                print(f"[ASI] Partial stderr:\n{err_str}")
        # input("[3] Completed induced workflow")
        
        # Generate research metrics after task completion (ASI: MCP enabled, ASI enabled with induction)
        generate_research_metrics(
            tid, args.website, task_index, 
            asi_enabled=True, 
            mcp_enabled=True,
            skill_induction_attempted=True,
            induced_skills_count=induced_skills_count,
            induced_skills_names=induced_skills_names
        )

def run_vanilla_asi():
    """Run Vanilla+ASI experiments - ASI enabled without MCP tools"""
    task_id_list = parse_task_ids(args.task_ids)
    for task_index, tid in enumerate(task_id_list, start=1+args.task_index_offset):
        # step 1: task solving
        cmd = [
            "venv/bin/python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--websites", args.website,
            "--headless"
        ]
        
        process = Popen(cmd)
        try:
            stdout, stderr = process.communicate(timeout=300)
            print("Process completed successfully:")
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)
            continue
        # input("[1] Completed task solving")
        path = f"results/webarena.{tid}/summary_info.json"
        if not os.path.exists(path):
            print(f"Warning: {path} not found, skipping task {tid}")
            continue
        
        summary = json.load(open(path, 'r'))
        
        # Check if task should proceed with skill induction
        should_induce = True
        if summary["n_steps"] < 1: 
            print(f"Task {tid} only had {summary['n_steps']} steps (< 1 required), skipping skill induction")
            should_induce = False
        elif summary.get("cum_reward", 0) < 1.0:
            print(f"Task {tid} did not achieve reward >= 1.0 (got {summary.get('cum_reward', 0)}), skipping skill induction")
            should_induce = False
        
        if not should_induce:
            # Generate metrics even for failed tasks (Vanilla+ASI: no MCP, ASI enabled but no induction attempted)
            generate_research_metrics(tid, args.website, task_index, asi_enabled=True, mcp_enabled=False, skill_induction_attempted=False)
            continue

        process = Popen([
            "venv/bin/python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[2.2] Completed clean trajectory")

        # step 3: induce actions
        logger.info(f"[Vanilla+ASI] Starting skill induction for task {tid}...")
        print(f"[Vanilla+ASI] Starting skill induction for task {tid}...")
        process = Popen([
            "venv/bin/python3", "-m", "induce.induce_actions",
            "--website", args.website,
            "--result_id_list", tid,
            "--mcp_enabled", "false",
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        induced_skills_count = 0
        induced_skills_names = []
        
        try:
            stdout, stderr = process.communicate(timeout=200)
            output_str = stdout.decode() if isinstance(stdout, bytes) else stdout
            
            if stdout:
                logger.info(f"[Vanilla+ASI] Skill induction output:\n{output_str}")
                print(f"[Vanilla+ASI] Skill induction output:\n{output_str}")
                
                # Parse induced skills from output: "Induced #2|2 Actions, [...] ['skill1', 'skill2']"
                import re
                match = re.search(r'Induced #(\d+)\|\d+ Actions.*?\[(.*?)\]\s*\[(.*?)\]', output_str, re.DOTALL)
                if match:
                    induced_skills_count = int(match.group(1))
                    names_str = match.group(3)
                    if names_str:
                        induced_skills_names = [n.strip().strip("'\"") for n in names_str.split(',') if n.strip()]
                
            if stderr:
                err_str = stderr.decode() if isinstance(stderr, bytes) else stderr
                logger.warning(f"[Vanilla+ASI] Skill induction errors:\n{err_str}")
                print(f"[Vanilla+ASI] Skill induction errors:\n{err_str}")
            
            logger.info(f"[Vanilla+ASI] Skill induction completed for task {tid}")
            print(f"[Vanilla+ASI] Skill induction completed for task {tid}")
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            logger.error(f"[Vanilla+ASI] ERROR: Skill induction timed out after {e.timeout} seconds for task {tid}")
            print(f"[Vanilla+ASI] ERROR: Skill induction timed out after {e.timeout} seconds for task {tid}")
            if stderr:
                err_str = stderr.decode() if isinstance(stderr, bytes) else stderr
                logger.error(f"[Vanilla+ASI] Partial stderr:\n{err_str}")
                print(f"[Vanilla+ASI] Partial stderr:\n{err_str}")
        # input("[3] Completed induced workflow")
        
        # Generate research metrics after task completion (Vanilla+ASI: no MCP, ASI enabled with induction)
        generate_research_metrics(
            tid, args.website, task_index, 
            asi_enabled=True, 
            mcp_enabled=False,
            skill_induction_attempted=True,
            induced_skills_count=induced_skills_count,
            induced_skills_names=induced_skills_names
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=str, required=True,
                        choices=["vanilla", "vanilla_asi", "mcp", "mcp_asi"],
                        help="vanilla: no MCP, no ASI (control); vanilla_asi: no MCP, ASI only; mcp: MCP only; mcp_asi: MCP + ASI")
    parser.add_argument("--website", type=str, required=True,
                        choices=["shopping"])
    parser.add_argument("--task_ids", type=str, required=True,
                        help="xxx-xxx,xxx-xxx")
    parser.add_argument("--task_index_offset", type=int, default=0,
                        help="Offset for task index (used when running single task in a batch)")

    args = parser.parse_args()

    if args.experiment == "vanilla":
        run_vanilla()
    elif args.experiment == "vanilla_asi":
        run_vanilla_asi()
    elif args.experiment == "mcp":
        run_mcp()
    elif args.experiment == "mcp_asi":
        run_asi()  # rename for clarity

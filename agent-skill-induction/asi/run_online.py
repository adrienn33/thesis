import os
import json
import argparse
import subprocess
from subprocess import Popen
from pathlib import Path

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

# %% Baseline

def run_vanilla():
    task_id_list = parse_task_ids(args.task_ids)

    for tid in task_id_list:
        # step 1: task solving
        cmd = [
            "python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--headless",
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
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)

# %% AWM

def run_awm():
    task_id_list = parse_task_ids(args.task_ids)

    for tid in task_id_list:
        # step 1: task solving
        cmd = [
            "python3", "run_demo.py",
            "--task_name", f"webarena.{tid}",
            "--memory_path", f"workflows/{args.website}.txt",
            "--headless",
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
        process.wait()
        # input("[1] Completed task solving")

        # step 2: eval traj
        process = Popen([
            "python3", "-m", "autoeval.evaluate_trajectory",
            "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()
        path = f"results/webarena.{tid}/claude-3-5-sonnet-20241022_autoeval.json"
        is_correct = json.load(open(path))[0]["rm"]  # bool
        if not is_correct: continue
        # input("[2] Completed evaluated trajectory (true)")

        # step 3: induce workflows
        process = Popen([
            "python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[3.1] Completed clean trajectory")

        process = Popen([
            "python3", "-m", "induce.induce_memory",
            "--website", args.website,
            "--result_id_list", tid,
        ])
        process.wait()  # write to 'workflows/{args.website}.txt'
        # input("[3.2] Completed induced workflow")

        # intermediate supervision
        cont = input("Continue? (y/n)")

# %% ASI
def run_asi():
    task_id_list = parse_task_ids(args.task_ids)
    for tid in task_id_list:
        # step 1: task solving
        cmd = [
            "python3", "run_demo.py",
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
        if summary["n_steps"] < 3: 
            print(f"Task {tid} only had {summary['n_steps']} steps (< 3 required), skipping skill induction")
            continue
        
        # Check if task was successful based on reward
        if summary.get("cum_reward", 0) < 1.0:
            print(f"Task {tid} did not achieve reward >= 1.0 (got {summary.get('cum_reward', 0)}), skipping skill induction")
            continue

        # step 2: eval traj (COMMENTED OUT - evaluator is unreliable)
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
            "python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[2.2] Completed clean trajectory")

        # step 3: induce actions
        print(f"[ASI] Starting skill induction for task {tid}...")
        process = Popen([
            "python3", "-m", "induce.induce_actions",
            "--website", args.website,
            "--result_id_list", tid,
        ])
        try:
            stdout, stderr = process.communicate(timeout=200)
            if stdout:
                print(f"[ASI] Skill induction output:\n{stdout.decode() if isinstance(stdout, bytes) else stdout}")
            if stderr:
                print(f"[ASI] Skill induction errors:\n{stderr.decode() if isinstance(stderr, bytes) else stderr}")
            print(f"[ASI] Skill induction completed for task {tid}")
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"[ASI] ERROR: Skill induction timed out after {e.timeout} seconds for task {tid}")
            if stderr:
                print(f"[ASI] Partial stderr:\n{stderr.decode() if isinstance(stderr, bytes) else stderr}")
        # input("[3] Completed induced workflow")

        # intermediate supervision
        # cont = input("Continue? (y/n)")


# %% Verified, Program
def run_veri_program():
    task_id_list = parse_task_ids(args.task_ids)
    for tid in task_id_list:
        # step 1: task solving with memory input
        cmd = [
            "python3", "run_demo.py", "--headless",
            "--task_name", f"webarena.{tid}",
            "--memory_path", f"workflows/{args.website}.txt",
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
        if json.load(open(path, 'r'))["n_steps"] < 3: continue

        # step 2: eval traj
        process = Popen([
            "python3", "-m", "autoeval.evaluate_trajectory",
            "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()
        path = f"results/webarena.{tid}/claude-3-5-sonnet-20241022_autoeval.json"
        is_correct = json.load(open(path))[0]["rm"]  # bool
        if not is_correct: continue
        # input("[2.1] Completed evaluated trajectory (true)")
        process = Popen([
            "python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[2.2] Completed clean trajectory")

        # step 3: induce actions
        orignal_content = open(f"actions/{args.website}.py", 'r').read()
        process = Popen([
            "python3", "-m", "induce.induce_actions",
            "--website", args.website,
            "--result_id_list", tid,
        ])
        try:
            stdout, stderr = process.communicate(timeout=200)
            print(stdout)
        except subprocess.TimeoutExpired as e:
            process.kill()
            stdout, stderr = process.communicate() # Clean up resources
            print(f"Process timed out after {e.timeout} seconds.")
            print(stderr)
            continue
        updated_content = open(f"actions/{args.website}.py", 'r').read()
        if orignal_content != updated_content:
            new_content = updated_content[len(orignal_content):].strip()
            with open(f"workflows/{args.website}.txt", 'a') as f:
                f.write(new_content + "\n\n")
        # input("[3] Completed induced workflow")

        # intermediate supervision
        # cont = input("Continue? (y/n)")

# %% Memory-Augmented ASI

def run_mem_asi():
    task_id_list = parse_task_ids(args.task_ids)
    for tid in task_id_list:
        # step 1: task solving
        cmd = [
            "python3", "run_demo.py",
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
        if json.load(open(path, 'r'))["n_steps"] < 3: continue

        # step 2: eval traj
        process = Popen([
            "python3", "-m", "autoeval.evaluate_trajectory",
            "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()
        path = f"results/webarena.{tid}/claude-3-5-sonnet-20241022_autoeval.json"
        is_correct = json.load(open(path))[0]["rm"]  # bool
        if not is_correct: continue
        # input("[2.1] Completed evaluated trajectory (true)")
        process = Popen([
            "python3", "-m", "results.calc_valid_steps",
            "--clean_and_store", "--result_dir", f"results/webarena.{tid}",
        ])
        process.wait()  # output 'clean_steps.json'
        # input("[2.2] Completed clean trajectory")

        # step 3: induce actions
        nlines = len(open(f"actions/{args.website}.py", 'r').readlines())
        process = Popen([
            "python3", "-m", "induce.induce_actions",
            "--website", args.website,
            "--result_id_list", tid,
        ])
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
        input("[3] Completed induced actions")

        # step 4: induce memory
        new_nlines = len(open(f"actions/{args.website}.py", 'r').readlines())
        if new_nlines == nlines: continue
        if new_nlines == nlines: task_abbr = tid
        else: task_abbr = f"{tid}_test"

        output_path = f"results/webarena.{task_abbr}/cleaned_steps.json"
        if not os.path.exists(output_path):
            process = Popen([
                "python3", "-m", "results.calc_valid_steps",
                "--clean_and_store",
                "--result_dir", f"results/webarena.{task_abbr}",
            ])
            process.wait()  # output 'clean_steps.json'
            # input("[4.1] Completed clean trajectory")
        process = Popen([
            "python3", "-m", "induce.induce_memory",
            "--website", args.website,
            "--result_id_list", task_abbr,
        ])
        process.wait()
        input("[4.2] Completed induce memory")

        # intermediate supervision
        cont = input("Continue? (y/n)")


# %% Main Pipeline

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", type=str, required=True,
                        choices=["vanilla", "awm", "asi", "mem_asi", "veri_program", "veri_text"])
    parser.add_argument("--website", type=str, required=True,
                        choices=["shopping", "admin", "reddit", "gitlab", "map"])
    parser.add_argument("--task_ids", type=str, required=True,
                        help="xxx-xxx,xxx-xxx")

    args = parser.parse_args()

    if args.experiment == "vanilla":
        run_vanilla()
    elif args.experiment == "awm":
        run_awm()
    elif args.experiment == "asi":
        run_asi()
    elif args.experiment == "mem_asi":
        run_mem_asi()

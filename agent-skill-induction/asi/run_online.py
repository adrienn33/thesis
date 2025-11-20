import os
import json
import argparse
import subprocess
from subprocess import Popen
from pathlib import Path

def generate_research_metrics(task_id: str, experiment_type: str, website: str):
    """Generate research_metrics.json from existing summary_info.json"""
    result_dir = f"results/webarena.{task_id}"
    summary_path = f"{result_dir}/summary_info.json"
    
    if not os.path.exists(summary_path):
        print(f"Warning: {summary_path} not found, skipping metrics generation")
        return
    
    summary = json.load(open(summary_path, 'r'))
    
    mcp_config_exists = os.path.exists(f"config_files/{task_id}-mcp-container.json")
    
    strategy = _determine_strategy(result_dir)
    mcp_connected = _check_mcp_connected(result_dir)
    mcp_calls = _check_mcp_calls(result_dir)
    browser_actions = _check_browser_actions(result_dir)
    skill_induction = _check_skill_induction(result_dir)
    skill_details = _extract_skill_details(result_dir, website)
    
    research_metrics = {
        "task_id": task_id,
        "experiment_type": experiment_type,
        "website": website,
        "mcp_enabled": mcp_config_exists,
        "mcp_connected": mcp_connected,
        "mcp_calls": mcp_calls,
        "browser_actions": browser_actions,
        "skill_induction": skill_induction,
        "skills_induced_count": skill_details["skills_induced_count"],
        "skills_induced_names": skill_details["skills_induced_names"],
        "skills_reused_count": skill_details["skills_reused_count"],
        "skills_reused_names": skill_details["skills_reused_names"],
        "strategy": strategy,
        
        "task_execution": {
            "success": summary.get("cum_reward", 0) >= 1.0,
            "reward": summary.get("cum_reward", 0),
            "steps": summary.get("n_steps", 0),
            "total_steps": summary.get("stats.cum_steps", 0),
            "elapsed_time": summary.get("stats.cum_step_elapsed", 0),
            "agent_elapsed_time": summary.get("stats.cum_agent_elapsed", 0),
            "terminated": summary.get("terminated", False),
            "truncated": summary.get("truncated", False),
            "error": summary.get("err_msg", None)
        }
    }
    
    output_path = f"{result_dir}/research_metrics.json"
    with open(output_path, 'w') as f:
        json.dump(research_metrics, f, indent=2)
    
    print(f"[Metrics] Generated {output_path}")

def _determine_strategy(result_dir: str) -> str:
    """Determine strategy based on action types in cleaned_steps.json or raw_output.txt"""
    cleaned_steps_path = f"{result_dir}/cleaned_steps.json"
    raw_output_path = f"{result_dir}/raw_output.txt"
    
    content = None
    
    if os.path.exists(cleaned_steps_path):
        with open(cleaned_steps_path) as f:
            steps = json.load(f)
            content = " ".join(steps)
    elif os.path.exists(raw_output_path):
        with open(raw_output_path) as f:
            content = f.read()
    else:
        return "unknown"
    
    has_mcp = False
    has_browser = False
    content_lower = content.lower()
    
    if 'magento_' in content or '_server_' in content:
        has_mcp = True
    
    browser_keywords = ['click(', 'fill(', 'goto(', 'scroll(', 'type(', 
                       'press(', 'select(', 'hover(', 'check(']
    if any(keyword in content_lower for keyword in browser_keywords):
        has_browser = True
    
    if has_mcp and has_browser:
        return "hybrid"
    elif has_mcp:
        return "mcp"
    elif has_browser:
        return "browser"
    else:
        return "unknown"

def _check_mcp_connected(result_dir: str) -> bool:
    """Check if MCP server successfully connected by looking for connection message"""
    raw_output_path = f"{result_dir}/raw_output.txt"
    
    if not os.path.exists(raw_output_path):
        return False
    
    with open(raw_output_path) as f:
        content = f.read()
    
    return "Connected to MCP server" in content

def _check_mcp_calls(result_dir: str) -> bool:
    """Check if MCP tools were actually called during execution"""
    cleaned_steps_path = f"{result_dir}/cleaned_steps.json"
    raw_output_path = f"{result_dir}/raw_output.txt"
    
    content = None
    
    if os.path.exists(cleaned_steps_path):
        with open(cleaned_steps_path) as f:
            steps = json.load(f)
            content = " ".join(steps)
    elif os.path.exists(raw_output_path):
        with open(raw_output_path) as f:
            content = f.read()
    else:
        return False
    
    return 'magento_' in content or '_server_' in content

def _check_browser_actions(result_dir: str) -> bool:
    """Check if browser actions were used during execution"""
    cleaned_steps_path = f"{result_dir}/cleaned_steps.json"
    raw_output_path = f"{result_dir}/raw_output.txt"
    
    content = None
    
    if os.path.exists(cleaned_steps_path):
        with open(cleaned_steps_path) as f:
            steps = json.load(f)
            content = " ".join(steps)
    elif os.path.exists(raw_output_path):
        with open(raw_output_path) as f:
            content = f.read()
    else:
        return False
    
    content_lower = content.lower()
    browser_keywords = ['click(', 'fill(', 'goto(', 'scroll(', 'type(', 
                       'press(', 'select(', 'hover(', 'check(']
    
    return any(keyword in content_lower for keyword in browser_keywords)

def _check_skill_induction(result_dir: str) -> bool:
    """Check if skill induction was attempted by looking for start message"""
    raw_output_path = f"{result_dir}/raw_output.txt"
    
    if not os.path.exists(raw_output_path):
        return False
    
    with open(raw_output_path) as f:
        content = f.read()
    
    return "Starting skill induction for task" in content

def _extract_skill_details(result_dir: str, website: str) -> dict:
    """Extract detailed skill information including counts and names"""
    import re
    
    skill_details = {
        "skills_induced_count": 0,
        "skills_induced_names": [],
        "skills_reused_count": 0,
        "skills_reused_names": []
    }
    
    raw_output_path = f"{result_dir}/raw_output.txt"
    actions_file = f"actions/{website}.py"
    
    if not os.path.exists(raw_output_path):
        return skill_details
    
    with open(raw_output_path) as f:
        content = f.read()
    
    induced_match = re.search(r'Induced #(\d+)\|(\d+) Actions.*?\[(.*?)\].*?\[(.*?)\]', content, re.DOTALL)
    if induced_match:
        skill_details["skills_induced_count"] = int(induced_match.group(1))
        names_str = induced_match.group(4)
        if names_str:
            skill_details["skills_induced_names"] = [n.strip().strip("'\"") for n in names_str.split(',') if n.strip()]
    
    if os.path.exists(actions_file):
        with open(actions_file) as f:
            actions_content = f.read()
        
        function_pattern = r'def\s+(\w+)\s*\('
        all_defined_functions = re.findall(function_pattern, actions_content)
        all_defined_functions = [f for f in all_defined_functions if f not in ['main', '__init__']]
        
        cleaned_steps_path = f"{result_dir}/cleaned_steps.json"
        raw_output_available = os.path.exists(raw_output_path)
        
        trajectory_text = ""
        if os.path.exists(cleaned_steps_path):
            with open(cleaned_steps_path) as f:
                steps = json.load(f)
            trajectory_text = " ".join(steps)
        elif raw_output_available:
            trajectory_text = content
        
        if trajectory_text:
            reused_functions = []
            for func_name in all_defined_functions:
                func_call_pattern = func_name + r'\s*\('
                if re.search(func_call_pattern, trajectory_text):
                    reused_functions.append(func_name)
            
            skill_details["skills_reused_count"] = len(reused_functions)
            skill_details["skills_reused_names"] = reused_functions
    
    return skill_details

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
        if summary["n_steps"] < 1: 
            print(f"Task {tid} only had {summary['n_steps']} steps (< 1 required), skipping skill induction")
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
        
        # Generate research metrics after task completion
        generate_research_metrics(tid, "asi", args.website)

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
        if json.load(open(path, 'r'))["n_steps"] < 1: continue

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
        if json.load(open(path, 'r'))["n_steps"] < 1: continue

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

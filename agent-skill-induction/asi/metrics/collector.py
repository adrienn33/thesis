import os
import json
import re
import time
from datetime import datetime

def generate_research_metrics(
    task_id: str, 
    website: str, 
    task_index: int = 1, 
    asi_enabled: bool = False, 
    mcp_enabled: bool = None,
    skill_induction_attempted: bool = False,
    induced_skills_count: int = 0,
    induced_skills_names: list = None
):
    """Generate research_metrics.json from existing summary_info.json
    
    Args:
        task_id: Task ID (e.g., "22")
        website: Website name (e.g., "shopping")
        task_index: Index of this task in a batch run (1-indexed, default=1)
        asi_enabled: Whether ASI (Agent Skill Induction) was enabled for this run
        mcp_enabled: Whether MCP was enabled for this run (None = auto-detect from config file)
        skill_induction_attempted: Whether skill induction subprocess was actually run for this task
        induced_skills_count: Number of skills induced in this run (0 if none)
        induced_skills_names: List of skill names induced in this run (empty list if none)
    """
    if induced_skills_names is None:
        induced_skills_names = []
    result_dir = f"results/webarena.{task_id}"
    summary_path = f"{result_dir}/summary_info.json"
    
    if not os.path.exists(summary_path):
        print(f"Warning: {summary_path} not found, skipping metrics generation")
        return
    
    summary = json.load(open(summary_path, 'r'))
    
    # Determine MCP status: use explicit parameter if provided, otherwise auto-detect
    if mcp_enabled is None:
        mcp_config_exists = os.path.exists(f"config_files/{task_id}-mcp-container.json")
    else:
        mcp_config_exists = mcp_enabled
    
    mcp_connected = _check_mcp_connected(result_dir)
    mcp_calls = _check_mcp_calls(result_dir)
    browser_actions = _check_browser_actions(result_dir)
    
    # Get list of skills available when this task ran (before any induction)
    available_skills = _get_available_skills(website, induced_skills_names)
    
    # Get reused skill information from trajectory analysis
    # Pass newly induced skills so we can exclude them (they didn't exist during the run)
    reused_skills = _get_reused_skills(result_dir, website, induced_skills_names)
    
    action_counts = _count_actions(result_dir, website)
    library_stats = _track_skill_library(result_dir, website, induced_skills_names)
    skills_used = _track_skill_usage(result_dir, website)
    
    configuration = _determine_configuration(mcp_config_exists, asi_enabled)
    
    research_metrics = {
        "task_index": task_index,
        "task_id": task_id,
        "website": website,
        "generated_at": datetime.now().isoformat(),
        
        "configuration": {
            "name": configuration,
            "mcp_enabled": mcp_config_exists,
            "asi_enabled": asi_enabled
        },
        
        "mcp_connected": mcp_connected,
        "mcp_calls": mcp_calls,
        "browser_actions": browser_actions,
        
        "available_skills": available_skills,
        "skill_induction": skill_induction_attempted,
        "skills_induced_count": induced_skills_count,
        "skills_induced_names": induced_skills_names,
        "skills_reused_count": reused_skills["count"],
        "skills_reused_names": reused_skills["names"],
        
        "browser_action_count": action_counts["browser_action_count"],
        "mcp_call_count": action_counts["mcp_call_count"],
        "skill_call_count": action_counts["skill_call_count"],
        
        "skill_library_size_before": library_stats["size_before"],
        "skill_library_size_after": library_stats["size_after"],
        
        "skills_used": skills_used,
        
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
        },
        
        "token_usage": {
            "input_tokens": {
                "last_action": summary.get("stats.cum_n_token_last_action", 0),
                "last_action_error": summary.get("stats.cum_n_token_last_action_error", 0),
                "last_action_output": summary.get("stats.cum_n_token_last_action_output", 0),
                "axtree": summary.get("stats.cum_n_token_axtree_txt", 0),
                "html": summary.get("stats.cum_n_token_pruned_html", 0)
            },
            "total_input_tokens": (
                summary.get("stats.cum_n_token_last_action", 0) +
                summary.get("stats.cum_n_token_last_action_error", 0) +
                summary.get("stats.cum_n_token_last_action_output", 0) +
                summary.get("stats.cum_n_token_axtree_txt", 0) +
                summary.get("stats.cum_n_token_pruned_html", 0)
            )
        }
    }
    
    output_path = f"{result_dir}/research_metrics.json"
    with open(output_path, 'w') as f:
        json.dump(research_metrics, f, indent=2)
    
    print(f"[Metrics] Generated {output_path}")

def _get_available_skills(website: str, newly_induced_skills: list = None) -> list:
    """Get list of skills that were available when this task ran
    
    This represents the skills that existed BEFORE this run, excluding any newly induced ones.
    
    Args:
        website: Website name
        newly_induced_skills: List of skills just induced in this run (to exclude)
    """
    if newly_induced_skills is None:
        newly_induced_skills = []
    
    actions_file = f"actions/{website}.py"
    if not os.path.exists(actions_file):
        return []
    
    with open(actions_file) as f:
        actions_content = f.read()
    
    function_pattern = r'def\s+(\w+)\s*\('
    all_functions = re.findall(function_pattern, actions_content)
    all_functions = [f for f in all_functions if f not in ['main', '__init__']]
    
    # Exclude newly induced skills - they didn't exist when this task ran
    available_at_runtime = [f for f in all_functions if f not in newly_induced_skills]
    
    return sorted(available_at_runtime)

def _check_mcp_connected(result_dir: str) -> list:
    """Extract MCP server connection details from log output
    
    Returns list of dicts with server name and tool count:
    [{'name': 'magento-review-server', 'tool_count': 2}, ...]
    """
    # Try experiment.log first (always available), then raw_output.txt as fallback
    log_paths = [
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    content = None
    for log_path in log_paths:
        if os.path.exists(log_path):
            with open(log_path) as f:
                content = f.read()
            break
    
    if not content:
        return []
    
    servers = []
    pattern = r'Connected to MCP server (\S+) with (\d+) tools'
    matches = re.findall(pattern, content)
    
    for server_name, tool_count in matches:
        servers.append({
            'name': server_name,
            'tool_count': int(tool_count)
        })
    
    return servers

def _check_mcp_calls(result_dir: str) -> bool:
    """Check if MCP tools were actually called during execution"""
    # Check multiple sources for MCP tool calls
    log_paths = [
        f"{result_dir}/cleaned_steps.json",
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        if log_path.endswith('.json'):
            with open(log_path) as f:
                steps = json.load(f)
                content = " ".join(steps)
        else:
            with open(log_path) as f:
                content = f.read()
        
        # Check for MCP tool call patterns
        if '_call_mcp_tool called' in content or 'magento_' in content or '_server_' in content:
            return True
    
    return False

def _check_browser_actions(result_dir: str) -> bool:
    """Check if browser actions were used during execution"""
    # Check multiple sources for browser actions
    log_paths = [
        f"{result_dir}/cleaned_steps.json",
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    browser_keywords = ['click(', 'fill(', 'goto(', 'scroll(', 'type(', 
                       'press(', 'select(', 'hover(', 'check(']
    
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        if log_path.endswith('.json'):
            with open(log_path) as f:
                steps = json.load(f)
                content = " ".join(steps)
        else:
            with open(log_path) as f:
                content = f.read()
        
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in browser_keywords):
            return True
    
    return False

def _check_skill_induction(result_dir: str) -> bool:
    """Check if skill induction was attempted by looking for start message"""
    # Check multiple sources for skill induction messages
    log_paths = [
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        with open(log_path) as f:
            content = f.read()
        
        if "Starting skill induction for task" in content:
            return True
    
    return False

def _determine_configuration(mcp_enabled: bool, asi_enabled: bool) -> str:
    """Determine configuration name based on MCP and ASI status
    
    Vanilla:      MCP -> Disabled, ASI -> Disabled
    MCP:          MCP -> Enabled,  ASI -> Disabled  
    Vanilla+ASI:  MCP -> Disabled, ASI -> Enabled
    MCP+ASI:      MCP -> Enabled,  ASI -> Enabled
    """
    if mcp_enabled and asi_enabled:
        return "MCP+ASI"
    elif mcp_enabled and not asi_enabled:
        return "MCP"
    elif not mcp_enabled and asi_enabled:
        return "Vanilla+ASI"
    else:
        return "Vanilla"

def _track_skill_usage(result_dir: str, website: str) -> list:
    """Track which skills were used and how many times each was called"""
    log_paths = [
        f"{result_dir}/cleaned_steps.json",
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    actions_file = f"actions/{website}.py"
    
    trajectory_text = ""
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        if log_path.endswith('.json'):
            with open(log_path) as f:
                steps = json.load(f)
            trajectory_text = " ".join(steps)
        else:
            with open(log_path) as f:
                trajectory_text = f.read()
        break
    
    if not trajectory_text:
        return []
    
    if not os.path.exists(actions_file):
        return []
    
    with open(actions_file) as f:
        actions_content = f.read()
    
    function_pattern = r'def\s+(\w+)\s*\('
    all_defined_functions = re.findall(function_pattern, actions_content)
    all_defined_functions = [f for f in all_defined_functions if f not in ['main', '__init__']]
    
    skills_used = []
    for func_name in all_defined_functions:
        func_call_pattern = func_name + r'\s*\('
        call_count = len(re.findall(func_call_pattern, trajectory_text))
        
        if call_count > 0:
            skills_used.append({
                "name": func_name,
                "calls": call_count
            })
    
    skills_used.sort(key=lambda x: x["calls"], reverse=True)
    
    return skills_used

def _track_skill_library(result_dir: str, website: str, newly_induced_skills: list) -> dict:
    """Track skill library size before/after task execution
    
    The library size is determined by counting functions in actions/{website}.py.
    For tasks that induce skills, we need to determine the "before" state by 
    subtracting the newly induced skills from the current library.
    """
    actions_file = f"actions/{website}.py"
    
    if not os.path.exists(actions_file):
        return {
            "size_before": 0,
            "size_after": 0
        }
    
    with open(actions_file) as f:
        actions_content = f.read()
    
    function_pattern = r'def\s+(\w+)\s*\('
    all_functions = re.findall(function_pattern, actions_content)
    all_functions = [f for f in all_functions if f not in ['main', '__init__']]
    
    current_library_size = len(all_functions)
    num_newly_induced = len(newly_induced_skills)
    
    size_before = current_library_size - num_newly_induced
    size_after = current_library_size
    
    return {
        "size_before": size_before,
        "size_after": size_after
    }

def _count_actions(result_dir: str, website: str) -> dict:
    """Count browser actions, MCP calls, and skill calls in the trajectory"""
    counts = {
        "browser_action_count": 0,
        "mcp_call_count": 0,
        "skill_call_count": 0
    }
    
    log_paths = [
        f"{result_dir}/cleaned_steps.json",
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    trajectory_text = ""
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        if log_path.endswith('.json'):
            with open(log_path) as f:
                steps = json.load(f)
            trajectory_text = " ".join(steps)
        else:
            with open(log_path) as f:
                trajectory_text = f.read()
        break
    
    if not trajectory_text:
        return counts
    
    browser_keywords = [r'click\(', r'fill\(', r'goto\(', r'scroll\(', r'type\(', 
                       r'press\(', r'select\(', r'hover\(', r'check\(']
    for keyword in browser_keywords:
        counts["browser_action_count"] += len(re.findall(keyword, trajectory_text, re.IGNORECASE))
    
    mcp_pattern = r'magento_\w+_server_\w+\('
    counts["mcp_call_count"] = len(re.findall(mcp_pattern, trajectory_text))
    
    actions_file = f"actions/{website}.py"
    if os.path.exists(actions_file):
        with open(actions_file) as f:
            actions_content = f.read()
        
        function_pattern = r'def\s+(\w+)\s*\('
        all_defined_functions = re.findall(function_pattern, actions_content)
        all_defined_functions = [f for f in all_defined_functions if f not in ['main', '__init__']]
        
        for func_name in all_defined_functions:
            func_call_pattern = func_name + r'\s*\('
            counts["skill_call_count"] += len(re.findall(func_call_pattern, trajectory_text))
    
    return counts

def _get_reused_skills(result_dir: str, website: str, newly_induced_skills: list = None) -> dict:
    """Get skills that were already in library and used in this trajectory
    
    Args:
        result_dir: Result directory path
        website: Website name
        newly_induced_skills: List of skills just induced in this run (to exclude from reused)
    """
    if newly_induced_skills is None:
        newly_induced_skills = []
        
    reused = {"count": 0, "names": []}
    
    actions_file = f"actions/{website}.py"
    if not os.path.exists(actions_file):
        return reused
    
    with open(actions_file) as f:
        actions_content = f.read()
    
    function_pattern = r'def\s+(\w+)\s*\('
    all_defined_functions = re.findall(function_pattern, actions_content)
    all_defined_functions = [f for f in all_defined_functions if f not in ['main', '__init__']]
    
    # Exclude newly induced skills - they didn't exist when trajectory ran
    pre_existing_functions = [f for f in all_defined_functions if f not in newly_induced_skills]
    
    # Get trajectory text from various sources
    log_paths = [
        f"{result_dir}/cleaned_steps.json",
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    trajectory_text = ""
    for log_path in log_paths:
        if not os.path.exists(log_path):
            continue
            
        if log_path.endswith('.json'):
            with open(log_path) as f:
                steps = json.load(f)
            trajectory_text = " ".join(steps)
        else:
            with open(log_path) as f:
                trajectory_text = f.read()
        break
    
    if trajectory_text:
        reused_functions = []
        for func_name in pre_existing_functions:
            func_call_pattern = func_name + r'\s*\('
            if re.search(func_call_pattern, trajectory_text):
                reused_functions.append(func_name)
        
        reused["count"] = len(reused_functions)
        reused["names"] = reused_functions
    
    return reused

def _extract_skill_details(result_dir: str, website: str) -> dict:
    """Extract detailed skill information including counts and names"""
    skill_details = {
        "skills_induced_count": 0,
        "skills_induced_names": [],
        "skills_reused_count": 0,
        "skills_reused_names": []
    }
    
    # Try experiment.log first, then raw_output.txt
    log_paths = [
        f"{result_dir}/experiment.log",
        f"{result_dir}/raw_output.txt"
    ]
    
    content = None
    for log_path in log_paths:
        if os.path.exists(log_path):
            with open(log_path) as f:
                content = f.read()
            break
    
    if not content:
        return skill_details
    
    actions_file = f"actions/{website}.py"
    
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
        
        trajectory_text = ""
        if os.path.exists(cleaned_steps_path):
            with open(cleaned_steps_path) as f:
                steps = json.load(f)
            trajectory_text = " ".join(steps)
        elif content:
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

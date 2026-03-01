"""Induce Actions on the Full Task Level."""

import os
import gzip
import json
import pickle
import anthropic
import argparse
import subprocess
from induce.utils import (
    extract_code_pieces, get_task_id, get_result_dirs,
    get_output_dir
)

# %% Induce Actions

def get_example_query_filtered(index: int, result_dir: str, config_dir: str) -> tuple[str, str]:
    """Get the string for a past example experience, without invalid actions."""
    cid = get_task_id(result_dir)
    config_path = os.path.join(config_dir, f"{cid}.json")
    config = json.load(open(config_path))
    instruction = config["intent"]
    task = config["intent_template"]

    step_dirs = [f for f in os.listdir(result_dir) if f.startswith("step") and f.endswith(".pkl.gz")]
    step_dirs = sorted(step_dirs, key=lambda x: int(x.split('.')[0].split('_')[1]))
    step_dirs = [os.path.join(result_dir, sd) for sd in step_dirs]
    steps = []
    for sd in step_dirs:
        step_info = pickle.load(gzip.open(sd, 'rb'))
        error_msg = step_info.obs["last_action_error"]
        if len(error_msg) > 0 and (not error_msg.startswith("TimeoutError")):
            continue  # skip error actions
        if len(step_info.obs["last_action"]) == 0:
            continue  # skip empty actions
        steps.append(step_info.obs["last_action"])

    if len(steps) > 0:
        print(f"Collected #{len(steps)} valid steps from a total of #{len(step_dirs)} steps.")
        steps = '\n'.join(steps)
        ex = f"### Example {index} ({config['task_id']}): {instruction}\n{steps}"
    else:
        ex = None
    return ex, task


def get_example_query_cleaned(index: int, result_dir: str, config_dir: str) -> str:
    """Get the string for a past example experience, without invalid actions."""
    # get config
    cid = get_task_id(result_dir)
    config_path = os.path.join(config_dir, f"{cid}.json")
    config = json.load(open(config_path))

    # get instruction
    subtask_inst_path = os.path.join(result_dir, "instruction.txt")
    if os.path.exists(subtask_inst_path):  # sub task
        instruction = open(subtask_inst_path, 'r').read()
        task = instruction
    else:  # full task
        instruction = config["intent"]
        task = config["intent_template"]

    steps = json.load(open(os.path.join(result_dir, "cleaned_steps.json")))
    if len(steps) > 0:
        print(f"Collected #{len(steps)} valid steps.")
        steps = '\n'.join(steps)
        ex = f"### Example {index} ({config['task_id']}): {instruction}\n{steps}"
    else:
        ex = None

    return ex, task

def get_test_query(result_dir_list: str, config_dir: str) -> str:
    """Transform past examples into a test query."""
    task = None
    examples = []
    for rdir in result_dir_list:
        ex, task = get_example_query_cleaned(len(examples)+1, rdir, config_dir)
        if ex is None: continue
        examples.append(ex)
    
    if len(examples) < 1:
        return None
    query = f"## Task: {task}\n" + '\n\n'.join(examples)
    return query


def induce_actions() -> list[str] | None:
    print(f"[INDUCE] Starting action induction...")
    result_dir_list = get_result_dirs(args.results_dir, args.result_id_list, args.template_id, args.config_dir)
    print(f"[INDUCE] Found {len(result_dir_list)} result directories: {result_dir_list}")
    test_query = get_test_query(result_dir_list, args.config_dir)
    if test_query is None:
        print(f"[INDUCE] ERROR: test_query is None, returning empty list")
        return []
    print(f"[INDUCE] Generated test query ({len(test_query)} chars)")
    with open(args.test_query_path, 'w') as fw: fw.write(test_query)

    # Extract existing function names and signatures to show the model
    existing_code = open(args.write_action_path).read()
    existing_signatures = []
    existing_names = []
    
    for line in existing_code.split('\n'):
        if line.strip().startswith('def '):
            existing_signatures.append(line.strip())
            # Extract just the function name
            import re
            name_match = re.search(r'def\s+(\w+)\s*\(', line.strip())
            if name_match:
                existing_names.append(name_match.group(1))
    
    # Remove duplicates from names list
    unique_existing_names = sorted(list(set(existing_names)))
    
    existing_funcs_summary = '\n'.join(existing_signatures) if existing_signatures else "None"
    existing_names_list = ', '.join(unique_existing_names) if unique_existing_names else "None"
    
    # Use explicit MCP enablement argument
    is_mcp_enabled = args.mcp_enabled
    
    # Choose appropriate instruction file based on MCP availability
    if is_mcp_enabled:
        if 'instruction.txt' in args.instruction_path:
            instruction_path = args.instruction_path.replace('instruction.txt', 'instruction_mcp.txt')
        else:
            instruction_path = args.instruction_path  # Assume explicitly specified
    else:
        if 'instruction.txt' in args.instruction_path:
            instruction_path = args.instruction_path.replace('instruction.txt', 'instruction_vanilla.txt')
        else:
            instruction_path = args.instruction_path  # Assume explicitly specified
    
    print(f"[INDUCE] Using instruction file: {instruction_path} (MCP enabled: {is_mcp_enabled})")
    
    messages = [{"role": "system", "content": open(args.sys_msg_path).read()}]
    messages += [{"role": "user", "content": open(instruction_path).read()}]
    messages += [{"role": "user", "content": open(args.few_shot_path).read()}]
    messages += [{"role": "user", "content": f"""## ⚠️ CRITICAL: EXISTING SKILLS - DO NOT DUPLICATE

The following skills have ALREADY been learned and implemented. You MUST NOT create new functions with these names or similar functionality.

**EXISTING SKILL NAMES (FORBIDDEN TO RECREATE):**
{existing_names_list}

**Existing Function Signatures:**
```python
{existing_funcs_summary}
```

🚨 **IMPORTANT RULES:**
1. You MUST ONLY propose NEW skills that don't already exist
2. Check the existing names list above - if a skill name already exists, DO NOT recreate it
3. Look for similar functionality in existing skills - don't duplicate similar behavior with different names
4. Focus on identifying genuinely NOVEL patterns that aren't covered by existing skills

✅ **WHAT TO DO:**
- Only propose skills that solve completely new problems not addressed by existing skills
- Use descriptive names that are clearly different from existing ones
- If you cannot identify novel skills, it's better to propose NO new skills than duplicate existing ones"""}]
    messages += [{"role": "user", "content": test_query + '\n\n## Reusable Functions'}]

    all_responses = []
    import time
    import random

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    system_msg = next((msg["content"] for msg in messages if msg["role"] == "system"), "")
    user_messages = [msg for msg in messages if msg["role"] == "user"]

    for i in range(args.num_responses):
        max_retries = 3
        base_delay = 30

        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=args.model,
                    max_tokens=4096,
                    temperature=args.temperature,
                    system=system_msg,
                    messages=user_messages,
                )
                curr_resp = response.content[0].text
                break  # Success, exit retry loop

            except anthropic.RateLimitError as e:
                if attempt < max_retries - 1:
                    delay = base_delay + random.uniform(0, 10)
                    print(f"Rate limit hit, waiting {delay:.1f} seconds before retry {attempt + 2}/{max_retries}")
                    time.sleep(delay)
                else:
                    print(f"Rate limit error after {max_retries} attempts: {e}")
                    curr_resp = ""
                    break

            except Exception as e:
                print(f"Error calling Anthropic API: {e}")
                curr_resp = ""
                break

        curr_path = os.path.join(args.output_dir, f"{i}.md")
        with open(curr_path, 'w') as fw:
            fw.write(test_query + '\n\n\n' + curr_resp)
        all_responses.append(curr_resp)
    print(f"[INDUCE] Generated {len(all_responses)} responses")
    for i, resp in enumerate(all_responses):
        print(f"[INDUCE] Response {i}: {len(resp)} chars")
    return all_responses



# %% Process Actions
from induce.utils import count_function_calls, get_function_names

def write_actions(response: str) -> tuple[str, list[str]]:
    """Extract actions from response and write actions to agent action loading file."""
    existing_action_names = get_function_names(open(args.write_action_path, 'r').read())
    # extract induced actions from the response
    actions = extract_code_pieces(response, start="```python", end="```", do_split=False)
    actions = [a for a in actions if "def " in a and count_function_calls(a, 1)]
    new_actions, action_names = [], []
    duplicates_found = []
    
    for a in actions:
        if ("def " in a) and count_function_calls(a, 1):
            all_names_in_action = get_function_names(a, [])
            
            existing_conflicts = [name for name in all_names_in_action if name in existing_action_names]
            if existing_conflicts:
                duplicates_found.extend(existing_conflicts)
                print(f"BLOCKED: Function(s) {existing_conflicts} already exist in file - Rejecting entire action")
                print(f"   Action was: {a.split('def ')[1].split('(')[0] if 'def ' in a else 'unknown'}")
                continue
            
            within_response_conflicts = [name for name in all_names_in_action if name in action_names]  
            if within_response_conflicts:
                duplicates_found.extend(within_response_conflicts)
                print(f"BLOCKED: Function(s) {within_response_conflicts} already proposed in this response - Rejecting")
                continue
                
            action_names.extend(all_names_in_action)
            new_actions.append(a)
            print(f"ACCEPTED: New skill(s) {all_names_in_action}")

    if duplicates_found:
        print(f"\n❌ REJECTED {len(duplicates_found)} duplicate function(s): {duplicates_found}")
        print(f"   These functions already exist in {args.write_action_path}")
    
    print(
        f"Induced #{len(new_actions)}|{len(action_names)} Actions, ",
        [a.split("\n")[0] for a in new_actions],
        action_names
    )
    # cont = input("Continue? (y/n): ")  # Commented out for non-interactive execution
    if len(new_actions) == 0: return None, None

    tmp_path = args.write_action_path + ".tmp"
    process = subprocess.Popen(["cp", args.write_action_path, tmp_path])
    process.wait()

    with open(args.write_action_path, 'a+') as fw:
        fw.write('\n\n'+ '\n\n'.join(new_actions))
    return tmp_path, action_names



# %% Run Tests
from induce.utils import parse_tests

def write_tests(response: str, result_id_list: list[str], action_names: list[str] = [], is_mcp_enabled: bool = False) -> bool:
    """Extract tests, write tests to file, and run tests.
    Args:
        response: model generated response including induced actions, tests, and texts.
        result_id_list: list of task result IDs.
        action_names: list of names of the induced actions to test on.
    Returns:
        bool: If all tests passed the check.
    """
    tests = parse_tests(response, action_names)
    if len(tests) != len(result_id_list):
        print(f"Warning: Got #{len(tests)} tests but for #{len(result_id_list)} results. Using last {len(result_id_list)} tests.")
        tests = tests[-len(result_id_list):]  # Take the last N tests
    
    # write tests and script
    script_content = []
    for i, (t, r) in enumerate(zip(tests, result_id_list)):
        # write test trajectory
        test_path = os.path.join(args.write_tests_dir, f"test_{i}.txt")
        test_str = '\n'.join([f"```{tl.strip()}```" for tl in t.split('\n') if tl.strip()])
        with open(test_path, 'w') as fw:  # overwrite existing content
            fw.write(test_str)
        
        # write test script
        script_content.append(f"# Run test for task {r}")
        task_id = r.split('_')[0]
        # Use original config based on MCP enablement
        if is_mcp_enabled:
            config_file = f"config_files/{task_id}-mcp-container.json"
        else:
            config_file = f"config_files/{task_id}.json"
        script_content.append(
            # f"python run_demo.py --websites {args.website} --headless "
            f"python run_demo.py --websites {args.website} --headless "
            f"--task_name webarena.{task_id} "
            f"--action_path {test_path} "
            f"--mcp_config {config_file} "
            f"--rename_to webarena.{task_id}_test",
        )
        script_content.append("\n")
    
    test_script_path = os.path.join(args.write_tests_dir, "run_tests.sh")
    with open(test_script_path, 'w') as fw:
        fw.write('\n'.join(script_content))
    
    # run all tests
    process = subprocess.Popen(["bash", test_script_path])
    try:
        stdout, stderr = process.communicate(timeout=1000)
        print(stdout)
    except subprocess.TimeoutExpired as e:
        process.kill()
        stdout, stderr = process.communicate() # Clean up resources
        print(f"Process timed out after {e.timeout} seconds.")
        print(stderr)
        return True  # revert
    
    # check test results
    scores = []
    revert_reasons = []
    for r in result_id_list:
        reason = None
        if args.eval_with_gold:
            eval_path = os.path.join(args.results_dir, f"webarena.{r}_test", "summary_info.json")
            if os.path.exists(eval_path):
                cum_reward = json.load(open(eval_path))["cum_reward"]
                passed = cum_reward == 1.0
                scores.append(passed)
                if not passed:
                    reason = f"[gold] cum_reward={cum_reward} (expected 1.0)"
                print(f"[EVAL] Task {r} gold eval: cum_reward={cum_reward} → {'PASS' if passed else 'FAIL'}")
            else:
                scores.append(False)
                reason = f"[gold] summary_info.json not found at {eval_path}"
                print(f"[EVAL] Task {r} gold eval: FAIL — {reason}")
        else:
            process = subprocess.Popen([
                "python", "-m", "autoeval.evaluate_trajectory",
                "--result_dir", os.path.join(args.results_dir, f"webarena.{r}_test"),
                "--model", args.autoeval_model,
            ])
            process.wait()

            eval_path = os.path.join(args.results_dir, f"webarena.{r}_test", f"{args.autoeval_model}_autoeval.json")
            if os.path.exists(eval_path):
                eval_data = json.load(open(eval_path))[0]
                rm = eval_data.get("rm")
                thoughts = eval_data.get('thoughts', '(no thoughts recorded)')
                passed = rm == True
                scores.append(passed)
                print(f"[EVAL] Task {r} autoeval ({args.autoeval_model}): rm={rm} → {'PASS' if passed else 'FAIL'}")
                print(f"[EVAL] LLM reasoning:\n{thoughts}")
                if not passed:
                    reason = f"[autoeval] rm={rm}"
            else:
                scores.append(False)
                reason = f"[autoeval] JSON not found at {eval_path}"
                print(f"[EVAL] Task {r} autoeval: FAIL — {reason}")

        # check step valid and use actions
        command = [
            "python", "-m", "results.calc_valid_steps",
            "--result_dir", os.path.join(args.results_dir, f"webarena.{r}_test"),
            "--action_names"] + action_names
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        process.wait()
        output = process.communicate()[0].decode("utf-8").strip()
        output = output.split('\n')[-1].strip()
        print("Validity Check: ", output)
        if output == 'False':
            reason = (reason or "") + " | [validity] induced actions not used in test trajectory"
            scores[-1] = False
            print(f"[EVAL] Task {r} validity: FAIL — induced actions not found in test steps")

        if reason:
            revert_reasons.append(f"Task {r}: {reason}")

        if scores[-1] == False: break
    
    print("Scores: ", scores)
    if all([s == True for s in scores]):
        print("All Tests Passed!")
        return False
    else:
        print(f"[REVERT REASONS]")
        for reason in revert_reasons:
            print(f"  - {reason}")
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="claude-haiku-4-5",
                        help="Anthropic model for skill induction.")
    parser.add_argument("--num_responses", type=int, default=1, help="Number of responses to generate.")
    parser.add_argument("--temperature", type=float, default=1.0, help="Temperature for sampling.")

    parser.add_argument("--sys_msg_path", type=str, default="induce/prompt/system_message.txt")
    parser.add_argument("--instruction_path", type=str, default="induce/prompt/instruction.txt")
    parser.add_argument("--few_shot_path", type=str, default="induce/prompt/shopping.md")
    parser.add_argument("--test_query_path", type=str, default="induce/prompttest_query.txt")

    parser.add_argument("--template_id", type=str, default=None)
    parser.add_argument("--website", type=str, required=True,
                        choices=["shopping", "admin", "reddit", "gitlab", "map"])
    parser.add_argument("--config_dir", type=str, default="config_files")
    parser.add_argument("--results_dir", type=str, default="results")
    parser.add_argument("--result_id_list", type=str, nargs="+", default=None, help="E.g., '110 111'.")

    parser.add_argument("--write_action_path", type=str, default=None)
    parser.add_argument("--write_tests_dir", type=str, default="debug_actions")
    parser.add_argument("--eval_with_gold", action="store_true", help="If perform evaluation with ground-truth.")
    parser.add_argument("--autoeval_model", type=str, default="claude-haiku-4-5",
                        help="Model used by autoeval.evaluate_trajectory; must match the JSON filename (e.g. <model>_autoeval.json).")
    parser.add_argument("--mcp_enabled", action=argparse.BooleanOptionalAction, default=False,
                        help="Whether MCP tools are enabled for this experiment (--mcp_enabled / --no-mcp_enabled)")
    args = parser.parse_args()
    
    # Make is_mcp_enabled available at module level for write_tests function
    is_mcp_enabled = args.mcp_enabled

    if args.write_action_path is None:
        args.write_action_path = os.path.join("actions", f"{args.website}.py")

    args = get_output_dir(args)
    if os.path.exists(args.output_dir):
        print(f"Output directory already exists: {args.output_dir} - removing and regenerating")
        import shutil
        shutil.rmtree(args.output_dir)
    
    print(f"Creating new output directory: {args.output_dir}")
    os.makedirs(args.output_dir, exist_ok=True)
    responses = induce_actions()

    print(f"Collected {len(responses)} Responses..")
    if len(responses) == 0:
        print(f"ERROR: No responses generated. Check if test_query was created and LLM call succeeded.")
        print(f"Test query path: {args.test_query_path}")
        if os.path.exists(args.test_query_path):
            print(f"Test query exists ({os.path.getsize(args.test_query_path)} bytes)")
        else:
            print(f"Test query file NOT FOUND!")
    for i, resp in enumerate(responses):
        print(f"\n\n** Start Evaluating Response {i}: ", resp, "**")
        tmp_path, action_names = write_actions(resp)
        if tmp_path is None: continue

        if_revert = write_tests(resp, args.result_id_list, action_names, is_mcp_enabled)
        print("If Revert: ", if_revert)
        if if_revert:
            process = subprocess.Popen(["mv", tmp_path, args.write_action_path])
            process.wait()
            for i, r in enumerate(args.result_id_list):
                print("Command: ", ["rm", "-rf", f"results/webarena.{r}_test"])
                process = subprocess.Popen(["rm", "-rf", f"results/webarena.{r}_test"])
                process.wait()
        else:
            process = subprocess.Popen(["rm", tmp_path])
            process.wait()
            break
            
        print(f"** Finish Evaluating Response {i}: ", resp, "**\n\n")
        
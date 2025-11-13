import ast
import copy
import re
import time

import numpy as np
import playwright.sync_api

from browsergym.core.env import BrowserEnv, logger
from browsergym.core.constants import EXTRACT_OBS_MAX_TRIES
from browsergym.core.observation import (
    extract_dom_snapshot,
    extract_merged_axtree,
    extract_focused_element_bid,
    extract_screenshot,
    extract_dom_extra_properties,
    _pre_extract,
    _post_extract,
    MarkingError,
)


agent_args = None
repl_output = None  # Global to store REPL output for current step


def _try_to_extract_legacy_goal(goal: list):
    """Helper function copied from browsergym.core.env"""
    legacy_goal_strings = []
    for message in goal:
        if message["type"] == "text":
            legacy_goal_strings.append(message["text"])
        else:
            logger.debug(
                f"Message type {repr(message['type'])} present in the goal, cannot be converted to legacy text-only format."
            )
            legacy_goal_strings.append(
                'WARNING: This goal cannot be converted to a text-only goal format. Use the new goal format instead ("goal_object" field). Any agent reading this should abort immediately.'
            )
            break
    legacy_goal = "\n".join(legacy_goal_strings)
    return legacy_goal

def execute_python_code(
    code: str,
    page: playwright.sync_api.Page,
    send_message_to_user: callable,
    report_infeasible_instructions: callable,
    **additional_globals
):
    """
    Executes Python code in a new context, except for a playwright `page` object and a `send_message_to_user` function.

    WARNING: this is not safe!
    https://stackoverflow.com/questions/77655440/can-you-protect-a-python-variable-with-exec

    Args:
        code: the Python code to execute, as a string.
        page: the playwright page that will be made accessible to the code.
        send_message_to_user: utility function that will be made accessible to the code. It should take one text argument.
        report_infeasible_instructions: utility function that will be made accessible to the code. It should take one text argument.
        additional_globals: additional global variables to make accessible to the code.
    """
    
    logger.info(f"execute_python_code called with {len(code)} chars")
    logger.debug(f"Code preview: {code[:200]}...")

    globals = {
        "page": page,
        "send_message_to_user": send_message_to_user,
        "send_msg_to_user": send_message_to_user,  # Alias for the abbreviated version
        "report_infeasible_instructions": report_infeasible_instructions,
        "DEMO_MODE": False,  # Required by python_includes (custom_action_set.py:107)
        **additional_globals,
    }
    
    # Add MCP tool wrappers to execution context if they exist
    import __main__
    if hasattr(__main__, '_mcp_tool_wrappers'):
        globals['_mcp_tool_wrappers'] = __main__._mcp_tool_wrappers
    
    # Define _call_mcp_tool helper function and add it to both __main__ and exec globals
    # This is needed because MCP wrapper functions defined in __main__ need to access it
    def _call_mcp_tool(tool_name, **kwargs):
        """Execute an MCP tool by name"""
        logger.info(f"_call_mcp_tool called: tool={tool_name}, kwargs={kwargs}")
        if not hasattr(__main__, '_action_set_mcp_manager'):
            raise RuntimeError("MCP manager not available in execution context")
        tools = __main__._action_set_mcp_manager.get_all_tools()
        if tool_name not in tools:
            raise NameError(f"MCP tool '{tool_name}' not found")
        logger.info(f"Calling MCP tool wrapper for {tool_name}")
        result = tools[tool_name](**kwargs)
        logger.info(f"MCP tool returned: type={type(result)}, len={len(result) if isinstance(result, (list,dict)) else 'N/A'}")
        return result
    
    # Add to __main__ so wrapper functions can find it
    __main__._call_mcp_tool = _call_mcp_tool
    # Also add to exec globals for direct calls
    globals['_call_mcp_tool'] = _call_mcp_tool
    
    # Add MCP tool functions to execution context
    main_globals = vars(__main__)
    mcp_funcs_added = []
    for name, obj in main_globals.items():
        if callable(obj) and ('magento_review_server' in name or 'magento_product_server' in name or 'find_reviewers' in name or 'get_product_reviews' in name):
            globals[name] = obj
            mcp_funcs_added.append(name)
    
    # Debug: Log what MCP functions are available
    if mcp_funcs_added:
        logger.debug(f"Added {len(mcp_funcs_added)} MCP functions to execution context: {mcp_funcs_added}")
    else:
        logger.warning("No MCP functions found in __main__ to add to execution context!")
        # Log what callable names are in __main__
        callable_names = [name for name, obj in main_globals.items() if callable(obj) and not name.startswith('_')]
        logger.debug(f"Callable functions in __main__: {callable_names[:20]}")

    # REPL-style execution: auto-display results of final expressions
    code = code.strip()
    
    logger.info("Starting REPL-style execution logic")
    
    try:
        # Parse code to detect structure
        tree = ast.parse(code, mode='exec')
        logger.info(f"Parsed {len(tree.body)} statements")
        
        # Check if the LAST statement is an expression (handles python_includes prepended)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            logger.info("Last statement is an expression - attempting REPL-style eval")
            # Last statement is an expression - execute all but last, then eval last and display
            try:
                if len(tree.body) == 1:
                    # Only one statement, just eval it
                    result = eval(code, globals)
                else:
                    # Multiple statements - execute all but last, then eval last
                    logger.info(f"Executing {len(tree.body)-1} preceding statements, then eval last")
                    # Split code to isolate last expression
                    last_expr_node = tree.body[-1]
                    preceding_code = ast.Module(body=tree.body[:-1], type_ignores=[])
                    
                    # Execute preceding statements
                    logger.info("Executing preceding statements...")
                    exec(compile(preceding_code, '<string>', 'exec'), globals)
                    logger.info("Preceding statements executed successfully")
                    
                    # Eval last expression
                    logger.info("Evaluating last expression...")
                    last_expr = ast.Expression(body=last_expr_node.value)
                    result = eval(compile(last_expr, '<string>', 'eval'), globals)
                    logger.info(f"Eval completed, result type: {type(result)}")
                
                # Display non-None results
                logger.info(f"Checking if result is None: {result is None}")
                if result is not None:
                    logger.info("Converting result to string...")
                    result_str = repr(result)
                    logger.info(f"Result string length: {len(result_str)}")
                    if len(result_str) > 10000:
                        result_str = result_str[:10000] + f"... (truncated, total length: {len(result_str)})"
                    logger.info("Storing REPL output...")
                    # Store in global instead of sending to chat to avoid STOP action
                    global repl_output
                    repl_output = f"→ {result_str}"
                    logger.info(f"REPL auto-display stored: {result_str[:200]}")
            except Exception as e:
                # If REPL-style execution fails, fall back to regular exec
                logger.warning(f"REPL-style execution failed, falling back to exec: {e}")
                exec(code, globals)
        else:
            # Last statement is not an expression - execute normally
            exec(code, globals)
    except SyntaxError:
        # Fallback: if parsing fails, try exec (handles edge cases)
        exec(code, globals)
    except Exception:
        # Re-raise execution errors so they're handled by the step() function
        raise


def step(self: BrowserEnv, action: str) -> tuple:
    """
    Small modification of the original BrowserEnv step method that uses the custom 
    execute_python_code function. 
    TODO: Probably better to refactor browsergym to support custom exec instead of this hack.
    """        
    self.last_action = action
    
    # Initialize last_action_output if it doesn't exist
    if not hasattr(self, 'last_action_output'):
        self.last_action_output = ""
    
    # Clear REPL output from previous step
    global repl_output
    repl_output = None

    info = {}
    info["action_exec_start"] = time.time()
    info["action_exec_timeout"] = 0

    def send_message_to_user(text: str):
        if not isinstance(text, str):
            raise ValueError(f"Forbidden value: {text} is not a string")
        self.chat.add_message(role="assistant", msg=text)

    def report_infeasible_instructions(reason: str):
        if not isinstance(reason, str):
            raise ValueError(f"Forbidden value: {reason} is not a string")
        self.chat.add_message(role="infeasible", msg=reason)
        self.infeasible_message_received = True

    # try to execute the action
    logger.debug(f"Executing action")
    try:
        if self.action_mapping:
            code = self.action_mapping(action)
        else:
            code = action
        execute_python_code(
            code,
            self.page,
            send_message_to_user=send_message_to_user,
            report_infeasible_instructions=report_infeasible_instructions,
            agent_args=agent_args,
            env=self,
        )
        self.last_action_error = ""
        # Set REPL output if available
        if repl_output is not None:
            self.last_action_output = repl_output
        else:
            self.last_action_output = ""
    except Exception as e:
        self.last_action_error = f"{type(e).__name__}: {e}"
        self.last_action_output = ""
        match = re.match("TimeoutError: Timeout ([0-9]+)ms exceeded.", self.last_action_error)
        if match:
            info["action_exec_timeout"] = float(match.groups()[0]) / 1000  # ms to sec
    logger.debug(f"Action executed")
    info["action_exec_stop"] = time.time()

    # wait a bit (for the JavaScript callback to set the active page)
    time.sleep(0.5)  # wait for JS events to be fired (half a second)
    self.context.cookies()  # trigger all waiting Playwright callbacks on the stack (hack, see https://playwright.dev/java/docs/multithreading)

    # wait for the network to idle before extracting the observation, reward etc.
    self._wait_dom_loaded()

    # after the action is executed, the active page might have changed
    # perform a safety check
    self._active_page_check()
    logger.debug(f"Active page checked")

    # if asked, wait for user message
    self._wait_for_user_message()
    logger.debug(f"User message done")

    logger.debug(f"Initiating task validation")
    # extract reward, done, user_message, info (task-specific)
    reward, done, user_message, task_info = self._task_validate()
    info["task_info"] = task_info
    logger.debug(f"Task validation done")

    # add any user message sent by the task to the chat
    if user_message:
        self.chat.add_message(role="user", msg=user_message)

    # extract observation (generic)
    obs = self._get_obs()
    logger.debug(f"Observation extracted")

    # new step API wants a 5-tuple (gymnasium)
    terminated = done or (
        self.terminate_on_infeasible and self.infeasible_message_received
    )  # task or agent can terminate the episode
    truncated = False

    return obs, reward, terminated, truncated, info
    
def get_obs(self):
    """
    Patched version of BrowserEnv._get_obs() that includes last_action_output field.
    """
    if self.use_raw_page_output:
        obs = {
            "page": self.page,
            "chat_messages": tuple(copy.deepcopy(self.chat.messages)),
            "goal": _try_to_extract_legacy_goal(self.goal_object),
            "goal_object": tuple(copy.deepcopy(self.goal_object)),
            "open_pages_urls": tuple(page.url for page in self.context.pages),
            "open_pages_titles": tuple(page.title() for page in self.context.pages),
            "active_page_index": np.asarray([self.context.pages.index(self.page)]),
            "url": self.page.url,
            "last_action": self.last_action,
            "last_action_error": self.last_action_error,
            "last_action_output": getattr(self, "last_action_output", ""),
            "elapsed_time": np.asarray([time.time() - self.start_time]),
        }
        return obs
    
    for retries_left in reversed(range(EXTRACT_OBS_MAX_TRIES)):
        try:
            _pre_extract(self.page, tags_to_mark=self.tags_to_mark, lenient=(retries_left == 0))
            dom = extract_dom_snapshot(self.page)
            axtree = extract_merged_axtree(self.page)
            focused_element_bid = extract_focused_element_bid(self.page)
            scale_factor = getattr(self.page, "_bgym_scale_factor", 1.0)
            extra_properties = extract_dom_extra_properties(dom, scale_factor=scale_factor)
        except (playwright.sync_api.Error, MarkingError) as e:
            err_msg = str(e)
            if retries_left > 0 and (
                "Frame was detached" in err_msg
                or "Frame with the given frameId is not found" in err_msg
                or "Execution context was destroyed" in err_msg
                or "Frame has been detached" in err_msg
                or "Cannot mark a child frame without a bid" in err_msg
                or "Cannot read properties of undefined" in err_msg
            ):
                logger.warning(
                    f"An error occurred while extracting the dom and axtree. Retrying ({retries_left}/{EXTRACT_OBS_MAX_TRIES} tries left).\n{repr(e)}"
                )
                _post_extract(self.page)
                time.sleep(0.5)
                continue
            else:
                raise e
        break
    
    _post_extract(self.page)
    
    obs = {
        "chat_messages": tuple(copy.deepcopy(self.chat.messages)),
        "goal": _try_to_extract_legacy_goal(self.goal_object),
        "goal_object": tuple(copy.deepcopy(self.goal_object)),
        "open_pages_urls": tuple(page.url for page in self.context.pages),
        "open_pages_titles": tuple(page.title() for page in self.context.pages),
        "active_page_index": np.asarray([self.context.pages.index(self.page)]),
        "url": self.page.url,
        "screenshot": extract_screenshot(self.page),
        "dom_object": dom,
        "axtree_object": axtree,
        "extra_element_properties": extra_properties,
        "focused_element_bid": focused_element_bid,
        "last_action": self.last_action,
        "last_action_error": self.last_action_error,
        "last_action_output": getattr(self, "last_action_output", ""),
        "elapsed_time": np.asarray([time.time() - self.start_time]),
    }
    
    return obs

def patch_with_custom_exec(args):
    global agent_args
    agent_args = args
    setattr(BrowserEnv, "step", step)
    setattr(BrowserEnv, "_get_obs", get_obs)
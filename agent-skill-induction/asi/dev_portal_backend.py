#!/usr/bin/env python3
"""
Flask backend for MCP Developer Portal
Provides API endpoints for server discovery, tool execution, and test running
Uses persistent MCP clients matching the production architecture
"""
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import subprocess
import json
import sys
import os
import atexit
import logging
import signal
import shutil
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
def load_env_file():
    """Load API keys from .env file if it exists"""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        logger.info("Loaded environment variables from .env file")

def save_env_file(keys):
    """Save API keys to .env file"""
    env_file = Path(__file__).parent / '.env'
    
    # Read existing .env content
    existing_vars = {}
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_vars[key.strip()] = value.strip()
    
    # Update with new keys
    existing_vars.update(keys)
    
    # Write back to file
    with open(env_file, 'w') as f:
        f.write("# API Keys for MCP Developer Portal\n")
        f.write("# This file is automatically managed - do not edit manually\n\n")
        for key, value in existing_vars.items():
            if value:  # Only write non-empty values
                f.write(f"{key}={value}\n")
    
    # Set file permissions to be readable only by owner (600)
    env_file.chmod(0o600)
    logger.info(f"Saved environment variables to .env file with secure permissions")

# Load .env on startup
load_env_file()

# Import the MCP client from the project
sys.path.insert(0, str(Path(__file__).parent / 'mcp_integration'))
from client import MCPClient, MCPServerConfig

app = Flask(__name__)
CORS(app)

# Task ID parser (matching run_online.py behavior)
def parse_task_ids(task_id_str: str) -> list[str]:
    """Parse task ID string like '21,22,24-26' into list ['21','22','24','25','26']"""
    chunks = [c.strip() for c in task_id_str.split(",")]
    task_id_list = []
    for c in chunks:
        if "-" in c:
            s, e = [int(n.strip()) for n in c.split("-")]
            task_id_list.extend([str(i) for i in range(s, e+1)])
        else:
            task_id_list.append(c.strip())
    return task_id_list

# MCP server configurations
MCP_SERVER_CONFIGS = {
    'magento-review-server': MCPServerConfig(
        name='Magento Review Server',
        command=['docker', 'exec', '-i', 'shopping', 'python3', '/tmp/magento_review_data.py']
    ),
    'magento-product-server': MCPServerConfig(
        name='Magento Product Server',
        command=['docker', 'exec', '-i', 'shopping', 'python3', '/tmp/magento_products.py']
    )
}

# Global MCP clients (persistent connections)
mcp_clients = {}

def init_mcp_clients():
    """Initialize MCP clients on startup"""
    print("Initializing MCP clients...")
    for server_id, config in MCP_SERVER_CONFIGS.items():
        try:
            client = MCPClient(config)
            if client.connect():
                mcp_clients[server_id] = client
                print(f"✓ Connected to {config.name} ({len(client.tools)} tools)")
            else:
                print(f"✗ Failed to connect to {config.name}")
        except Exception as e:
            print(f"✗ Error connecting to {config.name}: {e}")

def cleanup_mcp_clients():
    """Cleanup MCP clients on shutdown"""
    print("\nShutting down MCP clients...")
    for server_id, client in mcp_clients.items():
        try:
            client.disconnect()
            print(f"✓ Disconnected from {server_id}")
        except Exception as e:
            print(f"✗ Error disconnecting from {server_id}: {e}")

# Register cleanup handler
atexit.register(cleanup_mcp_clients)

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    print("\n\nReceived shutdown signal, cleaning up...")
    cleanup_mcp_clients()
    sys.exit(0)

# Register signal handlers for clean shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@app.route('/api/servers', methods=['GET'])
def get_servers():
    """List available MCP servers and their tools"""
    servers = []
    tools = {}
    
    for server_id, config in MCP_SERVER_CONFIGS.items():
        client = mcp_clients.get(server_id)
        
        if client and client._connected:
            status = 'connected'
            # Get tools from connected client
            server_tools = []
            for tool_info in client.list_tools():
                server_tools.append({
                    'name': tool_info.name,
                    'description': tool_info.description,
                    'inputSchema': tool_info.input_schema
                })
            tools[config.name] = server_tools
        else:
            status = 'disconnected'
        
        servers.append({
            'name': config.name,
            'description': f'{len(client.tools)} tools available' if client and client._connected else 'Not connected',
            'path': ' '.join(config.command[-2:]),  # Show the python script path
            'status': status
        })
    
    return jsonify({
        'servers': servers,
        'tools': tools
    })

@app.route('/api/execute-tool', methods=['POST'])
def execute_tool():
    """Execute a specific MCP tool using persistent client"""
    data = request.json
    server_name = data.get('server')
    tool_name = data.get('tool')
    args = data.get('args', {})
    
    # Find client by server name
    client = None
    for server_id, config in MCP_SERVER_CONFIGS.items():
        if config.name == server_name:
            client = mcp_clients.get(server_id)
            break
    
    if not client:
        return jsonify({'error': 'Server not found'}), 404
    
    if not client._connected:
        return jsonify({'error': 'Server not connected'}), 503
    
    try:
        result = client.call_tool(tool_name, args)
        return jsonify({'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reconnect/<server_name>', methods=['POST'])
def reconnect_server(server_name):
    """Reconnect to a specific MCP server"""
    # Find server config
    server_id = None
    config = None
    for sid, cfg in MCP_SERVER_CONFIGS.items():
        if cfg.name == server_name:
            server_id = sid
            config = cfg
            break
    
    if not config:
        return jsonify({'error': 'Server not found'}), 404
    
    try:
        # Disconnect if already connected
        if server_id in mcp_clients:
            mcp_clients[server_id].disconnect()
        
        # Reconnect
        client = MCPClient(config)
        if client.connect():
            mcp_clients[server_id] = client
            return jsonify({
                'status': 'connected',
                'tools_count': len(client.tools)
            })
        else:
            return jsonify({'error': 'Failed to connect'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-test/<test_name>', methods=['GET'])
def run_test(test_name):
    """Run test scripts and stream output"""
    if test_name == 'quick':
        script = 'claude_utils/test_mcp_server.py'
    elif test_name == 'full':
        script = 'claude_utils/test_magento_mcp.py'
    else:
        return jsonify({'error': 'Invalid test name'}), 400
    
    def generate():
        proc = subprocess.Popen(
            ['python3', script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        
        for line in iter(proc.stdout.readline, ''):
            if line:
                yield line
        
        proc.stdout.close()
        proc.wait()
    
    return Response(generate(), mimetype='text/plain')

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """List available WebArena tasks from config files (only MCP-enabled tasks)"""
    try:
        config_dir = Path(__file__).parent / 'config_files'
        tasks = []
        
        # Only include tasks that have a -mcp-container.json file
        for config_file in config_dir.glob('*-mcp-container.json'):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Extract base task name (e.g., "21" from "21-mcp-container.json")
                    task_name = config_file.stem.replace('-mcp-container', '')
                    tasks.append({
                        'name': task_name,
                        'id': config.get('task_id', task_name),
                        'sites': config.get('sites', []),
                        'intent': config.get('intent', 'No description available')
                    })
            except Exception as e:
                logger.error(f"Error reading config {config_file}: {e}")
                continue
        
        # Sort numerically by task name
        tasks.sort(key=lambda x: int(x['name']) if x['name'].isdigit() else float('inf'))
        return jsonify({'tasks': tasks})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-task', methods=['POST'])
def run_task():
    """Run a WebArena task and stream output"""
    data = request.json
    task_name = data.get('task_name')
    website = data.get('website', 'shopping')
    headless = data.get('headless', True)
    use_mcp = data.get('use_mcp', True)
    use_asi = data.get('use_asi', False)
    
    if not task_name:
        return jsonify({'error': 'task_name is required'}), 400
    
    # When MCP is enabled, prefer -mcp-container.json config if it exists
    if use_mcp:
        mcp_config_file = f"config_files/{task_name}-mcp-container.json"
        if os.path.exists(mcp_config_file):
            config_file = mcp_config_file
        else:
            config_file = f"config_files/{task_name}.json"
    else:
        config_file = f"config_files/{task_name}.json"
    
    if not os.path.exists(config_file):
        return jsonify({'error': f'Config file not found: {config_file}'}), 404
    
    cmd = [
        'python3', 'run_demo.py',
        '--task_name', f'webarena.{task_name}',
        '--websites', website
    ]
    
    if use_mcp:
        cmd.extend(['--mcp_config', config_file])
    
    if headless:
        cmd.append('--headless')
    
    def generate():
        # If ASI is enabled, use run_online.py instead
        if use_asi:
            yield '[ASI] Running task with Agent Skill Induction enabled...\n'
            proc = subprocess.Popen(
                ['python3', 'run_online.py', '--experiment', 'asi', '--website', website, '--task_ids', task_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            
            result_dir = None
            for line in iter(proc.stdout.readline, ''):
                if line:
                    yield line
                    # Extract result directory for later use
                    if 'results/webarena.' in line:
                        parts = line.split('results/')
                        if len(parts) > 1:
                            potential_dir = parts[1].split()[0].strip()
                            if potential_dir.startswith('webarena.'):
                                result_dir = potential_dir
            
            proc.stdout.close()
            return_code = proc.wait()
            
            if return_code == 0:
                yield '\n[ASI] Agent Skill Induction completed successfully!\n'
                yield '[ASI] Check actions/shopping.py for newly induced skills.\n'
                yield '\n[TASK COMPLETED SUCCESSFULLY]\n'
            else:
                yield f'\n[ASI] Process failed with code {return_code}\n'
                yield '\n[TASK FAILED]\n'
            
            # Set result_dir to symlink if not extracted
            if not result_dir:
                result_dir = f'webarena.{task_name}'
            
            yield f'\n[RESULT_DIR:{result_dir}]\n'
        else:
            # Normal execution without ASI
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=os.environ.copy()
            )
            
            result_dir = None
            prev_line = ''
            for line in iter(proc.stdout.readline, ''):
                if line:
                    yield line
                    # Extract result directory from output
                    # Format is: "Running experiment ... in:\n  results/dirname"
                    if 'Running experiment' in prev_line and 'results/' in line:
                        parts = line.strip().split('results/')
                        if len(parts) > 1:
                            result_dir = parts[1].strip()
                    elif 'results/' in line and 'Running experiment' in line:
                        # Fallback for single-line format
                        parts = line.split('results/')
                        if len(parts) > 1:
                            result_dir = parts[1].strip().split()[0]
                    prev_line = line
            
            proc.stdout.close()
            return_code = proc.wait()
            
            if return_code == 0:
                yield '\n[TASK COMPLETED SUCCESSFULLY]\n'
            else:
                yield f'\n[TASK FAILED WITH CODE {return_code}]\n'
            
            # Send result directory path for frontend to fetch detailed results
            if result_dir:
                yield f'\n[RESULT_DIR:{result_dir}]\n'
    
    return Response(generate(), mimetype='text/plain')

@app.route('/api/task-results/<path:result_path>', methods=['GET'])
def get_task_results(result_path):
    """Get parsed results from a completed task run"""
    try:
        results_base = Path(__file__).parent / 'results'
        results_dir = results_base / result_path
        
        # If timestamped directory doesn't exist, try webarena.{task_id} format
        if not results_dir.exists():
            # Extract task ID from path like "2025-10-08_00-23-13_DemoAgentArgs_on_webarena.21_23"
            if 'webarena.' in result_path:
                parts = result_path.split('webarena.')
                if len(parts) > 1:
                    # Extract just the task number (e.g., "21" from "21_23")
                    task_num = parts[1].split('_')[0]
                    fallback_dir = results_base / f'webarena.{task_num}'
                    if fallback_dir.exists():
                        results_dir = fallback_dir
                        logger.info(f"Using fallback directory: {fallback_dir}")
        
        if not results_dir.exists():
            return jsonify({'error': f'Results directory not found: {result_path}'}), 404
        
        # Read summary info
        summary_file = results_dir / 'summary_info.json'
        if not summary_file.exists():
            return jsonify({'error': 'Summary file not found'}), 404
        
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        # Read experiment log for agent actions and OpenAI evaluations
        log_file = results_dir / 'experiment.log'
        agent_actions = []
        openai_evals = []
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_content = f.read()
                
                # Parse out action logs
                for i, section in enumerate(log_content.split('INFO - action:')):
                    if i == 0:
                        continue
                    action_text = section.split('\n\n')[0].strip()
                    agent_actions.append({
                        'step': i - 1,
                        'action': action_text
                    })
                
                # Parse OpenAI API calls - these are action evaluations
                lines = log_content.split('\n')
                for i, line in enumerate(lines):
                    if 'HTTP Request: POST https://api.openai.com/v1/chat/completions' in line:
                        # Extract timestamp and status
                        timestamp = line.split(' - ')[0]
                        status = line.split('"')[-2] if '"' in line else 'Unknown'
                        
                        # Try to find which step this evaluation is for
                        # Look backwards to find the most recent action
                        step_num = None
                        for j in range(i-1, max(0, i-50), -1):
                            if 'INFO - action:' in lines[j]:
                                # Count how many actions we've seen so far
                                actions_before = log_content[:log_content.find(lines[j])].count('INFO - action:')
                                step_num = actions_before
                                break
                        
                        openai_evals.append({
                            'step': step_num,
                            'timestamp': timestamp,
                            'status': status,
                            'purpose': 'Action evaluation/critic'
                        })
        
        # Find screenshots
        screenshots = []
        for screenshot_file in sorted(results_dir.glob('screenshot_step_*.png')):
            step_num = int(screenshot_file.stem.split('_')[-1])
            screenshots.append({
                'step': step_num,
                'filename': screenshot_file.name
            })
        
        # Calculate success based on reward
        # Success: reward == 1, Failed: reward == 0, Error: execution failed
        reward = summary.get('cum_reward', 0)
        success = reward >= 1
        terminated = summary.get('terminated', False)
        truncated = summary.get('truncated', False)
        
        # Read raw output if available
        raw_output = None
        raw_output_file = results_dir / 'raw_output.txt'
        if raw_output_file.exists():
            with open(raw_output_file, 'r') as f:
                raw_output = f.read()
        elif log_file.exists():
            # Fallback to experiment.log if raw_output.txt doesn't exist
            with open(log_file, 'r') as f:
                raw_output = f.read()
        
        result = {
            'success': success,
            'reward': summary.get('cum_reward', 0),
            'n_steps': summary.get('n_steps', 0),
            'terminated': terminated,
            'truncated': truncated,
            'error': summary.get('err_msg'),
            'stats': {
                'total_time': summary.get('stats.cum_step_elapsed', 0),
                'agent_time': summary.get('stats.cum_agent_elapsed', 0),
                'tokens_used': summary.get('stats.cum_n_token_axtree_txt', 0) + summary.get('stats.cum_n_token_pruned_html', 0) + summary.get('stats.cum_n_token_last_action', 0),
                'input_tokens': summary.get('stats.cum_n_token_axtree_txt', 0) + summary.get('stats.cum_n_token_pruned_html', 0),
                'output_tokens': summary.get('stats.cum_n_token_last_action', 0),
                'max_tokens_per_step': max(
                    summary.get('stats.max_n_token_axtree_txt', 0),
                    summary.get('stats.max_n_token_pruned_html', 0)
                )
            },
            'actions': agent_actions,
            'openai_evals': openai_evals,
            'screenshots': screenshots,
            'raw_output': raw_output,
            'result_dir': results_dir.name  # Use the actual directory name we found
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error reading task results: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/task-results/<path:result_path>/screenshot/<filename>', methods=['GET'])
def get_screenshot(result_path, filename):
    """Serve screenshot images from results"""
    try:
        from flask import send_file
        screenshot_path = Path(__file__).parent / 'results' / result_path / filename
        
        if not screenshot_path.exists():
            return jsonify({'error': 'Screenshot not found'}), 404
        
        return send_file(screenshot_path, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error serving screenshot: {e}")
        return jsonify({'error': str(e)}), 500

def sanitize_api_key(key):
    """Remove invisible Unicode characters and whitespace from API key"""
    if not key:
        return key
    # Remove line separators, paragraph separators, and other invisible Unicode
    sanitized = key.replace('\u2028', '').replace('\u2029', '').replace('\u200b', '')
    # Strip whitespace
    sanitized = sanitized.strip()
    return sanitized

@app.route('/api/set-env', methods=['POST'])
def set_env():
    """Set environment variables for API keys and persist to .env file"""
    try:
        data = request.json
        keys_to_save = {}
        
        if 'ANTHROPIC_API_KEY' in data and data['ANTHROPIC_API_KEY']:
            clean_key = sanitize_api_key(data['ANTHROPIC_API_KEY'])
            os.environ['ANTHROPIC_API_KEY'] = clean_key
            keys_to_save['ANTHROPIC_API_KEY'] = clean_key
            logger.info("Updated ANTHROPIC_API_KEY")
        
        if 'OPENAI_API_KEY' in data and data['OPENAI_API_KEY']:
            clean_key = sanitize_api_key(data['OPENAI_API_KEY'])
            os.environ['OPENAI_API_KEY'] = clean_key
            keys_to_save['OPENAI_API_KEY'] = clean_key
            logger.info("Updated OPENAI_API_KEY")
        
        # Save to .env file for persistence
        if keys_to_save:
            save_env_file(keys_to_save)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error setting environment variables: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs', methods=['GET'])
def get_saved_runs():
    """List all saved task runs (including batch runs)"""
    try:
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        saved_runs_dir.mkdir(exist_ok=True)
        
        runs = []
        for run_dir in saved_runs_dir.iterdir():
            if run_dir.is_dir():
                # Check for batch metadata first
                batch_metadata_file = run_dir / 'batch_metadata.json'
                if batch_metadata_file.exists():
                    with open(batch_metadata_file, 'r') as f:
                        metadata = json.load(f)
                        metadata['type'] = 'batch'
                        runs.append(metadata)
                else:
                    # Regular run metadata
                    metadata_file = run_dir / 'metadata.json'
                    summary_file = run_dir / 'summary_info.json'
                    
                    if metadata_file.exists() and summary_file.exists():
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        with open(summary_file, 'r') as f:
                            summary = json.load(f)
                        
                        reward = summary.get('cum_reward', 0)
                        runs.append({
                            'id': run_dir.name,
                            'type': 'single',
                            'name': metadata.get('name', run_dir.name),
                            'task_id': metadata.get('task_id'),
                            'timestamp': metadata.get('timestamp'),
                            'tags': metadata.get('tags', []),
                            'notes': metadata.get('notes', ''),
                            'success': reward >= 1,
                            'error': summary.get('err_msg'),
                            'reward': reward,
                            'n_steps': summary.get('n_steps', 0),
                            'truncated': summary.get('truncated', False)
                        })
        
        # Sort by timestamp, most recent first
        runs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify({'runs': runs})
    except Exception as e:
        logger.error(f"Error listing saved runs: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs', methods=['POST'])
def save_run():
    """Save a task run for later analysis"""
    try:
        data = request.json
        result_dir = data.get('result_dir')
        custom_name = data.get('name', '')
        tags = data.get('tags', [])
        notes = data.get('notes', '')
        task_id = data.get('task_id', '')
        
        if not result_dir:
            return jsonify({'error': 'result_dir is required'}), 400
        
        # Source directory
        source_dir = Path(__file__).parent / 'results' / result_dir
        if not source_dir.exists():
            return jsonify({'error': f'Result directory not found: {result_dir}'}), 404
        
        # Create saved_runs directory if it doesn't exist
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        saved_runs_dir.mkdir(exist_ok=True)
        
        # Generate unique directory name
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = custom_name.replace(' ', '_').replace('/', '_')[:50] if custom_name else ''
        dir_name = f"task_{task_id}_{safe_name}_{timestamp}" if safe_name else f"task_{task_id}_{timestamp}"
        dest_dir = saved_runs_dir / dir_name
        
        # Copy the entire result directory
        shutil.copytree(source_dir, dest_dir)
        
        # Create metadata file
        metadata = {
            'name': custom_name or f"Task {task_id} - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            'task_id': task_id,
            'timestamp': datetime.now().isoformat(),
            'tags': tags,
            'notes': notes,
            'original_result_dir': result_dir
        }
        
        with open(dest_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved run to {dest_dir}")
        return jsonify({'success': True, 'id': dir_name})
    except Exception as e:
        logger.error(f"Error saving run: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs/<run_id>', methods=['DELETE'])
def delete_saved_run(run_id):
    """Delete a saved task run"""
    try:
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        run_dir = saved_runs_dir / run_id
        
        if not run_dir.exists():
            return jsonify({'error': 'Saved run not found'}), 404
        
        shutil.rmtree(run_dir)
        logger.info(f"Deleted saved run: {run_id}")
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting saved run: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs/<run_id>/batch', methods=['GET'])
def get_batch_run_details(run_id):
    """Get full batch run details including all task results"""
    try:
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        batch_dir = saved_runs_dir / run_id
        
        if not batch_dir.exists():
            return jsonify({'error': 'Batch run not found'}), 404
        
        batch_metadata_file = batch_dir / 'batch_metadata.json'
        if not batch_metadata_file.exists():
            return jsonify({'error': 'Not a batch run'}), 400
        
        with open(batch_metadata_file, 'r') as f:
            batch_data = json.load(f)
        
        return jsonify(batch_data)
    except Exception as e:
        logger.error(f"Error loading batch run details: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs/<run_id>/results', methods=['GET'])
def get_saved_run_results(run_id):
    """Get detailed results for a saved run (same format as /api/task-results)"""
    try:
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        results_dir = saved_runs_dir / run_id
        
        if not results_dir.exists():
            return jsonify({'error': f'Saved run not found: {run_id}'}), 404
        
        # Check if this is a batch run
        batch_metadata_file = results_dir / 'batch_metadata.json'
        if batch_metadata_file.exists():
            # This is a batch run, redirect to batch endpoint
            return get_batch_run_details(run_id)
        
        # Read metadata
        metadata_file = results_dir / 'metadata.json'
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
        else:
            metadata = {}
        
        # Read summary info
        summary_file = results_dir / 'summary_info.json'
        if not summary_file.exists():
            return jsonify({'error': 'Summary file not found'}), 404
        
        with open(summary_file, 'r') as f:
            summary = json.load(f)
        
        # Read experiment log for agent actions and OpenAI evaluations
        log_file = results_dir / 'experiment.log'
        agent_actions = []
        openai_evals = []
        raw_output = ""
        
        if log_file.exists():
            with open(log_file, 'r') as f:
                log_content = f.read()
                raw_output = log_content  # Store for raw output view
                logger.info(f"Loaded raw output for saved run {run_id}: {len(raw_output)} bytes")
                
                # Parse out action logs
                for i, section in enumerate(log_content.split('INFO - action:')):
                    if i == 0:
                        continue
                    action_text = section.split('\n\n')[0].strip()
                    agent_actions.append({
                        'step': i - 1,
                        'action': action_text
                    })
                
                # Parse OpenAI API calls
                lines = log_content.split('\n')
                for i, line in enumerate(lines):
                    if 'HTTP Request: POST https://api.openai.com/v1/chat/completions' in line:
                        timestamp = line.split(' - ')[0]
                        status = line.split('"')[-2] if '"' in line else 'Unknown'
                        
                        step_num = None
                        for j in range(i-1, max(0, i-50), -1):
                            if 'INFO - action:' in lines[j]:
                                actions_before = log_content[:log_content.find(lines[j])].count('INFO - action:')
                                step_num = actions_before
                                break
                        
                        openai_evals.append({
                            'step': step_num,
                            'timestamp': timestamp,
                            'status': status,
                            'purpose': 'Action evaluation/critic'
                        })
        else:
            logger.warning(f"No experiment.log found for saved run {run_id}")
        
        # Find screenshots
        screenshots = []
        for screenshot_file in sorted(results_dir.glob('screenshot_step_*.png')):
            step_num = int(screenshot_file.stem.split('_')[-1])
            screenshots.append({
                'step': step_num,
                'filename': screenshot_file.name
            })
        
        # Calculate success based on reward
        # Success: reward == 1, Failed: reward == 0, Error: execution failed
        reward = summary.get('cum_reward', 0)
        success = reward >= 1
        terminated = summary.get('terminated', False)
        truncated = summary.get('truncated', False)
        
        result = {
            'success': success,
            'reward': summary.get('cum_reward', 0),
            'n_steps': summary.get('n_steps', 0),
            'terminated': terminated,
            'truncated': truncated,
            'error': summary.get('err_msg'),
            'stats': {
                'total_time': summary.get('stats.cum_step_elapsed', 0),
                'agent_time': summary.get('stats.cum_agent_elapsed', 0),
                'tokens_used': summary.get('stats.cum_n_token_axtree_txt', 0) + summary.get('stats.cum_n_token_pruned_html', 0) + summary.get('stats.cum_n_token_last_action', 0),
                'input_tokens': summary.get('stats.cum_n_token_axtree_txt', 0) + summary.get('stats.cum_n_token_pruned_html', 0),
                'output_tokens': summary.get('stats.cum_n_token_last_action', 0),
                'max_tokens_per_step': max(
                    summary.get('stats.max_n_token_axtree_txt', 0),
                    summary.get('stats.max_n_token_pruned_html', 0)
                )
            },
            'actions': agent_actions,
            'openai_evals': openai_evals,
            'screenshots': screenshots,
            'result_dir': run_id,
            'metadata': metadata,
            'is_saved_run': True,
            'raw_output': raw_output
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error reading saved run results: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/saved-runs/<run_id>/screenshot/<filename>', methods=['GET'])
def get_saved_run_screenshot(run_id, filename):
    """Serve screenshot images from saved runs"""
    try:
        from flask import send_file
        screenshot_path = Path(__file__).parent / 'saved_runs' / run_id / filename
        
        if not screenshot_path.exists():
            return jsonify({'error': 'Screenshot not found'}), 404
        
        return send_file(screenshot_path, mimetype='image/png')
    except Exception as e:
        logger.error(f"Error serving saved run screenshot: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/skills', methods=['GET'])
def get_skills():
    """Get the current skill library content"""
    try:
        shopping_py_path = Path(__file__).parent / 'actions' / 'shopping.py'
        
        if not shopping_py_path.exists():
            return jsonify({'error': 'Skill library not found'}), 404
        
        with open(shopping_py_path, 'r') as f:
            content = f.read()
        
        # Parse out individual skills (functions)
        import re
        function_pattern = r'def\s+(\w+)\s*\([^)]*\)\s*(?:->\s*[^:]+)?:\s*\n?\s*"""(.*?)"""'
        matches = re.findall(function_pattern, content, re.DOTALL)
        
        skills = []
        for func_name, docstring in matches:
            skills.append({
                'name': func_name,
                'docstring': docstring.strip()
            })
        
        return jsonify({
            'content': content,
            'skill_count': len(skills),
            'skills': skills,
            'path': str(shopping_py_path)
        })
    except Exception as e:
        logger.error(f"Error reading skills: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reset-skills', methods=['POST'])
def reset_skills():
    """Reset the skill library (shopping.py) to initial state"""
    try:
        initial_shopping_py = """from browsergym.core.action.functions import *

import playwright.sync_api
page: playwright.sync_api.Page = None


# Skills will be induced here by ASI
"""
        
        shopping_py_path = Path(__file__).parent / 'actions' / 'shopping.py'
        
        # Write initial state
        with open(shopping_py_path, 'w') as f:
            f.write(initial_shopping_py)
        
        logger.info("Reset shopping.py to initial state")
        return jsonify({'success': True, 'message': 'Skill library reset to initial state'})
    except Exception as e:
        logger.error(f"Error resetting skills: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/run-batch-tasks', methods=['POST'])
def run_batch_tasks():
    """Run multiple WebArena tasks and stream progress updates"""
    data = request.json
    task_ids_str = data.get('task_ids')
    website = data.get('website', 'shopping')
    headless = data.get('headless', True)
    use_mcp = data.get('use_mcp', True)
    use_asi = data.get('use_asi', False)
    
    if not task_ids_str:
        return jsonify({'error': 'task_ids is required'}), 400
    
    try:
        task_ids = parse_task_ids(task_ids_str)
    except Exception as e:
        return jsonify({'error': f'Invalid task_ids format: {str(e)}'}), 400
    
    def generate():
        import time
        batch_results = []
        
        yield f"data: {json.dumps({'type': 'batch_start', 'total_tasks': len(task_ids), 'task_ids': task_ids})}\n\n"
        
        for idx, task_id in enumerate(task_ids):
            task_num = idx + 1
            yield f"data: {json.dumps({'type': 'task_start', 'task_id': task_id, 'task_num': task_num, 'total': len(task_ids)})}\n\n"
            
            # Run task with or without ASI
            start_time = time.time()
            
            if use_asi:
                # Use run_online.py for ASI workflow
                yield f"data: {json.dumps({'type': 'task_output', 'task_id': task_id, 'line': '[ASI] Running task with Agent Skill Induction enabled...'})}\n\n"
                cmd = [
                    'python3', 'run_online.py',
                    '--experiment', 'asi',
                    '--website', website,
                    '--task_ids', task_id
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=os.environ.copy()
                )
            else:
                # Normal execution without ASI
                # Determine config file
                if use_mcp:
                    mcp_config_file = f"config_files/{task_id}-mcp-container.json"
                    if os.path.exists(mcp_config_file):
                        config_file = mcp_config_file
                    else:
                        config_file = f"config_files/{task_id}.json"
                else:
                    config_file = f"config_files/{task_id}.json"
                
                if not os.path.exists(config_file):
                    yield f"data: {json.dumps({'type': 'task_error', 'task_id': task_id, 'error': f'Config file not found: {config_file}'})}\n\n"
                    batch_results.append({'task_id': task_id, 'status': 'error', 'error': 'Config not found'})
                    continue
                
                cmd = [
                    'python3', 'run_demo.py',
                    '--task_name', f'webarena.{task_id}',
                    '--websites', website
                ]
                
                if use_mcp:
                    cmd.extend(['--mcp_config', config_file])
                
                if headless:
                    cmd.append('--headless')
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=os.environ.copy()
                )
            
            result_dir = None
            output_lines = []
            prev_line = ''
            for line in iter(proc.stdout.readline, ''):
                if line:
                    output_lines.append(line)
                    # Extract result directory (two-line format)
                    if 'Running experiment' in prev_line and 'results/' in line:
                        parts = line.strip().split('results/')
                        if len(parts) > 1:
                            result_dir = parts[1].strip()
                    # Also handle single-line format
                    elif 'Running experiment' in line and 'results/' in line:
                        parts = line.split('results/')
                        if len(parts) > 1:
                            result_dir = parts[1].strip().split()[0]
                    
                    prev_line = line
                    # Stream output
                    yield f"data: {json.dumps({'type': 'task_output', 'task_id': task_id, 'line': line.rstrip()})}\n\n"
            
            proc.stdout.close()
            return_code = proc.wait()
            elapsed = time.time() - start_time
            
            # Determine status based on return code and reward
            # Error: execution failed (return_code != 0)
            # Success: reward == 1
            # Failed: reward == 0
            task_result = {
                'task_id': task_id,
                'status': 'error' if return_code != 0 else 'unknown',
                'result_dir': result_dir,
                'elapsed_time': round(elapsed, 2),
                'return_code': return_code
            }
            
            # Try to get summary info and save raw output to result dir
            # Use symlink directory (webarena.{task_id}) which always exists
            symlink_dir = Path(__file__).parent / 'results' / f'webarena.{task_id}'
            try:
                # Save raw output to the symlink directory first (guaranteed to work)
                raw_output_path = symlink_dir / 'raw_output.txt'
                with open(raw_output_path, 'w') as f:
                    f.write(''.join(output_lines))
                logger.info(f"Saved raw output for task {task_id} to {raw_output_path}")
                
                # Read summary from symlink directory
                summary_path = symlink_dir / 'summary_info.json'
                if summary_path.exists():
                    with open(summary_path, 'r') as f:
                        summary = json.load(f)
                        task_result['n_steps'] = summary.get('n_steps', 0)
                        reward = summary.get('cum_reward', 0)
                        task_result['reward'] = reward
                        
                        # Update status based on reward if execution succeeded
                        if return_code == 0:
                            task_result['status'] = 'success' if reward >= 1 else 'failed'
                
                # Also try to save to timestamped directory if we extracted it
                if result_dir:
                    timestamped_path = Path(__file__).parent / 'results' / result_dir
                    if timestamped_path.exists() and timestamped_path != symlink_dir:
                        timestamped_output = timestamped_path / 'raw_output.txt'
                        with open(timestamped_output, 'w') as f:
                            f.write(''.join(output_lines))
                        logger.info(f"Also saved raw output to timestamped dir: {timestamped_output}")
                
                # Note: ASI post-processing is handled by run_online.py, no need to do it here
                
            except Exception as e:
                logger.error(f"Error processing results for task {task_id}: {e}")
            
            batch_results.append(task_result)
            yield f"data: {json.dumps({'type': 'task_complete', **task_result})}\n\n"
        
        # Send batch summary
        success_count = sum(1 for r in batch_results if r['status'] == 'success')
        
        # Auto-save batch run
        batch_name = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_tasks_{'_'.join(task_ids)}"
        saved_runs_dir = Path(__file__).parent / 'saved_runs'
        saved_runs_dir.mkdir(exist_ok=True)
        
        batch_dir = saved_runs_dir / batch_name
        batch_dir.mkdir(exist_ok=True)
        
        # Save batch metadata
        batch_metadata = {
            'id': batch_name,
            'timestamp': datetime.now().isoformat(),
            'task_ids': task_ids,
            'results': batch_results,
            'success_count': success_count,
            'total': len(task_ids),
            'name': f"Batch {'-'.join(task_ids[:3])}{'...' if len(task_ids) > 3 else ''}",
            'tags': ['batch', 'auto-saved'],
            'notes': f"Auto-saved batch run of tasks {', '.join(task_ids)}"
        }
        
        with open(batch_dir / 'batch_metadata.json', 'w') as f:
            json.dump(batch_metadata, f, indent=2)
        
        logger.info(f"Auto-saved batch run to {batch_dir}")
        
        yield f"data: {json.dumps({'type': 'batch_complete', 'results': batch_results, 'success_count': success_count, 'total': len(task_ids), 'saved_to': batch_name})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("=" * 60)
    print("MCP Developer Portal Backend")
    print("=" * 60)
    print("")
    
    # Initialize MCP clients
    init_mcp_clients()
    
    print("")
    print("=" * 60)
    print("Flask API: http://localhost:5000")
    print("Frontend (Vite): Run 'npm run dev' in dev-portal/")
    print("=" * 60)
    print("")
    
    app.run(debug=True, port=5000, use_reloader=False)

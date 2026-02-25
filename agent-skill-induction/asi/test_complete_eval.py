#!/usr/bin/env python3
"""Test complete evaluation flow to verify LLM fuzzy match logging."""

import sys
import os
sys.path.insert(0, '/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')

# Set environment variables required by WebArena
os.environ.update({
    'REDDIT': 'reddit.example.com',
    'SHOPPING': 'localhost:7770', 
    'SHOPPING_ADMIN': 'localhost:7780/admin',
    'GITLAB': 'gitlab.example.com',
    'WIKIPEDIA': 'wikipedia.example.com',
    'MAP': 'map.example.com',
    'HOMEPAGE': 'homepage.example.com'
})

import logging
import json
from pathlib import Path

# Set up logging to capture our enhanced logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from evaluation_harness.evaluators import StringEvaluator
from evaluation_harness.helper_functions import PseudoPage

def test_task_225_evaluation():
    """Test Task 225 evaluation using the actual evaluator flow."""
    
    # Create a mock trajectory with the agent's response
    mock_trajectory = [
        # Mock action that contains the agent's response in "answer" field
        {
            'action_type': 'send_msg_to_user',
            'answer': 'No products found matching "sephora brush". Let me try a broader search.'
        }
    ]
    
    config_file = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    
    print("=== Testing Task 225 StringEvaluator ===")
    print(f"Config file: {config_file}")
    
    # Load config to show what we're testing
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print(f"Task intent: {config['intent']}")
    print(f"Expected fuzzy_match: {config['eval']['reference_answers']['fuzzy_match']}")
    print(f"Agent response: {mock_trajectory[0]['answer']}")
    print()
    
    # Create evaluator and test
    evaluator = StringEvaluator()
    
    print("=== Starting evaluation (watch for our enhanced logs) ===")
    
    try:
        result = evaluator(
            trajectory=mock_trajectory,
            config_file=config_file,
            page=None,
            client=None
        )
        
        print(f"=== Evaluation result: {result} ===")
        return result
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_task_225_evaluation()
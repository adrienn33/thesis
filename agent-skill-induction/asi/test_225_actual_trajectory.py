#!/usr/bin/env python3
"""Test evaluation on the actual Task 225 trajectory that just completed."""

import sys
import os
sys.path.insert(0, '/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')

# Load .env file
from dotenv import load_dotenv
load_dotenv('/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/.env')

# Set other environment variables
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from evaluation_harness.evaluators import StringEvaluator

def test_actual_225_trajectory():
    """Test evaluation on the actual agent response from Task 225."""
    
    # Use the actual agent response from the logs
    mock_trajectory = [
        {
            'action_type': 'send_msg_to_user',
            'answer': 'No Sephora brush products found.'
        }
    ]
    
    config_file = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    
    print("=== Testing Actual Task 225 Response ===")
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print(f"Task intent: {config['intent']}")
    print(f"Expected fuzzy_match: {config['eval']['reference_answers']['fuzzy_match']}")
    print(f"Actual agent response: {mock_trajectory[0]['answer']}")
    print(f"Expected unachievable reason: {config['eval'].get('string_note', 'N/A')}")
    print()
    
    # Create evaluator and test
    evaluator = StringEvaluator()
    
    print("=== Testing LLM Evaluation on Actual Response ===")
    
    try:
        result = evaluator(
            trajectory=mock_trajectory,
            config_file=config_file,
            page=None,
            client=None
        )
        
        print(f"\n=== Final evaluation result: {result} ===")
        
        if result > 0.0:
            print("🎉 SUCCESS: Task 225 would pass with LLM evaluation!")
        else:
            print("❌ Task 225 still fails - check LLM reasoning in logs")
        
        return result
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_actual_225_trajectory()
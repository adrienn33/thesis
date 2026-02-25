#!/usr/bin/env python3
"""Test evaluation with proper environment loading."""

import sys
import os
sys.path.insert(0, '/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')

# Load .env file BEFORE importing other modules
from dotenv import load_dotenv
load_dotenv('/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/.env')

# Verify OpenAI key is loaded
openai_key = os.environ.get('OPENAI_API_KEY')
print(f"OpenAI API Key loaded: {'Yes' if openai_key else 'No'}")
if openai_key:
    print(f"Key prefix: {openai_key[:20]}...")

# Set other required environment variables
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

def test_task_225_with_env():
    """Test Task 225 evaluation with proper environment loading."""
    
    # Create mock trajectory
    mock_trajectory = [
        {
            'action_type': 'send_msg_to_user',
            'answer': 'No products found matching "sephora brush". Let me try a broader search.'
        }
    ]
    
    config_file = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    
    print("\n=== Testing Task 225 with Environment Variables ===")
    
    # Load config
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print(f"Task intent: {config['intent']}")
    print(f"Expected fuzzy_match: {config['eval']['reference_answers']['fuzzy_match']}")
    print(f"Agent response: {mock_trajectory[0]['answer']}")
    print()
    
    # Create evaluator and test
    evaluator = StringEvaluator()
    
    print("=== Starting evaluation with OpenAI API key ===")
    
    try:
        result = evaluator(
            trajectory=mock_trajectory,
            config_file=config_file,
            page=None,
            client=None
        )
        
        print(f"\n=== Final evaluation result: {result} ===")
        
        if result > 0.0:
            print("🎉 SUCCESS: LLM fuzzy match is now working!")
        else:
            print("❌ Still getting 0.0 - check logs for details")
        
        return result
        
    except Exception as e:
        print(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_task_225_with_env()
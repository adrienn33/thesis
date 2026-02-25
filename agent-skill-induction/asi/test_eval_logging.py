#!/usr/bin/env python3
"""Test script to verify evaluation logging enhancements are working for Task 225."""

import sys
sys.path.insert(0, '/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')

import json
import logging

# Set up logging to capture our enhanced logs
logging.basicConfig(level=logging.INFO)

from evaluation_harness.evaluators import StringEvaluator

def test_task_225_evaluation():
    """Test Task 225 evaluation with expected LLM fuzzy match."""
    
    # Load Task 225 configuration
    config_path = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print(f"Task 225 Configuration:")
    print(f"  Intent: {config['intent']}")
    
    eval_types = config['eval']['eval_types'] if 'eval' in config else []
    print(f"  Evaluation types: {eval_types}")
    
    # Find string evaluator config
    string_eval = None
    for eval_config in eval_types:
        if eval_config.get('evaluator_type') == 'string_match':
            string_eval = eval_config
            break
    
    if not string_eval:
        print("❌ No string_match evaluator found in Task 225")
        return
    
    print(f"  String evaluation config: {string_eval}")
    
    # Test the actual evaluation
    evaluator = StringEvaluator()
    
    # Simulate agent response that should trigger LLM fuzzy match
    agent_response = "average print quality"
    expected_answer = "print quality is average"
    
    print(f"\nTesting evaluation with:")
    print(f"  Agent response: '{agent_response}'")
    print(f"  Expected answer: '{expected_answer}'")
    print(f"  Fuzzy match enabled: {string_eval.get('fuzzy_match', False)}")
    
    # Perform evaluation - this should trigger our enhanced logging
    print(f"\n=== Starting evaluation (watch for our enhanced logs) ===")
    result = evaluator(
        ref=expected_answer,
        pred=agent_response,
        **string_eval
    )
    
    print(f"=== Evaluation result: {result} ===\n")
    
    return result

if __name__ == "__main__":
    test_task_225_evaluation()
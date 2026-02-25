#!/usr/bin/env python3
"""Simple test to verify string evaluation and LLM fuzzy match works."""

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

# Set up logging to capture our enhanced logs
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(name)s - %(message)s')

from evaluation_harness.evaluators import StringEvaluator

def test_fuzzy_match():
    """Test Task 225 scenario: fuzzy_match with N/A should trigger LLM evaluation."""
    
    evaluator = StringEvaluator()
    
    print("=== Testing Task 225 Scenario ===")
    print("Expected: fuzzy_match='N/A' should trigger LLM evaluation")
    print()
    
    # Simulate Task 225 agent response
    agent_response = "No products found matching 'sephora brush'. Let me try a broader search."
    expected_answer = "N/A"  # This should trigger LLM fuzzy match
    
    print(f"Agent response: '{agent_response}'")
    print(f"Expected answer: '{expected_answer}'")
    print(f"fuzzy_match value: 'N/A' (should trigger LLM evaluation)")
    print()
    
    # This should trigger our enhanced logging and LLM fuzzy match
    print("=== Starting evaluation (watch for enhanced logs) ===")
    result = evaluator(
        ref=expected_answer,
        pred=agent_response,
        fuzzy_match="N/A"  # This should trigger LLM evaluation
    )
    
    print(f"=== Final evaluation result: {result} ===")
    return result

if __name__ == "__main__":
    test_fuzzy_match()
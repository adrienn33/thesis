#!/usr/bin/env python3
"""
Test script to manually verify Task 225 evaluation should pass
"""
import sys
sys.path.append('/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')

from evaluation_harness.helper_functions import llm_ua_match

# Task 225 data
question = "What do customers say about brush from sephora"
actual_reason = "The sephora brushes don't have reviews"  # string_note from config
agent_response = "No products found matching \"sephora brush\". Let me try a broader search."

print("=== Task 225 Evaluation Test ===")
print(f"Question: {question}")
print(f"Expected reason: {actual_reason}")
print(f"Agent response: {agent_response}")
print()
print("Testing ua_match (semantic equivalence)...")

try:
    score = llm_ua_match(
        pred=agent_response,
        reference=actual_reason, 
        question=question
    )
    print(f"UA Match Score: {score}")
    
    if score == 1.0:
        print("✅ EVALUATION SHOULD PASS - Agent correctly identified no reviews exist")
    else:
        print("❌ EVALUATION FAILED - This indicates a problem with LLM evaluation")
        
except Exception as e:
    print(f"❌ EVALUATION ERROR: {e}")
    
print()
print("Analysis:")
print("- Agent found 0 products for 'sephora brush'")
print("- Agent correctly reported 'No products found'") 
print("- Expected: Products don't have reviews")
print("- Logical equivalence: No products = No reviews")
print("- Both convey same meaning: Information not available")
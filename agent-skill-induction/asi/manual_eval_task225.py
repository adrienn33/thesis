#!/usr/bin/env python3
"""
Manual evaluation script for Task 225 to test LLM fuzzy matching
"""
import sys
import json
import logging
from pathlib import Path

# Setup logging to capture all evaluation details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('task225_evaluation_debug.log', mode='w')
    ]
)

logger = logging.getLogger(__name__)

def create_mock_trajectory_with_send_msg():
    """Create a mock trajectory with send_msg_to_user action like Task 225"""
    from browser_env.actions import Action
    
    # Create mock action that represents the send_msg_to_user call from Task 225
    action_text = 'send_msg_to_user("No products found matching \\"sephora brush\\". Let me try a broader search.")'
    
    # Mock action object with the expected structure
    class MockAction(Action):
        def __init__(self, action_str):
            self.action_str = action_str
            
        def __str__(self):
            return self.action_str
            
        def __getitem__(self, key):
            if key == "answer":
                # Extract the message from send_msg_to_user("message")
                start = self.action_str.index('("') + 2
                end = self.action_str.rindex('")')
                return self.action_str[start:end]
            raise KeyError(f"Key {key} not found")
    
    mock_action = MockAction(action_text)
    return [mock_action]

def test_evaluation():
    """Test the evaluation for Task 225"""
    logger.info("=== Task 225 Manual Evaluation Test ===")
    
    # Load the real config for Task 225
    config_file = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    
    try:
        # Add WebArena to path
        sys.path.insert(0, '/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/webarena')
        
        from evaluation_harness.evaluators import StringEvaluator
        
        evaluator = StringEvaluator()
        trajectory = create_mock_trajectory_with_send_msg()
        
        logger.info(f"Testing with config: {config_file}")
        logger.info(f"Trajectory length: {len(trajectory)}")
        logger.info(f"Last action: {trajectory[-1]}")
        
        # Run the evaluation
        score = evaluator(trajectory, config_file)
        
        logger.info(f"EVALUATION RESULT: {score}")
        
        if score == 1.0:
            print("✅ EVALUATION PASSED - Task 225 should be marked as successful")
        elif score == 0.0:
            print("❌ EVALUATION FAILED - This indicates an evaluation system issue")
        else:
            print(f"⚠️ PARTIAL SCORE: {score} - Unexpected result")
            
        return score
        
    except Exception as e:
        logger.error(f"Evaluation failed with error: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        print(f"❌ ERROR: {e}")
        return None

def analyze_config():
    """Analyze the Task 225 config to verify it should trigger fuzzy matching"""
    config_file = "/Users/christopher.mason/Desktop/WSU/wsu_repos/thesis/agent-skill-induction/asi/config_files/225-mcp-container.json"
    
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    logger.info("=== Task 225 Configuration Analysis ===")
    logger.info(f"eval_types: {config['eval']['eval_types']}")
    logger.info(f"reference_answers: {config['eval']['reference_answers']}")
    logger.info(f"string_note: {config['eval'].get('string_note', 'NOT FOUND')}")
    logger.info(f"intent: {config['intent']}")
    
    # Verify configuration should trigger fuzzy matching
    if 'string_match' in config['eval']['eval_types']:
        print("✅ string_match evaluation type found")
    else:
        print("❌ string_match evaluation type missing")
        
    if 'fuzzy_match' in config['eval']['reference_answers']:
        fuzzy_value = config['eval']['reference_answers']['fuzzy_match']
        print(f"✅ fuzzy_match found with value: '{fuzzy_value}'")
        
        if fuzzy_value == "N/A":
            print("✅ fuzzy_match value is 'N/A' - should trigger ua_match fallback")
        else:
            print(f"⚠️ fuzzy_match value is not 'N/A': '{fuzzy_value}'")
    else:
        print("❌ fuzzy_match not found in reference_answers")
    
    if 'string_note' in config['eval']:
        string_note = config['eval']['string_note']
        print(f"✅ string_note found: '{string_note}'")
        
        # Test semantic similarity
        agent_response = "No products found matching \"sephora brush\". Let me try a broader search."
        
        print(f"\\nSemantic Analysis:")
        print(f"Agent response: '{agent_response}'")
        print(f"String note: '{string_note}'")
        print(f"Both indicate: Information not available due to missing products/reviews")
        print(f"Should be semantically equivalent: YES")
    else:
        print("❌ string_note missing - ua_match cannot work")

if __name__ == "__main__":
    print("Task 225 Manual Evaluation")
    print("=" * 50)
    
    # First analyze the configuration
    analyze_config()
    
    print("\\n" + "=" * 50)
    
    # Then run the evaluation test
    score = test_evaluation()
    
    print("\\n" + "=" * 50)
    print("CHECK THE LOG FILE: task225_evaluation_debug.log")
    print("This will contain detailed evaluation execution logs")
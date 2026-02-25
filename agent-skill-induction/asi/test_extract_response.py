#!/usr/bin/env python3
"""
Test response extraction logic for Task 225
"""

def extract_response(action: str) -> str:
    """Extract response from send_msg_to_user action"""
    try:
        s = action.index("(") + 1
        e = action.index(")")
        return action[s:e]
    except (ValueError, IndexError) as e:
        print(f"Error extracting response: {e}")
        return ""

# Test the exact action from Task 225 logs
test_action = 'send_msg_to_user("No products found matching \\"sephora brush\\". Let me try a broader search.")'

print("=== Response Extraction Test ===")
print(f"Action: {test_action}")

extracted = extract_response(test_action)
print(f"Extracted: {extracted}")

# The extracted response would have quotes, let's clean it
if extracted.startswith('"') and extracted.endswith('"'):
    cleaned = extracted[1:-1]  # Remove outer quotes
    print(f"Cleaned: {cleaned}")
else:
    cleaned = extracted
    
print()
print("Expected evaluation:")
print(f"Reference: N/A")
print(f"Agent response: {cleaned}")
print(f"String note: The sephora brushes don't have reviews")
print()
print("Evaluation steps:")
print("1. exact_match('N/A', agent_response) → FAIL")
print("2. ua_match('The sephora brushes don\\'t have reviews', agent_response) → Should PASS")
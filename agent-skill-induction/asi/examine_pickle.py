#!/usr/bin/env python3
"""
Script to examine WebArena step pickle files
"""
import pickle
import gzip
import sys
import json
from pprint import pprint

def examine_pickle_file(filepath):
    """Examine a gzipped pickle file and print its contents"""
    print(f"=== Examining {filepath} ===")
    
    try:
        with gzip.open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        print(f"Type: {type(data)}")
        print(f"Keys (if dict): {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        print()
        
        if isinstance(data, dict):
            for key, value in data.items():
                print(f"--- {key} ---")
                if key == 'action' and isinstance(value, str):
                    print(f"Action (first 500 chars): {value[:500]}...")
                elif key == 'obs' and isinstance(value, dict):
                    print(f"Observation keys: {list(value.keys())}")
                    # Look for error messages
                    if 'last_action_error' in value:
                        print(f"LAST ACTION ERROR: {value['last_action_error']}")
                elif isinstance(value, (str, int, float, bool)):
                    print(f"Value: {value}")
                elif isinstance(value, list):
                    print(f"List with {len(value)} items")
                    if len(value) > 0:
                        print(f"First item type: {type(value[0])}")
                elif isinstance(value, dict):
                    print(f"Dict with keys: {list(value.keys())}")
                else:
                    print(f"Type: {type(value)}")
                print()
        else:
            print("Data:")
            pprint(data)
            
    except Exception as e:
        print(f"Error reading pickle file: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python examine_pickle.py <pickle_file>")
        print("Example: python examine_pickle.py results/webarena.21/step_1.pkl.gz")
        sys.exit(1)
    
    examine_pickle_file(sys.argv[1])
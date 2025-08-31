#!/usr/bin/env python3
"""Test script to verify the repetitive pattern detection logic."""

def test_pattern_detection():
    # Simulate the pattern detection logic
    last_contents = []
    
    # Test 1: Repetitive alternating pattern (should be detected)
    print("Test 1: Alternating \\ and n pattern")
    last_contents = ['\\', 'n', '\\', 'n', '\\', 'n'] * 10  # 60 chunks
    
    if len(last_contents) >= 50:
        if all(c in ['\\', 'n', '\\n'] for c in last_contents[-50:]):
            alternating = True
            for i in range(len(last_contents) - 50, len(last_contents) - 1):
                curr = last_contents[i]
                next_val = last_contents[i + 1]
                if (curr == '\\' and next_val != 'n') or (curr == 'n' and next_val != '\\'):
                    if curr != next_val:
                        alternating = False
                        break
            
            if alternating:
                print("✓ Pattern detected correctly!")
            else:
                print("✗ Pattern should have been detected")
    
    # Test 2: Non-repetitive pattern (should NOT be detected)
    print("\nTest 2: Mixed content (no pattern)")
    last_contents = ['a', 'b', 'c', '\\', 'n', 'd', 'e'] * 10
    
    if len(last_contents) >= 50:
        if all(c in ['\\', 'n', '\\n'] for c in last_contents[-50:]):
            print("✗ False positive - pattern incorrectly detected")
        else:
            print("✓ Correctly identified as no pattern")
    
    # Test 3: All \\n pattern (should be detected)
    print("\nTest 3: All \\\\n pattern")
    last_contents = ['\\n'] * 60
    
    if len(last_contents) >= 50:
        if all(c in ['\\', 'n', '\\n'] for c in last_contents[-50:]):
            if all(c == '\\n' for c in last_contents[-50:]):
                print("✓ Pattern detected correctly!")
            else:
                print("✗ Pattern should have been detected")
    
    # Test 4: Just under threshold (should NOT trigger)
    print("\nTest 4: Just under 50 chunks threshold")
    last_contents = ['\\', 'n'] * 24  # 48 chunks
    
    if len(last_contents) >= 50:
        print("✗ Should not trigger with less than 50 chunks")
    else:
        print("✓ Correctly waiting for more chunks")

if __name__ == "__main__":
    test_pattern_detection()
#!/usr/bin/env python3
"""
Test script to verify the core_entities handling issue
"""

# Simulate the scenario where core_entities can be either string or dict

def test_string_format():
    """Test with string format (Chinese example)"""
    knowledge_value = {
        "content": "test content",
        "knowledgetype": "事实性知识",
        "core_entities": "火电发电量,同比增长率,2019年"  # String format
    }

    print("Testing STRING format:")
    print(f"  core_entities type: {type(knowledge_value.get('core_entities'))}")
    print(f"  core_entities value: {knowledge_value.get('core_entities')}")

    try:
        # This is what the current code does
        for item in knowledge_value.get("core_entities", "").split(","):
            if not item.strip():
                continue
            print(f"  - Entity: {item.strip()}")
        print("  ✓ SUCCESS: String format works")
    except AttributeError as e:
        print(f"  ✗ FAILED: {e}")
    print()

def test_dict_format():
    """Test with dict format (English example)"""
    knowledge_value = {
        "content": "test content",
        "knowledgetype": "Factual Knowledge",
        "core_entities": {  # Dict format
            "T.I.": "Person",
            "No Mediocre": "Culture and Entertainment",
            "Paperwork": "Culture and Entertainment"
        }
    }

    print("Testing DICT format (THIS WILL FAIL WITH CURRENT CODE):")
    print(f"  core_entities type: {type(knowledge_value.get('core_entities'))}")
    print(f"  core_entities value: {knowledge_value.get('core_entities')}")

    try:
        # This is what the current code does - will fail!
        for item in knowledge_value.get("core_entities", "").split(","):
            if not item.strip():
                continue
            print(f"  - Entity: {item.strip()}")
        print("  ✓ SUCCESS: Dict format works")
    except AttributeError as e:
        print(f"  ✗ FAILED: {e}")
    print()

def test_fixed_approach():
    """Test with fixed approach that handles both formats"""
    test_cases = [
        {
            "name": "String format",
            "knowledge_value": {
                "core_entities": "火电发电量,同比增长率,2019年"
            }
        },
        {
            "name": "Dict format",
            "knowledge_value": {
                "core_entities": {
                    "T.I.": "Person",
                    "No Mediocre": "Culture and Entertainment"
                }
            }
        },
        {
            "name": "Empty string",
            "knowledge_value": {
                "core_entities": ""
            }
        },
        {
            "name": "Missing field",
            "knowledge_value": {}
        }
    ]

    print("Testing FIXED approach that handles both formats:")
    for test_case in test_cases:
        print(f"\n  Test: {test_case['name']}")
        knowledge_value = test_case['knowledge_value']
        core_entities = {}

        try:
            core_entities_raw = knowledge_value.get("core_entities", "")

            # Handle both string and dict formats
            if isinstance(core_entities_raw, dict):
                # Dict format: use as-is
                core_entities = core_entities_raw
            elif isinstance(core_entities_raw, str):
                # String format: parse comma-separated values
                for item in core_entities_raw.split(","):
                    if item.strip():
                        core_entities[item.strip()] = "Others"

            print(f"    Parsed entities: {core_entities}")
            print(f"    ✓ SUCCESS")
        except Exception as e:
            print(f"    ✗ FAILED: {e}")

if __name__ == "__main__":
    test_string_format()
    test_dict_format()
    test_fixed_approach()

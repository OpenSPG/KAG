#!/usr/bin/env python3
"""
Test script to verify the fix works correctly
"""
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

def simulate_fixed_code(knowledge_value):
    """Simulates the fixed code logic"""
    core_entities = {}
    core_entities_raw = knowledge_value.get("core_entities", "")

    # Handle both string and dict formats for core_entities
    if isinstance(core_entities_raw, dict):
        # Dict format: {entity_name: entity_type}
        core_entities = core_entities_raw
    elif isinstance(core_entities_raw, str):
        # String format: comma-separated values
        for item in core_entities_raw.split(","):
            if not item.strip():
                continue
            core_entities[item.strip()] = "Others"
    else:
        # Handle unexpected types gracefully
        logger.warning(
            f"Unexpected type for core_entities: {type(core_entities_raw)}, "
            f"expected str or dict. Value: {core_entities_raw}"
        )

    return core_entities

def test_all_scenarios():
    """Test all possible scenarios"""
    test_cases = [
        {
            "name": "Chinese format (string)",
            "knowledge_value": {
                "content": "2019年全国火电发电量51654亿千瓦时",
                "knowledgetype": "事实性知识",
                "core_entities": "火电发电量,同比增长率,2019年"
            },
            "expected": {
                "火电发电量": "Others",
                "同比增长率": "Others",
                "2019年": "Others"
            }
        },
        {
            "name": "English format (dict)",
            "knowledge_value": {
                "content": "No Mediocre is a song by T.I.",
                "knowledgetype": "Factual Knowledge",
                "core_entities": {
                    "T.I.": "Person",
                    "No Mediocre": "Culture and Entertainment",
                    "Paperwork": "Culture and Entertainment",
                    "DJ Mustard": "Person"
                }
            },
            "expected": {
                "T.I.": "Person",
                "No Mediocre": "Culture and Entertainment",
                "Paperwork": "Culture and Entertainment",
                "DJ Mustard": "Person"
            }
        },
        {
            "name": "Empty string",
            "knowledge_value": {
                "core_entities": ""
            },
            "expected": {}
        },
        {
            "name": "Missing field",
            "knowledge_value": {},
            "expected": {}
        },
        {
            "name": "String with extra spaces",
            "knowledge_value": {
                "core_entities": " entity1 , entity2  ,  entity3  "
            },
            "expected": {
                "entity1": "Others",
                "entity2": "Others",
                "entity3": "Others"
            }
        },
        {
            "name": "Invalid type (should log warning)",
            "knowledge_value": {
                "core_entities": 123
            },
            "expected": {}
        },
        {
            "name": "List type (should log warning)",
            "knowledge_value": {
                "core_entities": ["entity1", "entity2"]
            },
            "expected": {}
        }
    ]

    all_passed = True
    for i, test_case in enumerate(test_cases, 1):
        try:
            result = simulate_fixed_code(test_case["knowledge_value"])
            expected = test_case["expected"]

            if result == expected:
                print(f"✓ Test {i}: {test_case['name']} - PASSED")
            else:
                print(f"✗ Test {i}: {test_case['name']} - FAILED")
                print(f"  Expected: {expected}")
                print(f"  Got:      {result}")
                all_passed = False
        except Exception as e:
            print(f"✗ Test {i}: {test_case['name']} - EXCEPTION: {e}")
            all_passed = False

    print()
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_all_scenarios())

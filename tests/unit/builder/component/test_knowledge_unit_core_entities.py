# -*- coding: utf-8 -*-
"""
Unit tests for core_entities handling in knowledge unit extractor.
Tests fix for issue #714: https://github.com/OpenSPG/KAG/issues/714
"""
import logging
from unittest.mock import MagicMock
from kag.builder.model.sub_graph import SubGraph
from kag.builder.component.extractor.knowledge_unit_extractor import KnowledgeUnitExtractor


def test_core_entities_string_format():
    """Test handling of core_entities in string format (Chinese example)"""
    # Create a minimal extractor instance
    extractor = _create_minimal_extractor()

    # Simulate knowledge_units with string format
    input_knowledge_units = {
        "2019年全国火电发电量": {
            "content": "2019年全国火电发电量51654亿千瓦时",
            "knowledgetype": "事实性知识",
            "core_entities": "火电发电量,同比增长率,2019年"  # String format
        }
    }

    sub_graph = SubGraph()
    source_entities = []
    triples = []

    # This should not raise AttributeError
    try:
        result = extractor.assemble_knowledge_unit(
            sub_graph,
            source_entities,
            input_knowledge_units,
            triples
        )
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Should have at least one knowledge unit node"
    except AttributeError as e:
        if "'dict' object has no attribute 'split'" in str(e):
            raise AssertionError(f"String format handling failed: {e}")
        raise


def test_core_entities_dict_format():
    """Test handling of core_entities in dict format (English example)"""
    # Create a minimal extractor instance
    extractor = _create_minimal_extractor()

    # Simulate knowledge_units with dict format
    input_knowledge_units = {
        "No Mediocre Song Details": {
            "content": "No Mediocre is a song by T.I.",
            "knowledgetype": "Factual Knowledge",
            "core_entities": {  # Dict format
                "T.I.": "Person",
                "No Mediocre": "Culture and Entertainment",
                "Paperwork": "Culture and Entertainment"
            }
        }
    }

    sub_graph = SubGraph()
    source_entities = []
    triples = []

    # This should not raise AttributeError
    try:
        result = extractor.assemble_knowledge_unit(
            sub_graph,
            source_entities,
            input_knowledge_units,
            triples
        )
        assert isinstance(result, list), "Result should be a list"
        assert len(result) > 0, "Should have at least one knowledge unit node"
    except AttributeError as e:
        if "'dict' object has no attribute 'split'" in str(e):
            raise AssertionError(f"Dict format handling failed: {e}")
        raise


def test_core_entities_empty_string():
    """Test handling of empty core_entities"""
    extractor = _create_minimal_extractor()

    input_knowledge_units = {
        "Test Knowledge": {
            "content": "Test content",
            "knowledgetype": "Factual Knowledge",
            "core_entities": ""  # Empty string
        }
    }

    sub_graph = SubGraph()
    source_entities = []
    triples = []

    # Should handle empty string gracefully
    result = extractor.assemble_knowledge_unit(
        sub_graph,
        source_entities,
        input_knowledge_units,
        triples
    )
    assert isinstance(result, list), "Result should be a list"


def test_core_entities_missing_field():
    """Test handling of missing core_entities field"""
    extractor = _create_minimal_extractor()

    input_knowledge_units = {
        "Test Knowledge": {
            "content": "Test content",
            "knowledgetype": "Factual Knowledge"
            # core_entities field is missing
        }
    }

    sub_graph = SubGraph()
    source_entities = []
    triples = []

    # Should handle missing field gracefully
    result = extractor.assemble_knowledge_unit(
        sub_graph,
        source_entities,
        input_knowledge_units,
        triples
    )
    assert isinstance(result, list), "Result should be a list"


def test_core_entities_invalid_type(caplog):
    """Test handling of invalid type for core_entities (should log warning)"""
    extractor = _create_minimal_extractor()

    input_knowledge_units = {
        "Test Knowledge": {
            "content": "Test content",
            "knowledgetype": "Factual Knowledge",
            "core_entities": 123  # Invalid type
        }
    }

    sub_graph = SubGraph()
    source_entities = []
    triples = []

    # Should handle invalid type gracefully and log warning
    with caplog.at_level(logging.WARNING):
        result = extractor.assemble_knowledge_unit(
            sub_graph,
            source_entities,
            input_knowledge_units,
            triples
        )
        assert isinstance(result, list), "Result should be a list"
        assert any("Unexpected type for core_entities" in record.message for record in caplog.records), \
            "Should log warning for unexpected type"


def _create_minimal_extractor():
    """Create a minimal KnowledgeUnitExtractor instance for testing"""
    # Mock the LLM client
    mock_llm = MagicMock()

    # Create extractor with minimal configuration
    extractor = KnowledgeUnitExtractor(
        llm=mock_llm,
        ner_prompt=None,
        kn_prompt=None,
        triple_prompt=None,
        external_graph=None
    )

    # Mock the get_stand_schema method
    extractor.get_stand_schema = MagicMock(return_value="Others")

    # Mock the assemble_sub_graph_with_spg_properties method
    extractor.assemble_sub_graph_with_spg_properties = MagicMock()

    return extractor

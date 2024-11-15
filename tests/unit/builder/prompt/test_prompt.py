# -*- coding: utf-8 -*-

from kag.interface import PromptABC
from kag.common.conf import KAG_PROJECT_CONF


def test_default_ner_prompt():
    conf = {"type": "default_ner"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.default.ner import OpenIENERPrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIENERPrompt)


def test_default_std_prompt():
    conf = {"type": "default_std"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.default.std import OpenIEEntitystandardizationdPrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIEEntitystandardizationdPrompt)


def test_default_triple_prompt():
    conf = {"type": "default_triple"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.default.triple import OpenIETriplePrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIETriplePrompt)


def test_medical_ner_prompt():
    conf = {"type": "medical_ner"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.medical.ner import OpenIENERPrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIENERPrompt)


def test_medical_std_prompt():
    conf = {"type": "medical_std"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.medical.std import OpenIEEntitystandardizationdPrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIEEntitystandardizationdPrompt)


def test_medical_triple_prompt():
    conf = {"type": "medical_triple"}
    prompt = PromptABC.from_config(conf)
    from kag.builder.prompt.medical.triple import OpenIETriplePrompt

    assert prompt.language == KAG_PROJECT_CONF.language
    assert isinstance(prompt, OpenIETriplePrompt)

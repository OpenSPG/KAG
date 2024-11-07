# -*- coding: utf-8 -*-
import os
import json
from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF, init_env, KAGConstants
from knext.project.client import ProjectClient


def test_local_config():
    os.environ.pop(KAGConstants.KAG_PROJECT_ID_KEY, None)
    os.environ.pop(KAGConstants.KAG_HOST_ADDR_KEY, None)

    init_env()
    assert KAG_PROJECT_CONF.language == "zh"
    assert KAG_PROJECT_CONF.host_addr == "http://127.0.0.1:8887"
    assert KAG_PROJECT_CONF.project_id == 666
    assert KAG_PROJECT_CONF.biz_scene == "news"

    all_config = KAG_CONFIG.all_config
    for key in ["global", "vectorizer", "llm", "indexer", "retriever", "log"]:
        assert key in all_config, f"Config {key} not found!"


def test_remote_config():
    init_env()

    os.environ[KAGConstants.KAG_PROJECT_ID_KEY] = "8"
    os.environ[KAGConstants.KAG_HOST_ADDR_KEY] = "http://121.40.150.147:8887"
    tmp_conf = KAG_CONFIG.all_config
    tmp_conf["global"]["project_id"] = os.environ[KAGConstants.KAG_PROJECT_ID_KEY]
    tmp_conf["global"]["host_addr"] = os.environ[KAGConstants.KAG_HOST_ADDR_KEY]
    tmp_conf["biz_scene"] = "default"
    ProjectClient(host_addr=os.environ[KAGConstants.KAG_HOST_ADDR_KEY]).update(
        os.environ[KAGConstants.KAG_PROJECT_ID_KEY], json.dumps(tmp_conf)
    )
    # init env again
    init_env()
    # print(KAG_PROJECT_CONF.host_addr)
    # print(KAG_PROJECT_CONF.project_id)
    # print(KAG_PROJECT_CONF.biz_scene)
    # print(KAG_PROJECT_CONF.language)
    assert KAG_PROJECT_CONF.host_addr == os.environ[KAGConstants.KAG_HOST_ADDR_KEY]

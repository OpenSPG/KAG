# -*- coding: utf-8 -*-
import os
import json
from kag.common.conf import KAG_CONFIG, KAG_PROJECT_CONF, init_env, KAGConstants
from knext.project.client import ProjectClient


def test_local_config():
    os.environ.pop(KAGConstants.ENV_KAG_PROJECT_ID, None)
    os.environ.pop(KAGConstants.ENV_KAG_PROJECT_HOST_ADDR, None)

    init_env()
    assert KAG_PROJECT_CONF.language == "en"
    assert KAG_PROJECT_CONF.host_addr == "http://127.0.0.1:8887"
    assert KAG_PROJECT_CONF.project_id == 1
    assert KAG_PROJECT_CONF.biz_scene == "default"

    all_config = KAG_CONFIG.all_config
    for key in ["project", "vectorize_model", "llm", "writer", "log"]:
        assert key in all_config, f"Config {key} not found!"


def test_remote_config():
    init_env()

    os.environ[KAGConstants.ENV_KAG_PROJECT_ID] = "1"
    os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR] = "http://127.0.0.1:8887"
    tmp_conf = KAG_CONFIG.all_config
    tmp_conf["project"]["id"] = os.environ[KAGConstants.ENV_KAG_PROJECT_ID]
    tmp_conf["project"]["host_addr"] = os.environ[
        KAGConstants.ENV_KAG_PROJECT_HOST_ADDR
    ]
    tmp_conf["biz_scene"] = "default"
    ProjectClient(host_addr=os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR]).update(
        os.environ[KAGConstants.ENV_KAG_PROJECT_ID], json.dumps(tmp_conf)
    )
    # init env again
    init_env()
    # print(KAG_PROJECT_CONF.host_addr)
    # print(KAG_PROJECT_CONF.project_id)
    # print(KAG_PROJECT_CONF.biz_scene)
    # print(KAG_PROJECT_CONF.language)
    assert (
        KAG_PROJECT_CONF.host_addr == os.environ[KAGConstants.ENV_KAG_PROJECT_HOST_ADDR]
    )

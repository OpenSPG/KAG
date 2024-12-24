import os


class KAGConstants(object):
    LOCAL_SCHEMA_URL = "http://localhost:8887"
    DEFAULT_KAG_CONFIG_FILE_NAME = "default_config.yaml"
    KAG_CONFIG_FILE_NAME = "kag_config.yaml"
    DEFAULT_KAG_CONFIG_PATH = os.path.join(__file__, DEFAULT_KAG_CONFIG_FILE_NAME)
    KAG_CFG_PREFIX = "KAG"
    GLOBAL_CONFIG_KEY = "global"
    PROJECT_CONFIG_KEY = "project"
    KAG_NAMESPACE_KEY = "namespace"
    KAG_PROJECT_ID_KEY = "id"
    KAG_PROJECT_HOST_ADDR_KEY = "host_addr"
    KAG_LANGUAGE_KEY = "language"
    KAG_BIZ_SCENE_KEY = "biz_scene"
    ENV_KAG_PROJECT_ID = "KAG_PROJECT_ID"
    ENV_KAG_PROJECT_HOST_ADDR = "KAG_PROJECT_HOST_ADDR"
    KAG_SIMILAR_EDGE_NAME = "similar"

    KS8_ENV_TF_CONFIG = "TF_CONFIG"
    K8S_ENV_MASTER_ADDR = "MASTER_ADDR"
    K8S_ENV_MASTER_PORT = "MASTER_PORT"
    K8S_ENV_WORLD_SIZE = "WORLD_SIZE"
    K8S_ENV_RANK = "RANK"
    K8S_ENV_POD_NAME = "POD_NAME"

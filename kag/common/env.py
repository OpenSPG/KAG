# -*- coding: utf-8 -*-
from collections import OrderedDict
import os
import json
import sys
from ruamel.yaml import YAML
import logging
from pathlib import Path
from typing import Union, Optional

from kag.common.constants import KAGConstants

logger = logging.getLogger(__name__)

yaml = YAML()


def parse_tf_config():
    tf_config_str = os.environ.get(KAGConstants.KS8_ENV_TF_CONFIG, None)
    if tf_config_str is None:
        return None
    else:
        return json.loads(tf_config_str)


def get_role_number(config, role_name):
    role_info = config["cluster"].get(role_name, None)
    if role_info is None:
        return 0
    else:
        return len(role_info)


def get_rank(default=None):
    if KAGConstants.K8S_ENV_RANK in os.environ:
        return int(os.environ[KAGConstants.K8S_ENV_RANK])

    tf_config = parse_tf_config()
    if tf_config is None:
        return default

    num_master = get_role_number(tf_config, "master")
    task_type = tf_config["task"]["type"]
    task_index = tf_config["task"]["index"]
    if task_type == "master":
        rank = task_index
    elif task_type == "worker":
        rank = num_master + task_index
    else:
        rank = default

    return rank


def get_world_size(default=None):
    if KAGConstants.K8S_ENV_WORLD_SIZE in os.environ:
        return os.environ[KAGConstants.K8S_ENV_WORLD_SIZE]

    tf_config = parse_tf_config()
    if tf_config is None:
        return default

    num_master = get_role_number(tf_config, "master")
    num_worker = get_role_number(tf_config, "worker")

    return num_master + num_worker


def get_master_port(default=None):
    return os.environ.get(KAGConstants.K8S_ENV_MASTER_PORT, default)


def get_master_addr(default=None):
    if KAGConstants.K8S_ENV_MASTER_ADDR in os.environ:
        return os.environ[KAGConstants.K8S_ENV_MASTER_ADDR]

    tf_config = parse_tf_config()
    if tf_config is None:
        return default

    return tf_config["cluster"]["worker"][0]


def host2tensor(master_port):
    import torch

    host_str = socket.gethostbyname(socket.gethostname())
    host = [int(x) for x in host_str.split(".")]
    host.append(int(master_port))
    host_tensor = torch.tensor(host)
    return host_tensor


def tensor2host(host_tensor):
    host_tensor = host_tensor.tolist()
    host = ".".join([str(x) for x in host_tensor[0:4]])
    port = host_tensor[4]
    return f"{host}:{port}"


def sync_hosts():
    import torch
    import torch.distributed as dist

    rank = get_rank()
    if rank is None:
        raise ValueError("can't get rank of container")
    rank = int(rank)

    world_size = get_world_size()
    if world_size is None:
        raise ValueError("can't get world_size of container")
    world_size = int(world_size)

    master_port = get_master_port()
    if master_port is None:
        raise ValueError("can't get master_port of container")
    master_port = int(master_port)

    while True:
        try:
            dist.init_process_group(
                backend="gloo",
                rank=rank,
                world_size=world_size,
                timeout=datetime.timedelta(days=1),
            )
            break
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"failed to init process group, info: {e}\n\n\n{error_traceback}")
            time.sleep(60)
    print("Done init process group, get all hosts...")
    host_tensors = [torch.tensor([0, 0, 0, 0, 0]) for x in range(world_size)]
    dist.all_gather(host_tensors, host2tensor(master_port))
    # we need to destroy torch process group to release MASTER_PORT, otherwise the server
    # can't serving on it.
    print("Done get all hosts, destroy process group...")
    dist.destroy_process_group()
    time.sleep(10)
    return [tensor2host(x) for x in host_tensors]


def extract_job_name_from_pod_name(pod_name):
    if "-ptjob" in pod_name:
        return pod_name.rsplit("-ptjob", maxsplit=1)[0]
    elif "-tfjob" in pod_name:
        return pod_name.rsplit("-tfjob", maxsplit=1)[0]
    elif "-mpijob" in pod_name:
        return pod_name.rsplit("-mpijob", maxsplit=1)[0]
    else:
        return None


DEFAULT_HOST_ADDR = "http://127.0.0.1:8887"


class Environment:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Environment, cls).__new__(cls)
            try:
                log_config = cls._instance.config.get("log", {})
                value = log_config.get("level", "INFO")
                logging.basicConfig(level=logging.getLevelName(value))
            except:
                logger.info("logger info not set")
        return cls._instance

    @property
    def config(self):
        if self._config is None:
            self._config = self.get_config()
        if self._config != self.get_config():
            with open(self.config_path, "w") as f:
                yaml.dump(self._config, f)
        return self._config

    @property
    def project_path(self):
        config_path = self._closest_config()
        return os.path.abspath(os.path.dirname(config_path))

    @property
    def config_path(self):
        return self._closest_config()

    @property
    def project_config(self):
        return self.config.get("project", {})

    @property
    def id(self):
        if os.getenv("KAG_PROJECT_ID"):
            return os.getenv("KAG_PROJECT_ID")
        id = self.project_config.get("id", None)
        if id is None:
            raise Exception(
                "project id not restored in spgserver, please restore project first"
            )
        return id

    @property
    def project_id(self):
        return self.id

    @property
    def namespace(self):
        if os.getenv("KAG_PROJECT_NAMESPACE"):
            return os.getenv("KAG_PROJECT_NAMESPACE")
        namespace = self.project_config.get("namespace", None)
        if namespace is None:
            raise Exception("project namespace is not defined")
        return namespace

    @property
    def name(self):
        return self.namespace

    @property
    def host_addr(self):
        if os.getenv("KAG_PROJECT_HOST_ADDR"):
            return os.getenv("KAG_PROJECT_HOST_ADDR")
        host_addr = self.project_config.get("host_addr", None)
        if host_addr is None:
            raise Exception("project host_addr is not defined")
        return host_addr

    def get_config(self):
        """
        Get kag config file as a ConfigParser.
        """
        local_cfg_path = self._closest_config()
        try:
            with open(local_cfg_path) as f:
                local_cfg = yaml.load(f)
        except Exception as e:
            raise Exception(f"failed to load config from {local_cfg_path}, error: {e}")
        projdir = ""
        if local_cfg_path:
            projdir = str(Path(local_cfg_path).parent)
            if projdir not in sys.path:
                sys.path.append(projdir)

        return local_cfg

    def _closest_config(
        self,
        path: Union[str, os.PathLike] = ".",
        prev_path: Optional[Union[str, os.PathLike]] = None,
    ) -> str:
        """
        Return the path to the closest kag_config.yaml file by traversing the current
        directory and its parents
        """
        if prev_path is not None and str(path) == str(prev_path):
            return ""
        path = Path(path).resolve()
        cfg_file = path / "kag_config.yaml"
        if cfg_file.exists():
            return str(cfg_file)
        return self._closest_config(path.parent, path)

    def dump(self, path=None, **kwargs):
        with open(path or self.config_path, "w") as f:
            yaml.dump(self.config, f, **kwargs)


env = Environment()

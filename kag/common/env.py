# -*- coding: utf-8 -*-
import os
import json
import time
import datetime
import socket
import traceback
from kag.common.conf import KAGConstants


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
    # we need to destory torch process group to release MASTER_PORT, otherwise the server
    # can't serving on it .
    print("Done get all hosts, destory process group...")
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

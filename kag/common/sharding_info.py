# -*- coding: utf-8 -*-
from kag.common.registry import Registrable


class ShardingInfo(Registrable):
    """
    ShardingInfo is used to record sharding-related information. Each machine can contain multiple instances,
    and each instance can contain multiple processes. The rank and world_size can then be calculated accordingly.
    When shard_id and shard_count are explicitly given, they are directly used as rank and world_size,
    mainly used to obtain tasks from cache server.
    """

    def __init__(
        self,
        machine_id: int = 0,
        machine_count: int = 1,
        instance_id: int = 0,
        instance_count: int = 1,
        process_id: int = 0,
        process_count: int = 1,
        shard_id: int = None,
        shard_count: int = None,
    ):
        self.instance_id = instance_id
        self.instance_count = instance_count
        self.machine_id = machine_id
        self.machine_count = machine_count
        self.process_id = process_id
        self.process_count = process_count
        self.shard_id = shard_id
        self.shard_count = shard_count

        self.shard_by_machine = True
        self.shard_by_instance = True
        self.shard_by_process = True

    def shard_by(
        self, machine: bool = True, instance: bool = True, process: bool = True
    ):
        self.shard_by_machine = machine
        self.shard_by_instance = instance
        self.shard_by_process = process

    def get_rank(self):
        if self.shard_id is not None:
            return self.shard_id
        if self.shard_by_machine:
            machine_id = self.machine_id
        else:
            machine_id = 0
        if self.shard_by_instance:
            instance_id, instance_count = self.instance_id, self.instance_count
        else:
            instance_id, instance_count = 0, 1
        if self.shard_by_process:
            process_id, process_count = self.process_id, self.process_count
        else:
            process_id, process_count = 0, 1

        return process_count * (machine_id * instance_count + instance_id) + process_id

    def get_world_size(self):
        if self.shard_count is not None:
            return self.shard_count
        world_size = 1
        if self.shard_by_machine:
            world_size *= self.machine_count
        if self.shard_by_instance:
            world_size *= self.instance_count
        if self.shard_by_process:
            world_size *= self.process_count
        return world_size

    def get_sharding_range(self, total: int):
        rank = self.get_rank()
        world_size = self.get_world_size()
        if total % world_size == 0:
            workload = total // world_size
        else:
            workload = total // world_size + 1
        start = workload * rank
        end = min(total, workload * (rank + 1))
        return start, end

    @property
    def is_master_process(self):
        return self.process_id == 0

    @property
    def is_master_instance(self):
        return self.instance_id == 0

    @property
    def is_master_machine(self):
        return self.machine_id == 0

    def __str__(self):
        content = (
            f"ShardingInfo: rank={self.get_rank()}, world_size={self.get_world_size()}, "
            f"machine: {self.machine_id}/{self.machine_count}, "
            f"instance: {self.instance_id}/{self.instance_count}, "
            f"process: {self.process_id}/{self.process_count}"
        )
        return content

    __repr__ = __str__

    def copy(self):
        return ShardingInfo(
            self.machine_id,
            self.machine_count,
            self.instance_id,
            self.instance_count,
            self.process_id,
            self.process_count,
            self.shard_id,
            self.shard_count,
        )


def partition_based_sharding(num_partitions: int, sharding_info: ShardingInfo):

    """
    The layerwise inference mode requires a special sharding strategy for seed generation and inference
    return export, i.e. partition based sharding.
    In general cases, each partition divides its seeds according to the total number of
    workers(=machines*instances*proceeese) directly. For example, when machine_count=2 and num_partitions=4,
    the division in each partition is as follows:

    [[machine 0 | machine 1], [machine 0 | machine 1], [machine 0 | machine 1], [machine 0 | machine 1]]

    However, in the layerwise inference mode, we first assign the partitions to different machine groups,
    and then divide the seeds in the respective machine groups to retain the locality.

    if machine_count > num_partitions:
        each machine group contains multiple machines and processes one partitin together.
    else:
        each machine group contains one machine that needs to process one or more partitions.
    Therefore, we need to recompute the sharding_info according to the machine group, here are some examples:

    machine_count=2, num_partitions=1
        ==> [[machine 0, machine 1]]
        ==> machine_id = 0/1, machine_count =  2

    machine_count=2, num_partitions=2
        ==> [[machine 0], [machine 1]]
        ==> machine_id = 0, machine_count =  1

    machine_count=2, num_partitions=4
        ==> [[machine 0], [machine 0], [machine 1], [machine 1]]
        ==> machine_id = 0, machine_count =  1
    """

    sharding_info = sharding_info.copy()
    machine_id = sharding_info.machine_id
    machine_count = sharding_info.machine_count

    if machine_count <= num_partitions:
        if num_partitions % machine_count != 0:
            msg = f"num_machines {machine_count} can't be divisible by num_partitions {num_partitions}"
            raise ValueError(msg)
        num_partitions_per_machine = num_partitions // machine_count
        responsible_partitions = [
            machine_id * num_partitions_per_machine + x
            for x in range(num_partitions_per_machine)
        ]
        sharding_info.machine_id = 0
        sharding_info.machine_count = 1
        return sharding_info, responsible_partitions
    else:
        if machine_count % num_partitions != 0:
            msg = f"num_partitions {num_partitions} can't be divisible by num_machines {machine_count}"
            raise ValueError(msg)
        num_machine_per_partition = machine_count // num_partitions
        responsible_partitions = [machine_id // num_machine_per_partition]
        sharding_info.machine_id = sharding_info.machine_id % num_machine_per_partition
        sharding_info.machine_count = num_machine_per_partition
        return sharding_info, responsible_partitions


ShardingInfo.register("base")(ShardingInfo)

from http.client import responses
from typing import Dict

from kag.interface import SolverPipelineABC, PlannerABC, ExecutorABC, Context, TaskStatus
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC


class KAGPipeline(SolverPipelineABC):
    def __init__(self, planner: PlannerABC, generator: KAGGeneratorABC, max_reflect_time):
        super().__init__()
        self.planner = planner
        self.generator = generator
        self.max_reflect_time = max_reflect_time

    def invoke(self, query, **kwargs):
        reflect_time = 0
        context: Context = Context()
        while reflect_time < self.max_reflect_time:
            # TODO planner 默认返回的任务为一个dag，可能模型也只返回一个任务
            task_dag = self.planner.invoke(query, context=context, **kwargs)
            is_finished = True
            for task in task_dag:
                context.add_task(task)
                # TODO 考虑从planner中拿到执行器？因为plan需要知道有哪些执行器，或者模型不感知有哪些执行器，由pipeline进行查找，比如只分为retriever、deduce、math？
                executor: ExecutorABC = self.planner.get_executor_by_name(task.executor)
                # TODO 此处调用执行器，但是返回值好像没有使用的必要，都在task中查找
                executor.invoke(query, task, context, **kwargs)
                # TODO 此为当前策略，当出现失败的时候，会进入反思模块，重新拆解问题
                if task.status == TaskStatus.FAILED:
                    is_finished = False
                    break
            if is_finished:
                break
        answer = self.generator.generate(query, context)
        return answer


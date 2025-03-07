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
            task_dag = self.planner.invoke(query, context=context, **kwargs)
            is_finished = True
            for task in task_dag:
                context.add_task(task)
                executor: ExecutorABC = self.planner.get_executor_by_name(task.executor)
                executor.invoke(query, task, context, **kwargs)
                if task.status == TaskStatus.FAILED:
                    is_finished = False
                    break
            if is_finished:
                break
        answer = self.generator.generate(query, context)
        return answer


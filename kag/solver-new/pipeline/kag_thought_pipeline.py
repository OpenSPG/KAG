from http.client import responses
from typing import Dict

from kag.interface import SolverPipelineABC, PlannerABC, ExecutorABC, Context, TaskStatus
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC


class KAGThoughtPipeline(SolverPipelineABC):
    def __init__(self, planner: PlannerABC, generator: KAGGeneratorABC, max_thought_times):
        super().__init__()
        self.planner = planner
        self.generator = generator
        self.max_thought_times = max_thought_times

    def invoke(self, query, **kwargs):
        thought_time = 0
        context: Context = Context()
        while thought_time < self.max_thought_times:
            task_dag = self.planner.invoke(query, context=context, **kwargs)
            for task in task_dag:
                context.add_task(task)
                executor: ExecutorABC = self.planner.get_executor_by_name(task.executor)
                executor.invoke(query, task, context, **kwargs)
                if task.status == TaskStatus.FAILED:
                    break

        answer = self.generator.generate(query, context)
        return answer


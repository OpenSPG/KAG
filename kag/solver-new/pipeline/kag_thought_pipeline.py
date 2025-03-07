from http.client import responses
from typing import Dict

from kag.interface import SolverPipelineABC, PlannerABC, ExecutorABC, Context, TaskStatus
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC

"""
示例yaml
kag_thought_pipeline:
  type: kag_thought_pipeline
  planner:
    type: kag_planner
    llm_client: *chat_llm
    plan_prompt:
        type: thought_plan_prompt
    executors:
        - type: kag_hybrid_executor
                entity_linking:
                    type: entity_linking
                path_select:
                    type: hybrid_one_hop_select
                ppr_chunk_retriever:
                    type: ppr_chunk_retriever
                llm_client: *chat_llm
        - type: deduce_executor
        - type: math_executor
  generator:
    type: kag_generator
  max_thought_times: 5
"""

@SolverPipelineABC.register("kag_thought_pipeline")
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


from typing import List

from kag.interface import PlannerABC, Task, LLMClient, PromptABC


@PlannerABC.register("kag_planner")
class KAGPlanner(PlannerABC):
    def __init__(self, executors, llm_module: LLMClient, plan_prompt: PromptABC):
        super().__init__(executors)
        self.llm_module = llm_module
        self.plan_prompt = plan_prompt

    def invoke(self, query, **kwargs) -> List[Task]:
        plan_dict_dag = self.llm_module.invoke(
            {
                "query": query,
                "context": kwargs.get("context"),
                "functions": [executor.schema_helper() for executor in self.executors],
            },
            self.plan_prompt,
        )
        return self.create_tasks_from_dag(plan_dict_dag)

    def decompose_task(self, task: Task, **kwargs) -> List[Task]:
        raise NotImplementedError("decompose_task not implemented yet.")

    def compose_task(self, task: Task, children_tasks: List[Task], **kwargs):
        raise NotImplementedError("compose_task not implemented yet.")

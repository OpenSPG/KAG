import inspect
from typing import List
from kag.interface import PipelineABC, PlannerABC, ExecutorABC
from kag.solver.task import TaskDAG
from kag.common.conf import KAG_CONFIG
from kag.common.registry import import_modules_from_path


@PipelineABC.register("iterative_plan_pipeline")
class IterativePlanPipeline:
    def __init__(
        self,
        planner: PlannerABC,
        executors: List[ExecutorABC],
    ):
        self.planner = planner
        self.executors = executors
        self.executor_map = {}
        for executor in self.executors:
            schema = executor.schema()
            for func_call in schema:
                func_name = func_call["name"]
                self.executor_map[func_name] = (
                    getattr(executor, func_name),
                    executor.is_terminate(func_name),
                )

    def run_task(self, task, context):
        func_name["name"]
        arguments = task["arguments"]
        arguments["context"] = context
        if func_name not in self.executor_map:
            raise ValueError(f"function {func_name} not found!")
        func, _ = self.executor_map[func_name]
        signature = inspect.signature(func)
        with_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD  # type: ignore
            for p in signature.parameters.values()
        )

        if not with_kwargs:
            accepted_args = dict(signature.parameters)
            filtered_args = {}
            for arg in arguments.keys():
                if arg in accepted_args:
                    filtered_args[arg] = arguments[arg]
            return func(**filtered_args)
        return func(**arguments)

    def check_terminate(self, task, task_dep, query, context):
        if task is None:
            return True
        func_name = task["name"]
        _, is_terminate = self.executor_map[func_name]
        return is_terminate

    def invoke(self, query, **kwargs):
        context = []

        while True:
            task, task_dep = self.planner.invoke(query, context, self.executors)
            # run task with dependencies
            result = self.run_task(task, task_dep, query, context)
            context.append(result)
            if self.check_terminate(task, task_dep, query, context):
                break
        return context[-1]


if __name__ == "__main__":
    import_modules_from_path("./src")
    pipeline_config = KAG_CONFIG.all_config["iterative_retrieval_pipeline"]
    pipeline = PipelineABC.from_config(pipeline_config)

    query = "张学友和刘德华共同出演过哪些电影"
    result = pipeline.invoke(context)

    return result

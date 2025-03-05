from kag.interface import PlannerABC, LLMClient
from kag.solver.task import TaskDAG


@PlannerABC.register("static_planner")
class MyStaticPlanner(PlannerABC):
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.output = {
            0: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "张学友出演过的电影列表"},
            },
            1: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "刘德华出演过的电影列表"},
            },
            2: {
                "executor": "call_py_code_generator",
                "dependent_task_ids": [0, 1],
                "arguments": {
                    "query": "请编写Python代码，找出以下两个列表的共同元素：\n张学友电影列表：{{0.output}}\n刘德华电影列表：{{1.output}}"
                },
            },
            3: {
                "executor": "call_deepseek",
                "dependent_task_ids": [2],
                "arguments": {"query": "请根据上下文信息，生成问题“张学友和刘德华共同出演过哪些电影”的详细答案"},
            },
        }

    def invoke(self, query, context, executors, **kwargs):
        model_output = self.output
        tasks = {}
        task_deps = {}
        for task_id, task_info in model_output.items():
            deps = task_info.pop("dependent_task_ids", [])
            tasks[task_id] = task_info
            task_deps[task_id] = deps
        return TaskDAG(tasks, task_deps)

    def is_dynamic(self):
        return False


@PlannerABC.register("iterative_planner")
class MyIterativePlanner(PlannerABC):
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.output = {
            0: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "张学友出演过的电影列表"},
            },
            1: {
                "executor": "call_kg_retriever",
                "dependent_task_ids": [],
                "arguments": {"query": "刘德华出演过的电影列表"},
            },
            2: {
                "executor": "call_py_code_generator",
                "dependent_task_ids": [0, 1],
                "arguments": {
                    "query": "请编写Python代码，找出以下两个列表的共同元素：\n张学友电影列表：{{0.output}}\n刘德华电影列表：{{1.output}}"
                },
            },
            3: {
                "executor": "call_deepseek",
                "dependent_task_ids": [2],
                "arguments": {"query": "请根据上下文信息，生成问题“张学友和刘德华共同出演过哪些电影”的详细答案"},
            },
        }
        self.idx = 0

    def invoke(self, query, context, executors, **kwargs):
        self.idx = self.idx % len(self.output)
        task = self.output[self.idx]
        tasks = {0: task}
        task_deps = {0: []}
        return TaskDAG(tasks, task_deps)

    def is_dynamic(self):
        return True

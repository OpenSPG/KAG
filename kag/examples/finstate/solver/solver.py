from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.implementation.default_memory import DefaultMemory
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool
from kag.solver.implementation.table.table_reasoner import TableReasoner


class FinStateSolver(SolverPipeline):
    """
    solver
    """

    def __init__(
        self, max_run=3, reflector=None, reasoner=None, generator=None, **kwargs
    ):
        super().__init__(max_run, reflector, reasoner, generator, **kwargs)
        self.table_reasoner = TableReasoner(**kwargs)

    def run(self, question):
        """
        Executes the core logic of the problem-solving system.

        Parameters:
        - question (str): The question to be answered.

        Returns:
        - tuple: answer, trace log
        """
        return self.table_reasoner.reason(question)


if __name__ == "__main__":
    solver = FinStateSolver()
    #question = "阿里巴巴最新的营业收入是多少，哪个部分收入占比最高，占了百分之多少？"
    question = "阿里巴巴的总收入是多少，哪个部分收入占比最高，占了百分之多少？"
    # question = "231243423乘以13334233等于多少？"
    response = solver.run(question)
    print("*" * 80)
    print(question)
    print("*" * 20)
    print(response)
    print("*" * 80)

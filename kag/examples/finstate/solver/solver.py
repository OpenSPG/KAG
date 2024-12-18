import logging


from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.solver.implementation.default_memory import DefaultMemory
from kag.solver.tools.info_processor import ReporterIntermediateProcessTool

logger = logging.getLogger(__name__)


class HistoryMemory(DefaultMemory):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def save_memory(self, solved_answer, supporting_fact, instruction):
        super().save_memory(solved_answer, supporting_fact, instruction)
        self.supporting_fact = supporting_fact

    def serialize_memory(self):
        if len(self.exact_answer) > 0:
            return f"[Solved Answer]{self.exact_answer[-1]}"
        serialize_memory = "[State Memory]:{}\n[Evidence Memory]:{}\n".format(
            str(self.state_memory), str(self.supporting_fact)
        )
        return serialize_memory


class FinStateSolver(SolverPipeline):
    """
    solver
    """

    def __init__(
        self, max_run=3, reflector=None, reasoner=None, generator=None, **kwargs
    ):
        from kag.common.env import init_env
        import os

        current_file_path = os.path.abspath(__file__)
        current_dir = os.path.dirname(current_file_path)
        work_dir = os.path.join(current_dir, "..")
        os.chdir(work_dir)
        init_env()
        super().__init__(max_run, reflector, reasoner, generator, **kwargs)
        self.memory = HistoryMemory(**kwargs)

    def run(self, question):
        """
        Executes the core logic of the problem-solving system.

        Parameters:
        - question (str): The question to be answered.

        Returns:
        - tuple: answer, trace log
        """
        instruction = question
        if_finished = False
        logger.debug("input instruction:{}".format(instruction))
        present_instruction = instruction
        run_cnt = 0

        while not if_finished and run_cnt < self.max_run:
            run_cnt += 1
            logger.debug("present_instruction is:{}".format(present_instruction))
            # Attempt to solve the current instruction and get the answer, supporting facts, and history log
            solved_answer, supporting_fact, history_log = self.reasoner.reason(
                present_instruction
            )

            # Extract evidence from supporting facts
            self.memory.save_memory(solved_answer, supporting_fact, instruction)

            history_log["present_instruction"] = present_instruction
            history_log["present_memory"] = self.memory.serialize_memory()
            self.trace_log.append(history_log)

            # Reflect the current instruction based on the current memory and instruction
            if_finished, present_instruction = self.reflector.reflect_query(
                self.memory, present_instruction
            )

        response = self.generator.generate(instruction, self.memory)
        return response, self.trace_log


if __name__ == "__main__":
    solver = FinStateSolver()
    response, trace_log = solver.run(
        "不考虑交通费用，三个人去北京出差，其中包括1位领导，1位资深专家和1位普通员工，领导当天回来，资深专家3天后回来，普通员工5天回来，大概需要多少钱？"
        #"按照2024年前三季度营业收入增长率，预测四季度营业收入是多少？"
    )
    print(response)

import copy
import logging
from kag.common.registry import Registrable

# from kag.solver.implementation.default_generator import DefaultGenerator
# from kag.solver.implementation.default_reasoner import DefaultReasoner
# from kag.solver.implementation.default_reflector import DefaultReflector
from kag.interface.solver.kag_generator_abc import KAGGeneratorABC
from kag.interface.solver.kag_memory_abc import KagMemoryABC
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC
from kag.interface.solver.base_model import LFExecuteResult

logger = logging.getLogger(__name__)


class SolverPipeline(Registrable):
    def __init__(
        self,
        reflector: KagReflectorABC,
        reasoner: KagReasonerABC,
        generator: KAGGeneratorABC,
        memory: KagMemoryABC,
        max_iterations=3,
        **kwargs
    ):
        """
        Initializes the think-and-act loop class.

        :param max_iterations: Maximum number of iteration to limit the thinking and acting loop, defaults to 3.
        :param reflector: Reflector instance for reflect tasks.
        :param reasoner: Reasoner instance for reasoning about tasks.
        :param generator: Generator instance for generating actions.
        :param memory: Assign memory store type
        """
        super().__init__(**kwargs)
        self.max_iterations = max_iterations

        self.reflector = reflector
        self.reasoner = reasoner
        self.generator = generator
        self.memory = memory
        self.param = kwargs

    def run(self, question, **kwargs):
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
        trace_log = []
        present_instruction = instruction
        run_cnt = 0
        memory = copy.copy(self.memory)

        while not if_finished and run_cnt < self.max_iterations:
            run_cnt += 1
            logger.debug("present_instruction is:{}".format(present_instruction))
            # Attempt to solve the current instruction and get the answer, supporting facts, and history log
            reason_res: LFExecuteResult = self.reasoner.reason(
                present_instruction, **kwargs
            )

            # Extract evidence from supporting facts
            memory.save_memory(
                reason_res.kg_exact_solved_answer,
                reason_res.get_support_facts(),
                instruction,
            )
            history_log = reason_res.get_trace_log()
            history_log["present_instruction"] = present_instruction
            history_log["present_memory"] = memory.serialize_memory()
            trace_log.append(history_log)

            # Reflect the current instruction based on the current memory and instruction
            if_finished, present_instruction = self.reflector.reflect_query(
                memory, present_instruction
            )

        response = self.generator.generate(instruction, memory)
        return response, trace_log

    def get_kg_answer_num(self):
        """
        Get the number of direct answers from the knowledge graph.
        Debug Info

        Returns:
            int: The number of direct answers from the knowledge graph.
        """
        return self.reasoner.kg_direct

    def get_total_sub_question_num(self):
        """
        Get the total number of sub-questions for solve question.
        Debug Info

        Returns:
            int: The total number of sub-questions.
        """
        return self.reasoner.sub_query_total

import logging

from kag.interface.solver.kag_generator_abc import KAGGeneratorABC
from kag.interface.solver.kag_reasoner_abc import KagReasonerABC
from kag.interface.solver.kag_reflector_abc import KagReflectorABC
from kag.solver.implementation.default_generator import DefaultGenerator
from kag.solver.implementation.default_memory import DefaultMemory
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.default_reflector import DefaultReflector

logger = logging.getLogger(__name__)


class SolverPipeline:
    def __init__(self, max_run=3, reflector: KagReflectorABC = None, reasoner: KagReasonerABC = None,
                 generator: KAGGeneratorABC = None, **kwargs):
        """
        Initializes the think-and-act loop class.

        :param max_run: Maximum number of runs to limit the thinking and acting loop, defaults to 3.
        :param reflector: Reflector instance for reflect tasks.
        :param reasoner: Reasoner instance for reasoning about tasks.
        :param generator: Generator instance for generating actions.
        """
        self.max_run = max_run
        self.memory = DefaultMemory(**kwargs)

        self.reflector = reflector or DefaultReflector(**kwargs)
        self.reasoner = reasoner or DefaultReasoner(**kwargs)
        self.generator = generator or DefaultGenerator(**kwargs)

        self.trace_log = []

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
        logger.debug('input instruction:{}'.format(instruction))
        present_instruction = instruction
        run_cnt = 0

        while not if_finished and run_cnt < self.max_run:
            run_cnt += 1
            logger.debug('present_instruction is:{}'.format(present_instruction))
            # Attempt to solve the current instruction and get the answer, supporting facts, and history log
            solved_answer, supporting_fact, history_log = self.reasoner.reason(present_instruction)

            # Extract evidence from supporting facts
            self.memory.save_memory(solved_answer, supporting_fact, instruction)

            history_log['present_instruction'] = present_instruction
            history_log['present_memory'] = self.memory.serialize_memory()
            self.trace_log.append(history_log)

            # Reflect the current instruction based on the current memory and instruction
            if_finished, present_instruction = self.reflector.reflect_query(self.memory, present_instruction)

        response = self.generator.generate(instruction, self.memory)
        return response, self.trace_log

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

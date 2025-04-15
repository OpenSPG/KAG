import logging
import re

from kag.interface import (
    SolverPipelineABC,
    PlannerABC,
    ExecutorABC,
    GeneratorABC,
)

logger = logging.getLogger()


@SolverPipelineABC.register("kag_prqa_pipeline")
class PrqaPipeline(SolverPipelineABC):
    def __init__(
            self,
            planner: PlannerABC,
            executor: ExecutorABC,
            generator: GeneratorABC,
    ):
        super().__init__()
        self.planner = planner
        self.executor = executor
        self.generator = generator
        self.max_retries = 3

    def invoke(self, query, **kwargs):
        try:
            return self.process_question(question=query)
        except Exception as e:
            logger.error(f"处理问题失败: {query} - {str(e)}")

    def process_question(self, question: str, retry_count: int = 0) -> str:
        """主处理流程"""
        try:
            q_type = self.planner.analyze_question(question)
            raw_result = self.executor.handlers[q_type](question)
            result = self.generator.invoke(question, context="", raw_data=raw_result)

            if self.is_invalid_response(result):
                if retry_count < self.max_retries:
                    logger.info(f"触发重试机制 [{retry_count + 1}/{self.max_retries}] 问题：{question}")
                    return self.process_question(question, retry_count + 1)
                return "未找到相关信息"
            return result

        except Exception as e:
            logger.error(f"处理异常: {str(e)}")
            if retry_count < self.max_retries:
                return self.process_question(question, retry_count + 1)
            return "系统繁忙，请稍后再试"

    @staticmethod
    def is_invalid_response(response: str) -> bool:
        """判断响应是否无效的规则"""
        invalid_patterns = [
            "未找到相关信息",
            ".*没有数据.*",
            ".*无法找到.*",
            ".*查询失败.*",
            ".*无法根据现有数据回答问题.*",
            "系统繁忙，请稍后再试",
            "^$"  # 空
        ]
        return any(
            re.search(pattern, response)
            for pattern in invalid_patterns
        )

    @staticmethod
    def write_response_to_txt(question_id, question, response, output_file):
        with open(output_file, 'a', encoding='utf-8') as output:
            output.write(f"序号: {question_id}\n")
            output.write(f"问题: {question}\n")
            output.write(f"答案: {response}\n")
            output.write("\n")

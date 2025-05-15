"""
cypher检测器
"""

import json
from difflib import SequenceMatcher

from neo4j.exceptions import Neo4jError

from kag.interface import PlannerABC, Task, LLMClient, PromptABC
from kag.common.conf import KAG_PROJECT_CONF
from kag.solver.utils import init_prompt_with_fallback


class CypherChecker:
    """
    检查返回的列是否符合预期
    检查where条件的value是否正确

    返回错误原因
    """

    def __init__(self, graph_schema, llm, neo4j_driver):
        self.graph_schema = graph_schema
        self.llm: LLMClient = llm
        self.neo4j_driver = neo4j_driver
        self.question_output = init_prompt_with_fallback(
            "question_output", KAG_PROJECT_CONF.biz_scene
        )

    def check(self, question, cypher):
        """
        检查
        """
        is_match, reason, should_output_list = self._check_output(
            query=question, cypher=cypher
        )
        if not is_match and reason:
            return (
                False,
                f"output proprety list not match to question: {reason}, should output {should_output_list}",
            )
        valid, reason = self._check_where(query=question, cypher=cypher)
        if not valid and reason:
            return False, reason
        return True, ""

    def _check_output(self, query, cypher):
        # 通过工具分析当前cypher返回的属性列表
        provided_output_list = self.get_cypher_output_properties(cypher=cypher)
        # 大模型判断返回列表与问题是否匹配
        output_list_llm = self.llm.invoke(
            variables={
                "question": query,
                "schema": self.graph_schema,
                "return_property_list": json.dumps(provided_output_list),
            },
            prompt_op=self.question_output,
            with_json_parse=False,
        )
        is_match = (
            "true" == str(output_list_llm["provided_output_list_correct"]).lower()
        )
        reason = str(output_list_llm["reason"])
        should_output_list = output_list_llm["should_output_list"]
        return is_match, reason, should_output_list

    async def _check_where(self, query, cypher):
        where_list = self.get_cypher_where_info(cypher)
        for entity, where_key, op, where_value in where_list:
            if op.lower() in ["=", "in"]:
                values = await self._get_where_values(entity, where_key)
                if where_value not in values:
                    # 找出最相似的N个
                    values = self.find_most_similar(where_value, values, 5)
                    return (
                        False,
                        f"filter: [{where_key}{op}{where_value}] error, values={values}",
                    )
            else:
                rst, reason = await self._check_sub_where(
                    entity, where_key, op, where_value
                )
                if rst is False:
                    return rst, reason
        return True, ""

    def find_most_similar(self, target, string_list, N):
        # 计算相似度
        similarity_scores = [
            (string, SequenceMatcher(None, target, string).ratio())
            for string in string_list
        ]
        # 按照相似度排序，取前N个
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in similarity_scores[:N]]

    async def _get_where_values(self, entity, where_key):
        query_cypher = f"MATCH (s:{entity})\nRETURN DISTINCT {where_key} AS values"
        values = []
        async with self.neo4j_driver.session(database="birdgraph") as session:
            try:
                # 执行查询并获取结果
                result = await session.run(query_cypher)
                records = [record async for record in result]
                for record in records:
                    values.append(record[0])
            except Neo4jError as e:
                raise e
        return values

    async def _check_sub_where(self, entity, where_key, op, where_value):
        sub_cypher_where = f"MATCH (s:{entity})\nWHERE {where_key}{op}{where_value}\nRETURN COUNT(*) AS count"
        sub_cypher = f"MATCH (s:{entity})\nRETURN COUNT(*) AS count"
        async with self.neo4j_driver.session(database="birdgraph") as session:
            try:
                # 执行查询并获取结果
                result = await session.run(sub_cypher_where)
                count = result.single()["count"]
                if 0 == count:
                    return False, f"filter: {where_key}{op}{where_value} result is null"
                result2 = await session.run(sub_cypher)
                count2 = result2.single()["count"]
                if count2 == count:
                    return (
                        False,
                        f"filter: {where_key}{op}{where_value} not filtering anything",
                    )
            except Neo4jError as e:
                raise e
            return True, ""

    def get_cypher_order_by(self, cypher):
        """
        获取cypher是否进行了orderby
        """
        pass

    def get_cypher_where_info(self, cypher) -> list[tuple[str, str, str, str]]:
        """
        获取cypher语句中的所有where约束条件
        返回(实体/关系, where_key, 比较符号, where_value)
        """
        return []

    def get_cypher_output_properties(self, cypher) -> list[str]:
        """
        获取cypher返回列
        返回列如果不能映射到属性上（cypher有可能返回复杂结构，返回组合列）需要给出提示。
        返回[实体/关系.property_name]
        """
        return []

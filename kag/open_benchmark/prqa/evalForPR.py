import concurrent.futures
import json
import logging
import os
import re
from typing import List, Dict

from kag.common.conf import KAG_CONFIG
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface import LLMClient
from kag.open_benchmark.prqa.solver.prompt.prompt_message import type_messages, path_messages, filter_messages, multi_hop_messages
from neo4j.graph import Path, Node, Relationship

logger = logging.getLogger()

cypher_tools = [{
    "type": "function",
    "function": {
        "name": "run_cypher_query",
        "description": "Get subgraph response for provided cypher query",
        "parameters": {
            "type": "object",
            "properties": {
                "cypher_query": {"type": "string"}
            },
            "required": ["cypher_query"],
            "additionalProperties": False
        },
        "strict": True
    }
}]

type_tools = [{
    "type": "function",
    "function": {
        "name": "get_handle_type",
        "description": "Get which class of problems does analysis belong",
        "parameters": {
            "type": "object",
            "properties": {
                "handle_type": {"type": "number"}
            },
            "required": ["handle_type"],
            "additionalProperties": False
        },
        "strict": True
    }
}]


def write_response_to_txt(question_id, question, response, output_file):
    with open(output_file, 'a', encoding='utf-8') as output:
        output.write(f"序号: {question_id}\n")
        output.write(f"问题: {question}\n")
        output.write(f"答案: {response}\n")
        output.write("\n")


def send_cypher_messages_deepseek(messages):
    client = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])
    response = client.client.chat.completions.create(
        model=client.model,
        messages=messages,
        tools=cypher_tools
    )
    return response.choices[0].message


def send_type_messages_deepseek(messages):
    client = LLMClient.from_config(KAG_CONFIG.all_config["chat_llm"])

    response = client.client.chat.completions.create(
        model=client.model,
        messages=messages,
        tools=type_tools
    )
    return response.choices[0].message


class EnhancedQuestionProcessor:
    def __init__(self, llm_client):
        self.logger = logging.getLogger()
        self.llm_client = llm_client

        self.handlers = {
            'type1': self.handle_type1_path,
            'type2': self.handle_type2_filter,
            'type3': self.handle_type3_list
        }
        self.max_retries = 3

    @staticmethod
    def analyze_question(question: str) -> str:
        """问题分类"""
        new_message = {
            "role": "user",
            "content": str(question)
        }
        type_messages.append(new_message)

        completion_1 = send_type_messages_deepseek(type_messages)

        tool = completion_1.tool_calls[0]
        args = json.loads(tool.function.arguments)
        handle_type = args.get("handle_type")
        del type_messages[-1]

        if int(handle_type) == 1:
            return 'type1'
        elif int(handle_type) == 2:
            return 'type2'
        elif int(handle_type) == 3:
            return 'type3'
        else:
            logger.error(f"对于问题: {question}\n 大模型处理type错误: {handle_type}\n", exc_info=True)
            return ""

    @staticmethod
    def generate_cypher(question: str, query_type: int = 1) -> str:
        """不带缓存的Cypher生成"""
        try:
            if query_type == 1:
                message_list = path_messages
            elif query_type == 2:
                message_list = filter_messages
            elif query_type == 3:
                message_list = multi_hop_messages
            else:
                raise ValueError(f"未知的查询类型: {query_type}")

            new_message = {
                "role": "user",
                "content": str(question)
            }
            message_list.append(new_message)

            completion_1 = send_cypher_messages_deepseek(message_list)

            tool = completion_1.tool_calls[0]
            args = json.loads(tool.function.arguments)
            cypher_query = args.get("cypher_query")

            del message_list[-1]

            return cypher_query

        except Exception as e:
            logger.error(f"生成 Cypher 查询失败: {str(e)}", exc_info=True)
            return ""

    def process_question(self, question: str, retry_count: int = 0) -> str:
        """主处理流程"""
        try:
            q_type = self.analyze_question(question)
            raw_result = self.handlers[q_type](question)
            result = self.post_process(raw_result, question)

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
            "^$"  # 空
        ]
        return any(
            re.search(pattern, response)
            for pattern in invalid_patterns
        )

    # ---------- 第一类处理：路径查询 ----------
    def handle_type1_path(self, question: str) -> List:
        """处理明确路径查询"""
        try:
            cypher = self.generate_cypher(question, query_type=1)
            raw_result = self.execute_cypher(cypher)

            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"路径查询失败: {str(e)}")
            return []

    # ---------- 第二类处理：过滤型查询 ----------
    def handle_type2_filter(self, question: str) -> List:
        """处理带排除条件的查询"""
        try:
            cypher = self.generate_cypher(question, query_type=2)
            raw_result = self.execute_cypher(cypher)
            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"过滤查询失败: {str(e)}")
            return []

    # ---------- 第三类处理：多结果列表查询 ----------
    def handle_type3_list(self, question: str) -> List:
        """处理需要遍历多个结果的查询"""
        try:
            cypher = self.generate_cypher(question, query_type=3)
            raw_result = self.execute_cypher(cypher)
            return self.process_path_result(raw_result)
        except Exception as e:
            logger.error(f"列表查询失败: {str(e)}")
            return []

    def execute_cypher(self, cypher: str) -> List:
        """增强的查询执行"""
        try:
            raw = neo4j_client.run_cypher_query("prqa", cypher)
            if not isinstance(raw, list):
                logger.error(f"无效的查询结果类型: {type(raw)}")
                return []
            return self.standardize_result(raw)
        except Exception as e:
            logger.error(f"查询执行失败: {cypher} - {str(e)}")
            return []

    @staticmethod
    def standardize_result(data: List) -> List:
        """增强标准化方法"""
        processed = []
        for record in data:
            try:
                clean_record = {}
                for key, value in record.items():
                    if isinstance(value, Path):
                        path_data = {
                            "nodes": [
                                {
                                    "element_id": node.element_id if hasattr(node, 'element_id') else None,
                                    "labels": list(node.labels),
                                    "properties": {k: v for k, v in node.items() if k != '_name_vector'}
                                } for node in value.nodes
                            ],
                            "relationships": [
                                {
                                    "element_id": rel.element_id if hasattr(rel, 'element_id') else None,
                                    "type": rel.type,
                                    "start_node": rel.start_node.element_id,
                                    "end_node": rel.end_node.element_id,
                                    "properties": {k: v for k, v in rel.items() if k != '_name_vector'}
                                } for rel in value.relationships
                            ]
                        }
                        clean_record[key] = path_data
                    elif isinstance(value, (Node, Relationship)):
                        element_type = {
                            Node: {
                                "element_id": value.element_id,
                                "labels": list(value.labels),
                                "properties": {k: v for k, v in value.items() if k != '_name_vector'}
                            },
                            Relationship: {
                                "element_id": value.element_id,
                                "type": value.type,
                                "start_node": value.start_node.element_id,
                                "end_node": value.end_node.element_id,
                                "properties": {k: v for k, v in value.items() if k != '_name_vector'}
                            }
                        }[type(value)]
                        clean_record[key] = element_type
                    else:
                        clean_record[key] = value
                processed.append(clean_record)
            except Exception as e:
                logger.error(f"记录处理异常: {str(e)}")
        return processed

    def process_path_result(self, path_data: List[Dict]) -> List[str]:
        """安全处理包含多层结构的路径数据"""
        all_sentences = []
        try:
            for path in path_data:
                sentences = []
                # 提取核心路径数据（处理p字段嵌套）
                path_container = path.get("p", {})
                raw_nodes = path_container.get("nodes", [])
                raw_rels = path_container.get("relationships", [])

                node_map = {}
                for node in raw_nodes:
                    if not isinstance(node, dict):
                        continue

                    node_id = node.get("element_id")
                    if not node_id:
                        continue

                    props = node.get("properties", {})
                    node_name = props.get("name") or props.get("title") or f"未知节点_{node_id[-4:]}"
                    node_map[node_id] = node_name

                seen_relationships = set()
                for rel in raw_rels:
                    if not isinstance(rel, dict):
                        continue

                    rel_id = rel.get("element_id", "").split(":")[-1]
                    rel_type = rel.get("type", "未知关系")
                    start_id = rel.get("start_node")
                    end_id = rel.get("end_node")

                    start_name = node_map.get(start_id, f"未知起点_{start_id[-4:]}" if start_id else "完全未知起点")
                    end_name = node_map.get(end_id, f"未知终点_{end_id[-4:]}" if end_id else "完全未知终点")
                    rel_signature = f"{start_id}-{rel_type}->{end_id}"

                    if rel_signature not in seen_relationships:
                        sentences.append(f"{start_name} --[{rel_type}]--> {end_name}")
                        seen_relationships.add(rel_signature)

                connected_nodes = set()
                for rel in raw_rels:
                    connected_nodes.update([rel.get("start_node"), rel.get("end_node")])

                for node in raw_nodes:
                    node_id = node.get("element_id")
                    if node_id and node_id not in connected_nodes:
                        node_name = node_map.get(node_id, f"未命名节点_{node_id[-4:]}")
                        sentences.append(f"{node_name} ⚠️(未连接到主路径)")

                all_sentences.extend(sentences)

        except Exception as e:
            self.logger.error(f"路径解析异常: {str(e)}", exc_info=True)
            return ["路径解析失败，请检查数据格式"]

        return all_sentences

    def post_process(self, raw_data: List, question: str) -> str:
        """后处理生成自然语言回答"""
        if not raw_data:
            return "未找到相关信息"

        prompt = self.build_analysis_prompt(raw_data, question)
        return self.llm_client(prompt)

    def build_analysis_prompt(self, data: List, question: str) -> str:
        """构建分析提示词"""
        prompt_lines = [
            "从以下路径关系中分析问题：",
            *self.format_analysis_data(data),
            f"\n分析问题：“{question}”的答案",
            "请按照以下步骤完成：",
            "1. **提取逻辑链条**：逐步分析路径数据中与问题相关的关键信息",
            "2. **确定问题目标**：明确问题需要获取的核心信息",
            "3. **组织答案**：用简洁自然的中文回答，包含必要细节(如果有多个答案，请全部回答出来)",
            "只用最精简的结果给出答案，不要分析步骤的内容，多个答案时用顿号'、'隔开，除此之外不要有冗余字符"
        ]
        return '\n'.join(prompt_lines)

    @staticmethod
    def format_analysis_data(data: List) -> List[str]:
        """格式化分析数据"""
        formatted = []
        for item in data:
            if isinstance(item, str):
                formatted.append(item)
            elif isinstance(item, dict):
                formatted.append(json.dumps(item, ensure_ascii=False))
        return formatted

    def process_all_items_parallel(self, test_data, output_file, max_workers=5):
        """
        并行处理问题列表

        参数:
            test_data: 问题列表，格式为 [{ "question": "问题1" }, { "question": "问题2" }, ...]
            processor: 提供 process_question 方法的对象
            output_file: 输出结果文件路径
            max_workers: 最大并行线程数
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.handle_item, item, output_file)
                for item in test_data
            ]

            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"任务执行过程中出现异常: {str(e)}")

    def handle_item(self, item, output_file):
        """ 并行处理单个问题的完整逻辑 """
        question = item.get("question")
        question_id = item.get("id")
        try:
            response = self.process_question(question)
            write_response_to_txt(
                question_id=question_id,
                question=question,
                response=response,
                output_file=output_file
            )

        except Exception as e:
            logger.error(f"处理问题失败: {question} - {str(e)}")
            write_response_to_txt(
                question_id=question_id,
                question=question,
                response=f"处理失败: {str(e)}",
                output_file=output_file
            )

    def process_all_items_single(self, test_data, output_file):
        for item in test_data:
            question = item.get("question")
            question_id = item.get("id")
            try:
                response = self.process_question(question)
                write_response_to_txt(
                    question_id=question_id,
                    question=question,
                    response=response,
                    output_file=output_file
                )
            except Exception as e:
                logger.error(f"处理问题失败: {question} - {str(e)}")
                write_response_to_txt(
                    question_id=question_id,
                    question=question,
                    response=f"处理失败: {str(e)}",
                    output_file=output_file
                )


if __name__ == "__main__":
    neo4j_client = Neo4jClient(
        uri="neo4j://localhost:7687",
        user="",
        password="",
        database="prqa"
    )

    llm_client = LLMClient.from_config(KAG_CONFIG.all_config["openie_llm"])
    processor = EnhancedQuestionProcessor(llm_client)

    with open("./solver/data/test.json", 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    processor.process_all_items_single(test_data, output_file='./solver/data/result.txt')
    # processor.process_all_items_parallel(test_data,
    #                                      output_file='./solver/data/result.txt',
    #                                      max_workers=5)




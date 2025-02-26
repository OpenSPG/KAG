import json
import logging
from openai import OpenAI
import requests
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface import LLMClient

logger = logging.getLogger()


tools = [{
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

messages = [
    {
        "role": "system",
        "content": """{
                   "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句",
                    "example":[{
                        "query":"《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '利箭纵横' AND endNode.name =~ '陈道明' RETURN p"
                    },{
                        "query":"《春兰花开》作者的姐姐中，谁是刘梦溪的妻子？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '春兰花开' AND endNode.name =~ '刘梦溪' RETURN p"
                    }]}"""
    }
]


def send_messages_qwen(messages):
    # client1 = OpenAI(
    #     api_key="",
    #     base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    # )
    # model_name = "qwen-max-latest"

    client1 = OpenAI(
        api_key="",
        base_url="https://api.deepseek.com",
    )
    model_name = "deepseek-chat"

    response = client1.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools
    )
    return response.choices[0].message


def send_messages_deepseek(messages):
    client2 = OpenAI(
        api_key="",
        base_url="https://api.deepseek.com",
    )
    model_name = "deepseek-chat"

    response = client2.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=tools
    )
    return response.choices[0].message


def process_json_to_sentence_list(json_data):
    # 存储结果的字符串列表
    result_list = []
    # 遍历 JSON 数据
    for item in json_data:
        if "p" in item:
            path = item["p"]  # 提取路径列表
            # 初始化句子列表，用于拼接完整路径
            sentence_parts = []
            # 遍历路径，按照 节点-关系-节点 生成单句
            for i in range(0, len(path) - 2, 2):  # 每次取 节点-关系-节点
                current_node = path[i]
                relationship = path[i + 1]
                next_node = path[i + 2]

                # 生成句子部分（节点-关系-节点）
                part = f'{current_node["name"]}与{next_node["name"]}的关系是{relationship}'
                sentence_parts.append(part)

            # 将路径的所有句子部分用逗号拼接
            result_list.append("，".join(sentence_parts))

    return list(set(result_list))


def process_results(data, key_to_remove):
    if isinstance(data, dict):
        # 如果是字典，检查是否包含目标键
        if key_to_remove in data:
            del data[key_to_remove]  # 删除目标键
        # 递归检查字典中的每个值
        for key, value in data.items():
            process_results(value, key_to_remove)
    elif isinstance(data, list):
        # 如果是列表，递归检查列表中的每个元素
        for item in data:
            process_results(item, key_to_remove)


def write_response_to_txt(question, response, output_file):
    # 打开输出文件写入结果
    with open(output_file, 'a', encoding='utf-8') as output:
        # 写入到输出文件
        output.write(f"问题: {question}\n")
        output.write(f"答案: {response}\n")
        output.write("\n")


if __name__ == "__main__":
    neo4j_client = Neo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="",
        database="prqa"
    )
    llm_config = {
        "api_key": '',
        "base_url": 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-max-latest',
        'type': 'maas'
    }
    llm_client = LLMClient.from_config(llm_config)

    with open("./data/testForCypher.json", 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    for item in test_data:
        # 获取 question 和 cypher_query
        question = item.get("question")
        # cypher_query = item.get("cypher")

        new_message = {
            "role": "user",
            "content": str(question)
        }
        messages.append(new_message)
        completion_1 = send_messages_deepseek(messages)
        # print(f"User>\t {messages[0]['content']}")
        tool = completion_1.tool_calls[0]
        args = json.loads(tool.function.arguments)
        cypher_query = args.get("cypher_query")
        cypher_result = neo4j_client.run_cypher_query(database="prqa", query=cypher_query)

        # 递归地从 JSON 对象中删除指定字段 并 删除 "_name_vector" 字段
        records = []
        for record in cypher_result:
            records.append(record.data())  # 将每条记录转为字典
        # 转换为 JSON
        json_result = json.dumps(records, ensure_ascii=False, indent=2)
        data = json.loads(json_result)

        process_results(data, "_name_vector")
        cypher_result_list = process_json_to_sentence_list(data)
        # messages.append(question)
        # messages.append(completion_1)
        # messages.append({"role": "tool", "tool_call_id": tool.id, "content": str(cypher_result)})

        prompt = "从以下路径关系中分析问题：\n"
        prompt += '\n'.join(cypher_result_list)
        prompt += (f"\n分析问题：“{question}”的答案\n"
                   "请按照以下步骤完成：\n"
                   " 1. **提取逻辑链条**：逐步分析路径数据中与问题相关的关键信息。\n"
                   " 2. **确定问题目标**：问题需要的是什么。\n"
                   " 3. **输出答案**\n"
                   )
        # messages.append(prompt)

        # completion_2 = send_messages_qwen(messages)
        # print(f"Model>\t {completion_2.content}")
        del messages[-1]

        print(prompt)
        response = llm_client(prompt)
        print(response)
        write_response_to_txt(question, response, output_file='./cypher_result27.txt')





import json
import logging
import re
from typing import List, Dict

from neo4j.graph import Path, Node, Relationship
from openai import OpenAI

from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.interface import LLMClient

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


type_messages = [
    {
        "role": "system",
        "content": """{
                "instruct": "你是一个图数据专家，已知有三类问题，第一类问题是路径类问题，只需要起始节点和终点节点两点确定路径后，判断路径中的节点即可找到答案;
                    第二类问题是过滤类问题，需要起始节点和终点节点两点确定路径后，找到相应的答案，然后去除掉某个选项，典型关键词：除了、除外、不包括、排除；
                    第三类问题是多跳类问题，只需要起始节点，然后加上相应的关系，找到最终的答案，典型：存在使用连续'的'连接关系。
                    按以下步骤操作，步骤1：检测问题是否包含排除词汇（例如“除了”“不包括”）→ 如果是，归类为 过滤类问题（编号2）；
                    步骤2：检测问题是否同时指定起始和终点节点，且无排除条件(典型:存在“且”、存在“谁”、“是谁”) → 如果是，归类为 路径类问题（编号1）。
                    步骤3：检测问题是否仅有起始节点，并包含多级关系描述（例如“的...的...”） → 如果是，归类为 多跳类问题（编号3）。
                    请你确定给出的问题属于三类问题的哪一类问题，根据输入问题严格遵循规则，直接返回最终分类编号（仅限'1'、'2'、'3'）"
                }
                "example": [{
                        "query": "《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？",
                        "response": "1"
                    },{
                        "query": "《春兰花开》作者的姐姐中，谁是刘梦溪的妻子？",
                        "response": "1"
                    },{
                        "query": "谁是黄迪扬代表作品中的主要演员, 且有合作伙伴黄秋生？",
                        "response": "1"
                    },{
                        "query": "担任了金太郎的代表作品的主演的同时又是《少年们》的主要演员的人是谁？",
                        "response": "1"
                    },{
                        "query": "谁既是吴莉婕搭档的搭档，还是李乐祺的父亲？",
                        "response": "1"
                    },{
                        "query": "《山海惊奇》的作者有什么代表作品, 且出版社是中国致公出版社？"
                        "response": "1"
                    },{
                        "query": "是宜宁翁主的侄子的孙子的同时又是李芳远的曾孙的人是谁？"
                        "response": "1"
                    },{
                        "query": "谁是郑伟铭的毕业院校的知名校友，还是钟少珍的学生？",
                        "response": "1"
                    },{
                        "query": "高珊的代表作品的一位主要配音演员的的搭档除了许文广, 请问他的搭档还有谁？",
                        "response": "2"
                    },{
                        "query": "刘梦娜的毕业院校，它的哪位知名校友的搭档是安?",
                        "response": "1"
                    },{
                        "query": "《Godzilla》的歌曲原唱的某一个好友的音乐作品除了《Still Love》, 请问它的音乐作品还有哪些？",
                        "response": "2"
                    },{
                        "query": "请问《零号嫌疑犯》的主要演员参演的另一部作品中，哈利·基纳是该作品的主要角色之一，请问另外的主要角色是哪些人？"
                        "response": "2"
                    },{
                        "query": "《酬韦相公见寄》的作者的某一个好友的好友张蠙除外, 请问他的好友还有谁?",
                        "response": "2"
                    },{
                        "query": "赵超的毕业院校，它的知名人物的儿子有哪些?",
                        "response": "3"
                    },{
                        "query": "在爱里等你的歌曲原唱中，它老师合作过的搭档有哪些？",
                        "response": "3"
                    },{
                        "query": "如梦令这首歌的歌曲，它的原唱的前男友有哪些代表作品？",
                        "response": "3"
                    }]}"""
    }
]

path_messages = [
    {
        "role": "system",
        "content": """{
                   "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句,如果需要关系类型",
                    "example":[{
                        "query":"《利箭纵横》的主要演员的哪位搭档与陈道明搭档过？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '利箭纵横' AND endNode.name =~ '陈道明' RETURN p"
                    },{
                        "query":"《春兰花开》作者的姐姐中，谁是刘梦溪的妻子？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '春兰花开' AND endNode.name =~ '刘梦溪' RETURN p"
                    },{
                        "query":"《山海惊奇》的作者有什么代表作品, 且出版社是中国致公出版社？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '山海惊奇' AND endNode.name =~ '中国致公出版社' RETURN p"
                    }，{
                        "query":"谁是郑伟铭的毕业院校的知名校友，还是钟少珍的学生？",
                        "response":"MATCH p=(startNode)-[*1..3]-(endNode) WHERE startNode.name =~ '郑伟铭' AND endNode.name =~ '钟少珍' RETURN p"
                    }]}"""
    }
]

multi_hop_messages = [
    {
        "role": "system",
        "content": """{ 
            "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句, 需要的关系类型从如下关系中挑选： "PersonWithPerson": ["学姐", "未婚夫", "外祖父", "妾", 
            "姨夫", "堂伯父", "第三任妻子", "堂弟", "堂妹", "前男友", "外孙", "连襟", "义母", "叔父", "徒弟","妻姐", "堂哥", "前妻", "养女", "孙女", "外孙子", "曾外祖母", "第二任丈夫", "丈夫", 
            "师弟", "大姨子", "岳母", "侄子", "妻子","小姑子", "好友", "表哥", "曾外孙子", "义父", "学妹", "亲家公", "第四任妻子", "生母", "老师", "队友", "姑姑", "姑父", "义妹", "同门", 
            "兄弟", "合作人", "表兄", "第一任妻子", "继母", "堂兄", "外甥", "女婿", "表侄", "师傅", "师姐", "堂小舅子", "庶子", "老板", "前公公", "侄孙子", "侄孙媳妇", "弟子", "前儿媳", 
            "叔外公", "师兄", "堂姐", "助理", "伯母", "曾孙子", "义兄", "外曾孙女", "生父", "大姑子", "亲家母", "外曾孙子", "堂侄", "恩师", "舅母", "教练", "叔外祖父", "伯伯", "姨父", "婆婆", 
            "妯娌", "导师", "亡妻", "同学", "义子", "弟弟", "表弟", "学弟", "前任", "外甥女", "继子", "知己", "经纪人", "妹夫", "小舅子", "祖母", "师妹", "姑妈", "前队友", "表叔", 
            "表姑父", "大爷爷", "玄孙", "儿子", "姐夫", "堂舅", "第五任妻子", "大舅子", "前夫", "恋人", "对手", "偶像", "原配", "嫂子", "大伯哥", "儿媳", "孙子", "男朋友", "爱人", "伯乐", 
            "搭档", "师父", "学生", "旧爱", "外曾祖母", "女朋友", "先夫", "养父", "义弟", "继父", "师祖", "外祖母", "表姐", "姑母", "外曾祖父", "妹妹", "岳父", "姨母", "曾外祖父", "云孙", 
            "女儿", "朋友", "继女", "伴侣", "嫡母", "未婚妻", "母亲", "养母", "舅父", "曾孙", "曾祖母", "侄孙", "学长", "父亲", "第二任妻子", "外甥女婿", "公公", "师爷", "挚爱", "大舅哥", 
            "奶奶", "外孙女", "第一任丈夫", "表姨", "侄女", "伯父", "小叔子", "义女", "婶母", "曾孙女", "叔叔", "第六任妻子", "小姨子", "战友", "表妹", "养子", "曾祖父", "男友", "继任", 
            "姐姐", "祖父", "前女友", "哥哥", "弟媳", "社长", "师生", "员工", "旗下艺人"], "PersonWithWork": ["编剧", "综艺节目", "作者", "主要作品", "摄影作品", "歌曲原唱", "主要配音", 
            "代表作品", "音乐作品", "制作", "主要演员", "配音", "文学作品", "登场作品", "主持", "主要角色", "音乐视频", "参演", "为他人创作音乐", "执导", "发行专辑"], 
            "OrganizationWithOrganization": ["代表", "创办", "设立单位", "办学团体", "专职院士数", "相关国内联盟", "院系设置", "所属机构", "合作院校", "设立单位"], 
            "PersonWithOrganization": ["领导", "现任领导", "历任领导", "成员", "毕业院校", "创始人", "法人", "知名人物", "现任领导"], "WorkWithOrganization": ["出版社", 
            "连载平台"], "Others": ["类别", "经纪公司", "其他关系", "简称", "学校类别", "学校身份", "类型", "学校特色", "办学性质"]", 
            "example":[{ 
                "query":"赵超的毕业院校，它的知名人物的儿子有哪些?", 
                "response":"MATCH p=(startNode)-[:毕业院校]->()-[:知名人物]->()-[:儿子]->() WHERE startNode.name = '赵超' RETURN p" 
            },{ 
                "query":"在爱里等你的歌曲原唱中，它老师合作过的搭档有哪些？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:老师]->()-[:搭档]->() WHERE startNode.name = '在爱里等你' RETURN p" 
            },{ 
                "query":"如梦令这首歌的歌曲，它的原唱的前男友有哪些代表作品？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:前男友]->()-[:代表作品]->() WHERE startNode.name = '如梦令' RETURN p" 
            }]}"""
    }
]

filter_messages = [
    {
        "role": "system",
        "content": """{ 
            "instruct": "你是一个图数据专家，请参考example将用户请求转成cypher语句, 需要的关系类型从如下关系中挑选： "PersonWithPerson": ["学姐", "未婚夫", "外祖父", "妾", 
            "姨夫", "堂伯父", "第三任妻子", "堂弟", "堂妹", "前男友", "外孙", "连襟", "义母", "叔父", "徒弟","妻姐", "堂哥", "前妻", "养女", "孙女", "外孙子", "曾外祖母", "第二任丈夫", "丈夫", 
            "师弟", "大姨子", "岳母", "侄子", "妻子","小姑子", "好友", "表哥", "曾外孙子", "义父", "学妹", "亲家公", "第四任妻子", "生母", "老师", "队友", "姑姑", "姑父", "义妹", "同门", 
            "兄弟", "合作人", "表兄", "第一任妻子", "继母", "堂兄", "外甥", "女婿", "表侄", "师傅", "师姐", "堂小舅子", "庶子", "老板", "前公公", "侄孙子", "侄孙媳妇", "弟子", "前儿媳", 
            "叔外公", "师兄", "堂姐", "助理", "伯母", "曾孙子", "义兄", "外曾孙女", "生父", "大姑子", "亲家母", "外曾孙子", "堂侄", "恩师", "舅母", "教练", "叔外祖父", "伯伯", "姨父", "婆婆", 
            "妯娌", "导师", "亡妻", "同学", "义子", "弟弟", "表弟", "学弟", "前任", "外甥女", "继子", "知己", "经纪人", "妹夫", "小舅子", "祖母", "师妹", "姑妈", "前队友", "表叔", 
            "表姑父", "大爷爷", "玄孙", "儿子", "姐夫", "堂舅", "第五任妻子", "大舅子", "前夫", "恋人", "对手", "偶像", "原配", "嫂子", "大伯哥", "儿媳", "孙子", "男朋友", "爱人", "伯乐", 
            "搭档", "师父", "学生", "旧爱", "外曾祖母", "女朋友", "先夫", "养父", "义弟", "继父", "师祖", "外祖母", "表姐", "姑母", "外曾祖父", "妹妹", "岳父", "姨母", "曾外祖父", "云孙", 
            "女儿", "朋友", "继女", "伴侣", "嫡母", "未婚妻", "母亲", "养母", "舅父", "曾孙", "曾祖母", "侄孙", "学长", "父亲", "第二任妻子", "外甥女婿", "公公", "师爷", "挚爱", "大舅哥", 
            "奶奶", "外孙女", "第一任丈夫", "表姨", "侄女", "伯父", "小叔子", "义女", "婶母", "曾孙女", "叔叔", "第六任妻子", "小姨子", "战友", "表妹", "养子", "曾祖父", "男友", "继任", 
            "姐姐", "祖父", "前女友", "哥哥", "弟媳", "社长", "师生", "员工", "旗下艺人"], "PersonWithWork": ["编剧", "综艺节目", "作者", "主要作品", "摄影作品", "歌曲原唱", "主要配音", 
            "代表作品", "音乐作品", "制作", "主要演员", "配音", "文学作品", "登场作品", "主持", "主要角色", "音乐视频", "参演", "为他人创作音乐", "执导", "发行专辑"], 
            "OrganizationWithOrganization": ["代表", "创办", "设立单位", "办学团体", "专职院士数", "相关国内联盟", "院系设置", "所属机构", "合作院校", "设立单位"], 
            "PersonWithOrganization": ["领导", "现任领导", "历任领导", "成员", "毕业院校", "创始人", "法人", "知名人物", "现任领导"], "WorkWithOrganization": ["出版社", 
            "连载平台"], "Others": ["类别", "经纪公司", "其他关系", "简称", "学校类别", "学校身份", "类型", "学校特色", "办学性质"]", 
            "example":[{ 
                "query":"高珊的代表作品的一位主要配音演员的的搭档除了许文广, 请问他的搭档还有谁？", 
                "response":"MATCH p=(startNode)-[:代表作品]->()-[:主要配音]->(actor)-[:搭档]->() WHERE startNode.name = '高珊' AND '许文广' IN [(actor)-[:搭档]->(endNode) | endNode.name] RETURN p" 
            },{ 
                "query":"《Godzilla》的歌曲原唱的某一个好友的音乐作品除了《Still Love》, 请问它的音乐作品还有哪些？", 
                "response":"MATCH p=(startNode)-[:歌曲原唱]->()-[:好友]->(actor)-[:音乐作品]->() WHERE startNode.name = 'Godzilla' AND 'Still Love' IN [(actor)-[:音乐作品]->(endNode) | endNode.name] RETURN p" 
            },{ 
                "query":"《酬韦相公见寄》的作者的某一个好友的好友张蠙除外, 请问他的好友还有谁?", 
                "response":"MATCH p=(startNode)-[:作者]->()-[:好友]->(actor)-[:好友]->() WHERE startNode.name = '酬韦相公见寄' AND '张蠙' IN [(actor)-[:好友]->(endNode) | endNode.name] RETURN p" 
            }]}"""
    }
]


def write_response_to_txt(question, response, output_file):
    # 打开输出文件写入结果
    with open(output_file, 'a', encoding='utf-8') as output:
        # 写入到输出文件
        output.write(f"问题: {question}\n")
        output.write(f"答案: {response}\n")
        output.write("\n")


def send_messages_qwen(messages):
    client1 = OpenAI(
        api_key="",
        base_url="",
    )
    model_name = "deepseek-chat"
    # model_name = "qwen-max-latest"
    response = client1.chat.completions.create(
        model=model_name,
        messages=messages,
        tools=cypher_tools
    )
    return response.choices[0].message


def send_messages_deepseek(messages):
    client2 = OpenAI(
        api_key="",
        base_url="",
    )
    model_name = "deepseek-chat"

    response = client2.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=cypher_tools
        )
    return response.choices[0].message


def send_type_messages_deepseek(messages):
    client2 = OpenAI(
        api_key="",
        base_url="",
    )
    model_name = "deepseek-chat"

    response = client2.chat.completions.create(
        model=model_name,
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
        # 添加新消息到消息列表
        new_message = {
            "role": "user",
            "content": str(question)
        }
        type_messages.append(new_message)
        # 调用生成函数
        completion_1 = send_type_messages_deepseek(type_messages)
        # 提取工具调用结果
        tool = completion_1.tool_calls[0]
        args = json.loads(tool.function.arguments)
        handle_type = args.get("handle_type")
        # 从消息列表中移除最后一条消息（回滚）
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
            # 根据类型选择消息列表
            if query_type == 1:
                message_list = path_messages
            elif query_type == 2:
                message_list = filter_messages
            elif query_type == 3:
                message_list = multi_hop_messages
            else:
                raise ValueError(f"未知的查询类型: {query_type}")

            # 添加新消息到消息列表
            new_message = {
                "role": "user",
                "content": str(question)
            }
            message_list.append(new_message)

            # 调用生成函数
            completion_1 = send_messages_deepseek(message_list)

            # 提取工具调用结果
            tool = completion_1.tool_calls[0]
            args = json.loads(tool.function.arguments)
            cypher_query = args.get("cypher_query")
            # 从消息列表中移除最后一条消息（回滚）
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
            # 验证响应有效性
            if self.is_invalid_response(result):
                if retry_count < self.max_retries:
                    logger.info(f"触发重试机制 [{retry_count+1}/{self.max_retries}] 问题：{question}")
                    return self.process_question(question, retry_count+1)
                return "未找到相关信息"  # 达到最大重试次数
            return result

        except Exception as e:
            logger.error(f"处理异常: {str(e)}")
            if retry_count < self.max_retries:
                return self.process_question(question, retry_count+1)
            return "系统繁忙，请稍后再试"  # 最终错误提示

    @staticmethod
    def is_invalid_response(response: str) -> bool:
        """判断响应是否无效的规则"""
        invalid_patterns = [
            "未找到相关信息",
            ".*没有数据.*",
            ".*无法找到.*",
            ".*查询失败.*",
            "^$"  # 空
        ]
        # 匹配任意无效模式即为无效
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
            logger.error(f"列表查询失败: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"过滤查询失败: {str(e)}")
            return []

    # ---------- 第三类处理：多结果列表查询 ----------
    def handle_type3_list(self, question: str) -> List:
        """处理需要遍历多个结果的查询"""
        try:
            # 执行主查询
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
            # 添加结果类型校验
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
                        # 安全处理路径对象
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
                        # 处理单个节点/关系
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

                # 构建节点名称映射表（带类型检查）
                node_map = {}
                for node in raw_nodes:
                    # 确保节点数据格式正确
                    if not isinstance(node, dict):
                        continue

                    node_id = node.get("element_id")
                    if not node_id:
                        continue

                    # 获取节点名称，兼容不同属性名的情况
                    props = node.get("properties", {})
                    node_name = props.get("name") or props.get("title") or f"未知节点_{node_id[-4:]}"
                    node_map[node_id] = node_name

                # 处理关系数据（带顺序保持）
                seen_relationships = set()  # 防止重复关系
                for rel in raw_rels:
                    if not isinstance(rel, dict):
                        continue

                    # 提取关系关键信息
                    rel_id = rel.get("element_id", "").split(":")[-1]
                    rel_type = rel.get("type", "未知关系")
                    start_id = rel.get("start_node")
                    end_id = rel.get("end_node")

                    # 生成关系描述（带唯一性校验）
                    start_name = node_map.get(start_id, f"未知起点_{start_id[-4:]}" if start_id else "完全未知起点")
                    end_name = node_map.get(end_id, f"未知终点_{end_id[-4:]}" if end_id else "完全未知终点")
                    rel_signature = f"{start_id}-{rel_type}->{end_id}"

                    if rel_signature not in seen_relationships:
                        sentences.append(f"{start_name} --[{rel_type}]--> {end_name}")
                        seen_relationships.add(rel_signature)

                # 检测孤立节点（带路径上下文提示）
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

        # 结构化数据转自然语言
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
            "3. **组织答案**：用简洁自然的中文回答，包含必要细节"
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


# # 主函数，使用线程池处理问题
# def process_questions_multithreaded(test_data, processor, output_file='./cypher_result_0304.txt', max_workers=5):
#     llm_client = LLMClient.from_config(llm_config)
#     processor = EnhancedQuestionProcessor(llm_client)
#
#     """
#     多线程处理问题
#
#     参数:
#         test_data (list): 包含问题的列表
#         processor: 提供 process_question 方法的对象
#         output_file (str): 输出结果文件路径
#         max_workers (int): 最大线程数量
#     """
#     with ThreadPoolExecutor(max_workers=max_workers) as executor:
#         # 提交任务到线程池
#         futures = [
#             executor.submit(process_question, item, processor, output_file)
#             for item in test_data
#         ]
#         # 确保所有任务完成
#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 # 如果需要，可以获取返回结果（当前不需要）
#                 future.result()
#             except Exception as e:
#                 logger.error(f"处理任务过程中出现异常: {str(e)}")


if __name__ == "__main__":
    neo4j_client = Neo4jClient(
        uri="neo4j://localhost:7687",
        user="neo4j",
        password="",
        database=""
    )

    llm_config = {
        "api_key": '',
        "base_url": '',
        'model': 'qwen-max-latest',
        'type': 'maas'
    }

    llm_client = LLMClient.from_config(llm_config)
    processor = EnhancedQuestionProcessor(llm_client)

    # 加载测试数据
    with open("./data/test.json", 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    # 处理每个问题
    for item in test_data:
        question = item.get("question")
        try:
            # 核心处理流程
            response = processor.process_question(question)

            # 写入结果
            write_response_to_txt(
                question=question,
                response=response,
                output_file='./cypher_result_0304.txt'
            )

        except Exception as e:
            logger.error(f"处理问题失败: {question} - {str(e)}")
            write_response_to_txt(
                question=question,
                response=f"处理失败: {str(e)}",
                output_file='./cypher_result_0304.txt'
            )

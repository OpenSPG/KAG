# -*- coding: utf-8 -*-
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.
import json
import logging
import re
from typing import List

from kag.common.utils import get_now, resolve_instance
from kag.interface import PromptABC, Task
from kag.interface.common.vectorize_model import VectorizeModelABC
from kag.interface.solver.base_model import LogicNode
from kag.interface.solver.model.schema_utils import SchemaUtils
from kag.common.config import LogicFormConfiguration
from kag.common.parser.logic_node_parser import (
    ParseLogicForm,
    GetSPONode,
    MathNode,
    DeduceNode,
    GetNode,
)
from kag.common.parser.schema_std import StdSchema

logger = logging.getLogger()


@PromptABC.register("default_lf_static_planning")
class RetrieverLFStaticPlanningPrompt(PromptABC):
    instruct_zh = """"instruction": "你是一个规划专家，你的任务是根据function中的算子来规划问题",
        "function": [
          {
              "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`], p.prop=`value`, s.prop=`value`, o.prop=`value`)",
              "description": "用于文本信息检索，根据spo检索信息，s、p、o不能在同一表达式中反复多次出现，可对s、p、o进行带约束查询；多跳则进行多次检索。当前变量引用前文变量时，变量名必须和指代的变量名一致，且只需给出变量名，实体类型及名称仅在首次引用时给定。prop为被约束的属性名,属性约束的值`value`可以是文本、常数，也可以引用前面函数中的变量名"
          },
          {
              "function_declaration": "Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alias",
              "description": "执行计算，该算子包含数值计算或排序计数等集合操作。content给出输入信息，可以为文本或引用的变量名。target为计算的目标，通常是当前子问题。math_alias为变量名，表示其计算结果，可在后续动作中被引用。"
          },
          {
              "function_declaration": "Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias",
              "description": "推断，对检索或计算结果进行推断，以回答问题，op=judgement|entailment|extract|choice|multiChoice 分别表示判断、条件推理、信息提取、选择题、多项选择题。content为问题、历史对话或检索结果，可以是文本片段或以变量名指代。target为推理的目标。"
          },     
          {
              "function_declaration": "Output(alias)",
              "description": "返回指定变量名代表的信息，作为最后的输出结果"
          }
        ],
        """
    default_case_zh = [
        {
            "query": "吴京是谁",
            "answer": "首先需要检索公众人物'吴京'的基本信息\n```\nStep1:查询吴京\nAction1:Retrieval(s=s1:公众人物[`吴京`], p=p1, o=o1)\n```\n根据检索结果输出吴京的简介\n```\nStep2:输出s1\nAction2:output(s1)\n```",
        },
        {
            "query": "张三是张四的爸爸，张二是张三的爸爸，哪么张二和张四是什么关系",
            "answer": "首先需要根据已知的家庭关系推断张二和张四的亲属关系\n```\nStep1: 推断张二和张四的关系\nAction1:Deduce(op=entailment,content=[`张三是张四的爸爸`, `张二是张三的爸爸`],target=`张二和张四是什么关系`)->res\n```\n最后输出推断结果\n```\nStep2:输出res\nAction2:output(res)\n```",
        },
        {
            "query": "30+6加上华为创始人在2024年的年龄是多少",
            "answer": "首先需要解决数学问题30+6\n```\nStep1:30+6 等于多少？\nAction1:Math(content=[], target=`30+6等于多少`)->math1\n```\n确定华为的创始人是谁\n```\nStep2:华为创始人是谁？\nAction2:Retrieval(s=s2:企业[`华为`],p=p2:创始人,o=o2)\n```\n获取创始人出生年份\n```\nStep3:华为创始人出生在什么年份？\nAction3:Retrieval(s=o2,p=p3:出生年份,o=o3)\n```\n将数学结果与年龄相加\n```\nStep4:30+6的结果与华为创始人在2024年的年龄相加是多少？\nAction4:Math(content=[`math1`,`o3`], target=`30+6的结果与华为创始人在2024年的年龄相加是多少？`)->math4\n```\n输出最终结果\n```\nStep5:输出math4\nAction5:output(math4)\n```",
        },
        {
            "query": "C罗在2011年效力的运动队中，哪一支成立时间最晚？",
            "answer": "首先需要查询C罗在2011年的效力球队\n```\nStep1:C罗在2011年效力于哪些运动队？\nAction1:Retrieval(s=s1:球员[`C罗`], p=p1:2011年效力于, o=o1:运动队)\n```\n获取这些球队的成立年份\n```\nStep2:这些队伍的成立年份分别是？\nAction2:Retrieval(s=o1, p=p2:成立年份, o=o2:年份)\n```\n比较成立时间并选择最晚的\n```\nStep3:哪支队伍成立最晚？\nAction3:Math(content=[`o2`], target=`成立时间最晚的球队`)->math3\n```",
        },
        {
            "query": "发表《心理治疗整合期刊》的协会首任主席是谁？",
            "answer": "首先需要确定期刊的出版机构\n```\nStep1:哪家协会出版《心理治疗整合期刊》？\nAction1:Retrieval(s=s1:出版物[`心理治疗整合期刊`], p=p1:出版机构, o=o1:协会)\n```\n查询该协会的首任主席\n```\nStep2:该协会的首任主席是谁？\nAction2:Retrieval(s=o1, p=p2:首任主席, o=o2:人物)\n```",
        },
        {
            "query": "波卡洪塔斯丘所在州何时加入美国？",
            "answer": "首先需要定位波卡洪塔斯丘的地理位置\n```\nStep1:波卡洪塔斯丘位于哪个州？\nAction1:Retrieval(s=s1:历史遗址[`波卡洪塔斯丘`], p=p1:所在地, o=o1:州)\n```\n查询该州加入美国的时间\n```\nStep2:该州何时成为美国的一部分？\nAction2:Retrieval(s=o1, p=p2:加入美国年份, o=o2:日期)\n```",
        },
        {
            "query": "两次龙卷风爆发中哪次致死人数更多？",
            "answer": "首先需要确定两次龙卷风事件\n```\nStep1:第一次龙卷风爆发是哪个事件？\nAction1:Retrieval(s=s1:事件[`龙卷风爆发`], p=p1:第一次事件, o=o1:事件)\n```\n获取第二次事件信息\n```\nStep2:第二次龙卷风爆发是哪个事件？\nAction2:Retrieval(s=s2:事件[`龙卷风爆发`], p=p2:第二次事件, o=o2:事件)\n```\n分别查询死亡人数\n```\nStep3:第一次事件的死亡人数？\nAction3:Retrieval(s=s1, p=p3:致死人数, o=o3:数字)\n```\n```\nStep4:第二次事件的死亡人数？\nAction4:Retrieval(s=s2, p=p4:致死人数, o=o4:数字)\n```\n比较死亡人数并确定更多的一方\n```\nStep5:比较两次事件的死亡人数\nAction5:Math(content=[`o3`,`o4`], target=`致死人数更多的事件`)->math5\n```",
        },
        {
            "query": "电影《Aas Ka Panchhi》和《Phoolwari》哪部更早上映？",
            "answer": "首先需要查询《Aas Ka Panchhi》的上映时间\n```\nStep1:《Aas Ka Panchhi》的上映时间是？\nAction1:Retrieval(s=s1:作品[`Aas Ka Panchhi`], p=p1:上映时间, o=o1:日期)\n```\n查询《Phoolwari》的上映时间\n```\nStep2:《Phoolwari》的上映时间是？\nAction2:Retrieval(s=s2:作品[`Phoolwari`], p=p2:上映时间, o=o2:日期)\n```\n比较两部电影的上映时间\n```\nStep3:比较两部电影的上映时间\nAction3:Math(content=[`o1`,`o2`], target=`更早上映的电影`)->math5\n```",
        },
    ]

    instruct_en = """"instruction": "You are a planning expert who designs plans based on the operators in the function.",
        "function_description": "functionName is operator name;the function format is functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
        "function": [
          {
              "functionName": "Retrieval",
              "function_declaration": "Retrieval(s=s_alias:type[name], p=p_alias:edge, o=o_alias:type[name])",
               "description": "For text information retrieval, retrieve information based on spo. The elements s, p, and o cannot appear multiple times in the same expression. Constrained queries can be performed on s, p, and o. Multi-hop retrieval involves performing multiple retrievals. When referencing a variable from the current context to a prior one, the variable name must match the referenced variable name exactly, and only the variable name needs to be provided; the entity type and name are given only when first referenced."
          },
          {
              "functionName": "Math",
              "function_declaration": "Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alias",
              "description": "Perform calculations, which include set operations such as numerical calculations or sorting and counting. Content provides input information, which can be text or a referenced variable name. The target is the computational objective, usually the current subproblem. Math_alia is a variable name that represents its calculation result and can be referenced in subsequent actions."
          },
          {
              "functionName": "Deduce",
              "function_declaration": "Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias",
              "description": "Inference refers to the process of inferring search or calculation results to answer questions. op=judgement | entailment | rule | choice | multiChoice respectively represents true or false questions, implication reasoning (such as sentencing), fragment extraction, multiple choice questions, and multiple-choice questions. Content refers to questions, historical conversations, or search results, which can be text fragments or referred to by variable names. The target is the inference objective."
          },
          {
              "functionName": "Output",
              "function_declaration": "Output(A,B,...)",
              "description": "Directly output A, B, ... as answers, where A and B are variable names referring to previous retrieval or calculation results."
          }
        ],"""

    default_case_en = [
        {
            "query": "Which sports team for which Cristiano Ronaldo played in 2011 was founded last ?",
            "answer": "First, retrieve the sports teams Cristiano Ronaldo played for in 2011\n```\nStep1:Which Sports Teams Cristiano Ronaldo Played for in 2011 ?\nAction1:Retrieval(s=s1:Player[`Cristiano Ronaldo`],p=p1:PlayedForIn2011Year,o=o1:SportsTeam)\n```\nNext, obtain the foundation years of these teams\n```\nStep2: What are the foundation years of the teams retrieved in Step1?\nAction2:Retrieval(s=o1,p=p2:FoundationYear,o=o2:Year)\n```\nFinally, determine the team founded last by comparing years\n```\nStep3:Which team has the most recent foundation year based on Step2's results?\nAction3:Math(content=[`o2`], target=`Which team was founded last?`)->math3\n```",
        },
        {
            "query": "John is Mike's father, and James is John's father. What is the relationship between James and Mike?",
            "answer": "First, infer the relationship between James and Mike\n```\nStep1: What is the familial relationship between James and Mike?\nAction1:Deduce(op=entailment,content=[`John is Mike's father`, `James is John's father`],target=`What is the relationship between James and Mike?`)->res\n```\nOutput the deduced result\n```\nStep2:What is the final answer from the relationship deduction by Step1?\nAction2:output(res)\n```",
        },
        {
            "query": "Who was the first president of the association which published Journal of Psychotherapy Integration?",
            "answer": "First, identify the association publishing the Journal of Psychotherapy Integration\n```\nStep1:Which association publishes the Journal of Psychotherapy Integration?\nAction1:Retrieval(s=s1:Player[`Psychotherapy Integration`],p=p1:Publish,o=o1:Association)\n```\nNext, retrieve the first president of this association\n```\nStep2: Who was the first president of the association retrieved in Step1?\nAction2:Retrieval(s=o1,p=p2:FirstPresident,o=o2:Person)\n```",
        },
        {
            "query": "When did the state where Pocahontas Mounds is located become part of the United States?",
            "answer": "First, locate the state where *Pocahontas Mounds* is situated\n```\nStep1:Which State Where Pocahontas Mounds is Located ?\nAction1:Retrieval(s=s1:HistoricalSite[`Pocahontas Mounds`], p=p1:LocatedIn, o=o1:State)\n```\nNext, retrieve the state's admission year to the U.S.\n```\nStep2:What year was the state retrieved in Step1 admitted to the U.S.?\nAction2:Retrieval(s=o1, p=p2:StatehoodYear, o=o2:Date)\n```",
        },
        {
            "query": "Which of the two tornado outbreaks killed the most people?",
            "answer": "First, identify the two tornado outbreaks\n```\nStep1:Which is the first tornado outbreaks ?\nAction1:Retrieval(s=s1:Event[`Tornado Outbreak`], p=p1:TheFirst, o=o1:Event)\n```\nConfirm the second event details\n```\nStep2:Which is the second tornado outbreaks ?\nAction2:Retrieval(s=s2:Event[`Tornado Outbreak`], p=p2:TheSecond, o=o2:Event)\n```\nRetrieve casualties from first outbreak\n```\nStep3:How many people died in the first tornado outbreak retrieved in Step1?\nAction3:Retrieval(s=s1, p=p3:KilledPeopleNumber, o=o3:Number)\n```\nRetrieve casualties from second outbreak\n```\nStep4:How many people died in the second tornado outbreak retrieved in Step2?\nAction4:Retrieval(s=s2, p=p4:KilledPeopleNumber, o=o4:Number)\n```\nCompare fatality numbers between events\n```\nStep5:To compare the death toll between two tornado outbreaks to determine which one had more fatalities.\nAction5:Math(content[`o3`,`o4`], target=`Which one had more fatalities?`)->math5\n```",
        },
        {
            "query": "Which film was released first, Aas Ka Panchhi or Phoolwari?",
            "answer": "First, retrieve *Aas Ka Panchhi*'s release date\n```\nStep1:When was Aas Ka Panchhi released ?\nAction1:Retrieval(s=s1:Work[`Aas Ka Panchhi`], p=p1:ReleaseTime, o=o1:Date)\n```\nNext, retrieve *Phoolwari*'s release information\n```\nStep2:When was Phoolwari released ?\nAction2:Retrieval(s=s2:Work[`Phoolwari`], p=p2:ReleaseTime, o=o2:Date)\n```\nCompare release dates to determine earliest\n```\nStep3:Comparing the release dates of Aas Ka Panchi and Phoolwari, who came earlier ? based by retrieved in Step1 and Step2\nAction3:Math(content=[`o1`,`o2`], target=`Comparing the release dates of Aas Ka Panchi and Phoolwari, who came earlier?`)->math5\n```",
        },
    ]

    def __init__(self, std_schema: StdSchema = None, **kwargs):
        self.template_zh = f"""
            {{
                "time": "今天是{get_now(language='zh')}"
                {self.instruct_zh}
                "cases": {json.dumps(self.default_case_zh, ensure_ascii=False, indent=2)},
                "output_format": "使用文本格式输出，只输出case中的answer内容，不要在开始输出'```markdown'",
                "tips": [
                    "输出每一步的Step和Action前可以增加一些思路输出，类似’首先...其次...最后...‘",
                    "Each `Step` must contain exactly one `Action`",
                    "Each step is an indivisible atomic question, please re-split accordingly.",
                    "Output also needs to be a separate step."
                    "Step和Action内容需要使用代码风格输出"
                ],
                "query": "$query"
            }}   
                """
        self.template_en = f"""
            {{
                "time": "Today is {get_now(language='en')}"
                {self.instruct_en},
                "cases":  {json.dumps(self.default_case_en, ensure_ascii=False, indent=2)},
                "output_format": "Output the answer content from the case in plain text format, do not print'```markdown' at the beginning",
                "tips": [
                    "Before outputting each Step and Action, you can add some thought process, such as 'First... Then... Finally...'", 
                    "Each Step only contain one Action", 
                    "Each step should be an indivisible atomic question; please re-split accordingly.", 
                    "Output also needs to be a separate step.", 
                    "Content for Step and Action should be output in code style",
                    "Step and Action/Output must be on a separate line and in the format XXX: YYY"
                ],
                "query": "$query"
            }}   
                """
        super().__init__(**kwargs)

        if std_schema is not None:
            logger.info(
                f"KAG_PROJECT_ID: {self.kag_project_config.project_id}, KAG_PROJECT_HOST_ADDR: {self.kag_project_config.host_addr}"
            )
            self.schema_helper: SchemaUtils = SchemaUtils(
                LogicFormConfiguration(
                    {
                        "KAG_PROJECT_ID": self.kag_project_config.project_id,
                        "KAG_PROJECT_HOST_ADDR": self.kag_project_config.host_addr,
                    }
                )
            )
            self.std_schema = resolve_instance(
                std_schema,
                default_config={"type": "default_std_schema"},
                from_config_func=StdSchema.from_config,
            )

            self.logic_node_parser = ParseLogicForm(
                schema=self.schema_helper, schema_retrieval=self.std_schema
            )
        else:
            self.logic_node_parser = ParseLogicForm(schema=None, schema_retrieval=None)

    def is_json_format(self):
        return False

    @property
    def template_variables(self) -> List[str]:
        return ["query"]

    def parse_steps(self, response):
        logger.debug(f"logic form:{response}")
        _output_string = response.replace("：", ":")
        _output_string = _output_string.strip()
        sub_querys = []
        logic_forms = []
        current_sub_query = ""
        for line in _output_string.split("\n"):
            if line.startswith("Step"):
                sub_querys_regex = re.search("Step\d+:(.*)", line)
                if sub_querys_regex is not None:
                    sub_querys.append(sub_querys_regex.group(1))
                    current_sub_query = sub_querys_regex.group(1)
                    current_sub_query = current_sub_query.strip()
                    if current_sub_query == "":
                        raise RuntimeError(f"{line} is not step query")
            elif line.startswith("Action"):
                logic_forms_regex = re.search("Action\d+:(.*)", line)
                if logic_forms_regex:
                    logic_forms.append(logic_forms_regex.group(1))
                    if len(logic_forms) - len(sub_querys) == 1:
                        sub_querys.append(current_sub_query)
        if len(sub_querys) != len(logic_forms):
            raise RuntimeError(
                f"sub query not equal logic form num {len(sub_querys)} != {len(logic_forms)}"
            )
        return sub_querys, logic_forms

    def _parse_lf(self, sub_queries, logic_forms) -> List[LogicNode]:
        return self.logic_node_parser.parse_logic_form_set(logic_forms, sub_queries, "")

    def _get_dep_task_id(self, logic_forms):
        all_alias_index_map = {}

        def add_index_map(alias, index):
            if alias in all_alias_index_map.keys():
                return
            all_alias_index_map[alias] = index

        for i, logic_form in enumerate(logic_forms):
            if isinstance(logic_form, GetSPONode):
                add_index_map(logic_form.s.alias_name.alias_name, i)
                add_index_map(logic_form.p.alias_name.alias_name, i)
                add_index_map(logic_form.o.alias_name.alias_name, i)
            elif isinstance(logic_form, MathNode) or isinstance(logic_form, DeduceNode):
                add_index_map(logic_form.alias_name, i)

        return all_alias_index_map

    def _get_task_dep(self, index, logic_node, dep_task):
        ret = []

        def add_dep_by_index(alias_name):
            alias_index = dep_task[alias_name]
            if alias_index < index:
                ret.append(alias_index)

        if isinstance(logic_node, GetSPONode):
            add_dep_by_index(logic_node.s.alias_name.alias_name)
            add_dep_by_index(logic_node.p.alias_name.alias_name)
            add_dep_by_index(logic_node.o.alias_name.alias_name)
        if isinstance(logic_node, GetNode):
            return []

        if isinstance(logic_node, MathNode) or isinstance(logic_node, DeduceNode):
            for alias in dep_task.keys():
                if alias in logic_node.content:
                    ret.append(dep_task[alias])
        return ret

    def parse_response(self, response: str, **kwargs):
        sub_queries, logic_forms = self.parse_steps(response)
        logic_forms = self._parse_lf(sub_queries, logic_forms)
        tasks_dep = {}
        alias_dep = self._get_dep_task_id(logic_forms)
        for i, logic_form in enumerate(logic_forms):
            deps = self._get_task_dep(i, logic_form, alias_dep)
            task_deps = [] if i == 0 else [i - 1]
            is_need_rewrite = (
                True if (deps or isinstance(logic_form, GetSPONode)) else False
            )
            if isinstance(logic_form, GetNode) or len(tasks_dep) == 0:
                is_need_rewrite = False
            tasks_dep[i] = {
                "name": f"Step{i+1}",
                "executor": logic_form.operator,
                "dependent_task_ids": task_deps,
                "arguments": {
                    "query": logic_form.sub_query,
                    "logic_form_node": logic_form,
                    "is_need_rewrite": is_need_rewrite,
                },
            }
        return Task.create_tasks_from_dag(tasks_dep)

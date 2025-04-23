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
import logging
import re
from typing import List
from kag.interface import PromptABC

logger = logging.getLogger()


@PromptABC.register("default_spo_retriever_decompose")
class DefaultSPORetrieverDecomposePrompt(PromptABC):
    instruct_zh = """"instruction": "",
        "function": [
          {
              "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`], p.prop=`value`, s.prop=`value`, o.prop=`value`)",
              "description": "根据spo检索信息，s、p、o不能在同一表达式中反复多次出现，可对s、p、o进行带约束查询；多跳则进行多次检索。当前变量引用前文变量时，变量名必须和指代的变量名一致，且只需给出变量名，实体类型及名称仅在首次引用时给定。prop为被约束的属性名,属性约束的值`value`可以是文本、常数，也可以引用前面函数中的变量名"
          }
        ],
        """
    default_case_zh = """"cases": [
            {
                "query": "吴京是谁",
                "answer": "Step1:查询吴京\nAction1:Retrieval(s=s1:公众人物[`吴京`], p=p1, o=o1)"
            },
            {
                "query": "B公司创始人的妻子是谁",
                "answer": "Step1:B公司创始人是谁？\nAction1:Retrieval(s=s1:企业[`B公司`],p=p1:创始人,o=o1[人物])\nStep2:B公司创始人的妻子是谁？\nAction2:Retrieval(s=o2,p=p2:妻子,o=o2[人物])"
            }
            ],"""

    instruct_en = """    "instruction": "You are a task decomposer. Your job is to break down a complex task into several atomic questions, where each sub-question corresponds to only one Action.",
        "function_description": "functionName is operator name;the function format is functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
        "function": [
          {
              "functionName": "Retrieval",
              "function_declaration": "Retrieval(s=s_alias:type[name], p=p_alias:edge, o=o_alias:type[name], p.prop=value, s.prop=value, o.prop=value)",
               "description": "Retrieval information according to SPO. 's' represents the subject, 'o' represents the object, and they are denoted as variable_name:entity_type[entity_name]. The entity name is an optional parameter and should be provided when there is a specific entity to query. 'p' represents the predicate, which can be a relationship or attribute, denoted as variable_name:edge_type_or_attribute_type. Each variable is assigned a unique variable name, which is used for reference in subsequent mentions. Note that 's', 'p', and 'o' should not appear repeatedly within the same expression; only one set of SPO should be queried at a time. When a variable is a reference to a previously mentioned variable name, the variable name must match the previously mentioned variable name, and only the variable name needs to be provided; the entity type is only given when it is first introduced. And 's.prop', 'o.prop', 'p.prop' represent the properties of subject, object and edge. the subject (s), predicate (p), and object (o) should not repeatedly appear multiple times within the same expression.Constraints can be applied specifically to the predicate (p) for more targeted querying. For multi-hop queries, each hop necessitates a separate retrieval operation. When a current variable references a previously mentioned variable, the variable name must be identical to the one it represents, and only the variable name needs to be stated. The entity type and name should be provided only upon the first mention of the variable; Note Use camelCase for types. Enclose strings in square brackets with backticks to avoid conflicts with keywords."
          }
        ],"""

    default_case_en = """"cases": [
            {
                "query": "Which sports team for which Cristiano Ronaldo played in 2011 was founded last ?",
                "answer": "Step1:Which Sports Teams Cristiano Ronaldo Played for in 2011 ?\nAction1:Retrieval(s=s1:Player[`Cristiano Ronaldo`],p=p1:PlayedForIn2011Year,o=o1:SportsTeam)\nStep2:In which year were these teams established ?\nAction2:Retrieval(s=o1,p=p2:FoundationYear,o=o2:Year)"
            },
            {
                "query": "Who was the first president of the association which published Journal of Psychotherapy Integration?",
                "answer": "Step1:Which association that publishes the Journal of Psychotherapy Integration ?\nAction1:Retrieval(s=s1:Player[`Psychotherapy Integration`],p=p1:Publish,o=o1:Association)\nStep2:Who was the first president of that specific association?\nAction2:Retrieval(s=o1,p=p2:FirstPresident,o=o2:Person)"
            },
            {
                "query": "When did the state where Pocahontas Mounds is located become part of the United States?",
                "answer": "Step1:Which State Where Pocahontas Mounds is Located ?\nAction1:Retrieval(s=s1:HistoricalSite[`Pocahontas Mounds`], p=p1:LocatedIn, o=o1:State)\nStep2:When did this state become a part of the United States ？\nAction2:Retrieval(s=o1, p=p2:YearOfBecamingPartofTheUnitedStates, o=o2:Date)"
            },
            {
                "query": "Which of the two tornado outbreaks killed the most people?",
                "answer": "Step1:Which is the first tornado outbreaks ?\nAction1:Retrieval(s=s1:Event[`Tornado Outbreak`], p=p1:TheFirst, o=o1:Event)\nStep2:Which is the second tornado outbreaks ?\nAction2:Retrieval(s=s2:Event[`Tornado Outbreak`], p=p2:TheSecond, o=o2:Event)\nStep3:How many people died in the first tornado outbreak ?\nAction3:Retrieval(s=s1, p=p3:KilledPeopleNumber, o=o3:Number)\nStep4:How many people died in the second tornado outbreak ?\nAction4:Retrieval(s=s2, p=p4:KilledPeopleNumber, o=o4:Number)"
            },
            {
                "query": "Which film was released first, Aas Ka Panchhi or Phoolwari?",
                "answer": "Step1:When was Aas Ka Panchhi released ?\nAction1:Retrieval(s=s1:Work[`Aas Ka Panchhi`], p=p1:ReleaseTime, o=o1:Date)\nStep2:When was Phoolwari released ?\nAction2:Retrieval(s=s2:Work[`Phoolwari`], p=p2:ReleaseTime, o=o2:Date)"
            }
        ],"""

    def __init__(self, **kwargs):
        self.template_zh = f"""
            {{
                {self.instruct_zh}
                {self.default_case_zh}
                "output_format": "Only start with output words in answer, for examples: `Step`, `Action` content. Do not output json format",
                "tips": [
                    "Each `Step` must contain exactly one `Action`",
                    "Each step is an indivisible atomic question, please re-split accordingly."
                ],
                "query": "$question"
            }}   
                """
        self.template_en = f"""
            {{
                {self.instruct_en}
                {self.default_case_en}
                "output_format": "Only start with output words in answer, for examples: `Step`, `Action` content. Do not output json format",
                "tips": [
                    "Each `Step` must contain exactly one `Action`",
                    "Each step is an indivisible atomic question, please re-split accordingly."
                ],
                "query": "$question"
            }}   
                """
        super().__init__(**kwargs)

    @property
    def template_variables(self) -> List[str]:
        return ["question"]

    def parse_response(self, response: str, **kwargs):
        try:
            logger.debug(f"logic form:{response}")
            _output_string = response.replace("：", ":")
            _output_string = response.strip()
            sub_querys = []
            logic_forms = []
            current_sub_query = ""
            for line in _output_string.split("\n"):
                if line.startswith("Step"):
                    sub_querys_regex = re.search("Step\d+:(.*)", line)
                    if sub_querys_regex is not None:
                        sub_querys.append(sub_querys_regex.group(1))
                        current_sub_query = sub_querys_regex.group(1)
                        if current_sub_query == "":
                            raise RuntimeError(f"{line} is not step query")
                elif line.startswith("Output"):
                    sub_querys.append("output")
                elif line.startswith("Action"):
                    logic_forms_regex = re.search("Action\d+:(.*)", line)
                    if logic_forms_regex:
                        logic_forms.append(logic_forms_regex.group(1))
                        if len(logic_forms) - len(sub_querys) == 1:
                            sub_querys.append(current_sub_query)
            return sub_querys, logic_forms
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return [], []

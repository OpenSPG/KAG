import logging
import re
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_logic_form_plan")
class LogicFormPlanPrompt(PromptABC):
    instruct_zh = """"instruction": "",
            "function_description": "functionName为算子名;基本格式为 functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
            "function": [
              {
                  "functionName": "Retrieval",
                  "function_declaration": "Retrieval(s=s_alias:entity_type[`entity_name`], p=p_alias:edge_type, o=o_alias:entity_type[`entity_name`], p.prop=`value`, s.prop=`value`, o.prop=`value`)",
                  "description": "根据spo检索信息，s、p、o不能在同一表达式中反复多次出现，可对s、p、o进行带约束查询；多跳则进行多次检索。当前变量引用前文变量时，变量名必须和指代的变量名一致，且只需给出变量名，实体类型及名称仅在首次引用时给定。属性约束`value`可以是文本、常数，也可以引用前面函数中的变量名"
              },
              {
                  "functionName": "Math",
                  "function_declaration": "Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alias",
                  "description": "执行计算，该算子包含数值计算或排序计数等集合操作。content给出输入信息，可以为文本或引用的变量名。target为计算的目标，通常是当前子问题。math_alias为变量名，表示其计算结果，可在后续动作中被引用。"
              },
              {
                  "functionName": "Deduce",
                  "function_declaration": "Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias",
                  "description": "推断，对检索或计算结果进行推断，以回答问题，op=judgement|entailment|rule|choice|multiChoice 分别表示判断题、蕴涵推理（条件推理，如量刑）、片段抽取、选择题、多项选择题。content为问题、历史对话或检索结果，可以是文本片段或以变量名指代。target为推理的目标。"
              },     
              {
                  "functionName": "Output",
                  "function_declaration": "Output(alias)",
                  "description": "返回指定变量名代表的信息，作为最后的输出结果"
              }
            ],
            """
    default_case_zh = """"cases": [
            {
                "Action": "吴京是谁",
                "answer": "Step1:查询吴京\nAction1:get_spo(s=s1:公众人物[吴京], p=p1, o=o1)\nOutput:输出s1\nAction2:get(s1)"
            },
            {
                "query": "30+6加上华为创始人在2024年的年龄是多少",
                "answer": "Step1:30+6 等于多少？\nAction1:sum(30,6)->sum1\nStep2:华为创始人是谁？\nAction2:get_spo(s=s2:企业[华为],p=p2:创始人,o=o2)\nStep3:华为创始人出生在什么年份？\nAction3:get_spo(s=o2,p=p3:出生年份,o=o3)\nStep4:华为创始人在2024年的年龄是多少？\nAction4:sum(2024,-o3)->sum4\nStep5:30+6的结果与华为创始人在2024年的年龄相加是多少？\nAction5:sum(sum1,sum4)->sum5\nStep6:输出sum5\nAction6:get(sum5)"
            }
        ],"""



    instruct_en = """    "instruction": "",
            "function_description": "functionName is operator name;the function format is functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
            "function": [
              {
                  "functionName": "Retrieval",
                  "function_declaration": "Retrieval(s=s_alias:type[name], p=p_alias:edge, o=o_alias:type[name], p.prop=value, s.prop=value, o.prop=value)",
                   "description": "Retrieval information according to SPO. 's' represents the subject, 'o' represents the object, and they are denoted as variable_name:entity_type[entity_name]. The entity name is an optional parameter and should be provided when there is a specific entity to query. 'p' represents the predicate, which can be a relationship or attribute, denoted as variable_name:edge_type_or_attribute_type. Each variable is assigned a unique variable name, which is used for reference in subsequent mentions. Note that 's', 'p', and 'o' should not appear repeatedly within the same expression; only one set of SPO should be queried at a time. When a variable is a reference to a previously mentioned variable name, the variable name must match the previously mentioned variable name, and only the variable name needs to be provided; the entity type is only given when it is first introduced. And 's.prop', 'o.prop', 'p.prop' represent the properties of subject, object and edge. the subject (s), predicate (p), and object (o) should not repeatedly appear multiple times within the same expression.Constraints can be applied specifically to the predicate (p) for more targeted querying. For multi-hop queries, each hop necessitates a separate retrieval operation. When a current variable references a previously mentioned variable, the variable name must be identical to the one it represents, and only the variable name needs to be stated. The entity type and name should be provided only upon the first mention of the variable; Note Use camelCase for types. Enclose strings in square brackets with backticks to avoid conflicts with keywords."
              },
              {
                  "functionName": "Math",
                  "function_declaration": "Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alias",
                  "description": "Perform calculations, which include set operations such as numerical calculations or sorting and counting. Content provides input information, which can be text or a referenced variable name. The target is the computational objective, usually the current subproblem. Math_alia is a variable name that represents its calculation result and can be referenced in subsequent actions."
              },
              {
                  "functionName": "Deduce",
                  "function_declaration": "Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias",
                  "description": "Inference refers to the process of inferring search or calculation results to answer questions. op=judgment | entailment | rule | choice | multiChoice respectively represents true or false questions, implication reasoning (such as sentencing), fragment extraction, multiple choice questions, and multiple-choice questions. Content refers to questions, historical conversations, or search results, which can be text fragments or referred to by variable names. The target is the inference objective."
              },
              {
                  "functionName": "Output",
                  "function_decl:aration": "Output(A,B,...)",
                  "description": "Directly output A, B, ... as answers, where A and B are variable names referring to previous retrieval or calculation results."
              }
            ],"""

    default_case_en = """"cases": [
            {
                "query": "Which sports team for which Cristiano Ronaldo played in 2011 was founded last ?",
                "answer": "Step1:Which Sports Teams Cristiano Ronaldo Played for in 2011 ?\nAction1:get_spo(s=s1:Player[Cristiano Ronaldo],p=p1:PlayedForIn2011Year,o=o1:SportsTeam)\nStep2:In which year were these teams established ?\nAction2:get_spo(s=o1,p=p2:FoundationYear,o=o2:Year)\nStep3:Which team was founded last ?\nAction3:sort(set=o1, orderby=o2, direction=max, limit=1)"
            },
            {
                "query": "Who was the first president of the association which published Journal of Psychotherapy Integration?",
                "answer": "Step1:Which association that publishes the Journal of Psychotherapy Integration ?\nAction1:Journal(s=s1:Player[Psychotherapy Integration],p=p1:Publish,o=o1:Association)\nStep2:Who was the first president of that specific association?\nAction2:get_spo(s=o1,p=p2:FirstPresident,o=o2:Person)"
            },
            {
                "query": "When did the state where Pocahontas Mounds is located become part of the United States?",
                "answer": "Step1:Which State Where Pocahontas Mounds is Located ?\nAction1:get_spo(s=s1:HistoricalSite[Pocahontas Mounds], p=p1:LocatedIn, o=o1:State)\nStep2:When did this state become a part of the United States ？\nAction2:get_spo(s=o1, p=p2:YearOfBecamingPartofTheUnitedStates, o=o2:Date)"
            },
            {
                "query": "Which of the two tornado outbreaks killed the most people?",
                "answer": "Step1:Which is the first tornado outbreaks ?\nAction1:get_spo(s=s1:Event[Tornado Outbreak], p=p1:TheFirst, o=o1:Event)\nStep2:Which is the second tornado outbreaks ?\nAction2:get_spo(s=s2:Event[Tornado Outbreak], p=p2:TheSecond, o=o2:Event)\nStep3:How many people died in the first tornado outbreak ?\nAction3:get_spo(s=s1, p=p3:KilledPeopleNumber, o=o3:Number)\nStep4:How many people died in the second tornado outbreak ?\nAction4:get_spo(s=s2, p=p4:KilledPeopleNumber, o=o4:Number)\nStep5:To compare the death toll between two tornado outbreaks to determine which one had more fatalities.\nAction5:compare(set=[o3,o4], op=max)"
            }
        ],"""


    def __init__(self, **kwargs):
        self.template_zh = f"""
        {{
            {self.instruct_zh}
            {self.default_case_zh}
            "output_format": "only output `Step`, `Action` and `Output` content",
            "query": "$question"
        }}   
            """
        self.template_en = f"""
        {{
            {self.instruct_en}
            {self.default_case_en}
            "output_format": "Only output words in answer, for examples: `Step`, `Action` content",
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

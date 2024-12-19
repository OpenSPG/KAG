import logging
import re
from string import Template
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)

from kag.common.base.prompt_op import PromptOp


class LogicFormPlanPrompt(PromptOp):
    template_en = """
{
  "instruction": "Given a list of functions, each accompanied by a functionName, function_declaration, and description, your task is to rewrite queries using sub-queries while incorporating function calls. We will also provide examples to guide you through this process. Please note that the final step should involve either sorting, deduction, or outputting the results.",
  "function_description": "functionName is operator name;the function format is functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),Parameters are in parentheses, those enclosed in [] are optional, and those not enclosed are required parameters. \n Note, The last function must be Deduce or Output",
  "output_format": "Output the string without formatting, and do not include any markdown tags. ",
  "function": [
    {
      "functionName": "Retrieval",
      "function_declaration": "Retrieval(s=s_alias:type[`name`], p=p_alias:edge, o=o_alias:type[`name`], p.prop=`value`, s.prop=`value`, o.prop=`value`)",
      "description": "Retrieval information according to SPO. 's' represents the subject, 'o' represents the object, and they are denoted as variable_name:entity_type[entity_name]. The entity name is an optional parameter and should be provided when there is a specific entity to query. 'p' represents the predicate, which can be a relationship or attribute, denoted as variable_name:edge_type_or_attribute_type. Each variable is assigned a unique variable name, which is used for reference in subsequent mentions. Note that 's', 'p', and 'o' should not appear repeatedly within the same expression; only one set of SPO should be queried at a time. When a variable is a reference to a previously mentioned variable name, the variable name must match the previously mentioned variable name, and only the variable name needs to be provided; the entity type is only given when it is first introduced. And 's.prop', 'o.prop', 'p.prop' represent the properties of subject, object and edge. the subject (s), predicate (p), and object (o) should not repeatedly appear multiple times within the same expression.Constraints can be applied specifically to the predicate (p) for more targeted querying. For multi-hop queries, each hop necessitates a separate retrieval operation. When a current variable references a previously mentioned variable, the variable name must be identical to the one it represents, and only the variable name needs to be stated. The entity type and name should be provided only upon the first mention of the variable; Note Use camelCase for types. Enclose strings in square brackets with backticks to avoid conflicts with keywords."
    },
    {
      "functionName": "Sort",
      "function_declaration": "Sort(set=A, direction=ASC|DESC, limit=n)->sort_alias",
      "description": "Sort a set of retrieval results. A is the variable name for the retrieved SPO (s_alias, o_alias, or p_alias.prop). Direction specifies the sorting order: direction=ASC means ascending order, direction=DESC means descending order. Limit=n means  output the top_n results"
    },
    {
      "functionName": "Math",
      "function_declaration": "Math(expr)->math_alias expr:In Python eval syntax, operations can be performed on sets, for example: counting: abs(A); summing: sum(A)",
      "description": "Perform calculations where expr is in Python syntax, allowing computations on retrieval results (sets) or constants. math_alias is the calculation result and can be referenced as a variable name in subsequent actions"
    },
    {
      "functionName": "Deduce",
      "function_declaration": "Deduce(op=judgement|extract|entailment|choice|multiChoice, content=[`XXX`], target=`XXX`)->deduce_alias",
      "description": "Inference, infer from retrieval or calculation results to answer questions, where 'op' can be 'judgement', 'extract', 'entailment', 'choice', or 'multiChoice'. These represent judgment questions, entailment reasoning (conditional reasoning, such as sentencing), rule reasoning (such as medical diagnosis), multiple-choice questions, and multiple-choice questions respectively."
    },
    {
      "functionName": "Output",
      "function_decl:aration": "Output(A,B,...)",
      "description": "Directly output A, B, ... as answers, where A and B are variable names referring to previous retrieval or calculation results."
    }
  ],
  "cases": [
    {
      "query": "What was gaming revenue in 2020 if it continues to grow at its current rate?",
      "answer": "Step1: Get gaming revenue for 2019, year before 2020.\nAction1: Retrieval(s=s1:MetricConstraint[`gaming`,`2019`], p=p1:dimension, o=o1:Metric)\nStep2: Get gaming revenue for 2018, year before 2019.\nAction2: Retrieval(s=s2:MetricConstraint[`gaming`,`2018`], p=p2:dimension, o=o2:Metric)\nStep3: Calculate the percentage change.\nAction3: Math((o1-o2)/o2)->math1\nStep4: Calculate projected revenue based on percentae change.\nAction4: Math((math1+1)*o1)->math2\nStep5: Output math2.\nAction5: Output(math2)",
    },
    {
      "query": "What is the sum of 30 + 6 and the age of the founder of Tesla in 2027 ?",
      "answer": "Step1: What is the sum of 30 and 6 ?\nAction1: Math(30+6)->math1\nStep2: Who is the founder of Tesla?\nAction2: Retrieval(s=s2:company[`Tesla`], p=p2:founder, o=o2)\nStep3: In which year was the founder of Tesla born?\nAction3: Retrieval(s=o2, p=p3:yearOfBirth, o=o3)\nStep4: How old will the founder of Tesla be in the year 2027?\nAction4: Math(2027-o3)->math4\nStep5: What is the sum of math1 and math4?\nAction5: Math(math1+math4)->math5\nStep6: output result. \nAction6: Output(math5)"
    }
  ],
  "question": "$question"
}
"""
    template_zh = """
{
  "instructions": [
    "给定一个函数列表，每个函数都有 functionName、function_declaration 和 description，你的任务是使用子查询并结合函数调用来重写查询。我们还将提供示例来指导你完成这个过程。请注意，最后一步应该涉及排序、推断或输出结果。",
    "Step描述尽可能包含完整的描述信息，使得子问题的解决者可以理解他的任务背景。"
  ],
  "function_description": "functionName 是操作符名称；函数格式为 functionName(arg_name1=arg_value1, [args_name2=arg_value2, args_name3=arg_value3])。括号中的参数为必选参数，方括号中的为可选参数。注意，最后一个函数必须是 Deduce 或 Output。",
  "output_format": "输出字符串时不做格式处理，并且不包含任何 markdown 标签。",
  "function": [
    {
      "functionName": "Retrieval",
      "function_declaration": "Retrieval(s=s_aliasname, p=p_alias, o=o_aliasname, p.prop=value, s.prop=value, o.prop=value)",
      "description": "根据 SPO 检索信息。's' 表示主语，'o' 表示宾语，它们表示为 variable_nameentity_name。实体名称是一个可选参数，当有具体的实体需要查询时提供。'p' 表示谓词，可以是关系或属性，表示为 variable_name。每个变量分配一个唯一的变量名，用于在后续提及中引用。注意，'s'、'p' 和 'o' 在同一表达式中不应重复出现；每次只能查询一组 SPO。当变量引用先前提及的变量名时，变量名必须与之前提及的变量名一致，并且只需要提供变量名；首次引入变量时需给出实体类型。可以对谓词（p）应用约束以进行更有针对性的查询。对于多跳查询，每跳需要单独的检索操作。当当前变量引用先前提及的变量时，变量名必须与其代表的变量名相同，并且只需声明变量名；实体类型和名称仅在首次提及变量时提供。注意使用驼峰命名法表示类型。用反引号括住字符串以避免与关键字冲突。"
    },
    {
      "functionName": "Sort",
      "function_declaration": "Sort(set=A, direction=ASC|DESC, limit=n)->sort_alias",
      "description": "对检索结果进行排序。A 是检索到的 SPO 的变量名（s_alias, o_alias 或 p_alias.prop）。Direction 指定排序顺序：direction=ASC 表示升序，direction=DESC 表示降序。Limit=n 表示输出前 n 个结果。"
    },
    {
      "functionName": "Math",
      "function_declaration": "Math(expr)->math_alias expr Python eval syntax, operations can be performed on sets, for example: counting: abs(A); summing: sum(A)",
      "description": "执行计算，其中 expr 使用 Python 语法，允许对检索结果（集合）或常量进行计算。math_alias 是计算结果，可以在后续操作中引用为变量名。"
    },
    {
      "functionName": "Deduce",
      "function_declaration": "Deduce(op=judgement|extract|entailment|choice|multiChoice, content=[XXX], target=XXX)->deduce_alias",
      "description": "推理，从检索或计算结果中推断答案，其中 'op' 可以是 'judgement'、'extract'、'entailment'、'choice' 或 'multiChoice'。这些分别表示判断题、推理（如条件推理）、规则推理（如医学诊断）、选择题和多项选择题。"
    },
    {
      "functionName": "Output",
      "function_decl": "Output(A,B,...)",
      "description": "直接输出 A, B,... 作为答案，其中 A 和 B 是指之前的检索或计算结果的变量名。"
    }
  ],
  "cases": [
    {
      "query": "如果游戏收入按照目前的速度增长，2020年的游戏收入是多少？",
      "answer": "Step1: 获取2019年（2020年前一年）的游戏收入。\nAction1: Retrieval(s=s1:MetricConstraint[`gaming`,`2019`], p=p1:dimension, o=o1:Metric)\nStep2: 获取2018年（2019年前一年）的游戏收入。\nAction2: Retrieval(s=s2:MetricConstraint[`gaming`,`2018`], p=p2:dimension, o=o2:Metric)\nStep3: 计算百分比变化。\nAction3: Math((o1-o2)/o2)->math1\nStep4: 基于百分比变化计算预计收入。\nAction4: Math((math1+1)*o1)->math2\nStep5: 输出math2。\nAction5: Output(math2)"
    },
    {
      "query": "What is the sum of 30 + 6 and the age of the founder of Tesla in 2027 ?",
      "answer": "Step1: What is the sum of 30 and 6 ?\nAction1: Math(30+6)->math1\nStep2: Who is the founder of Tesla?\nAction2: Retrieval(s=s2:company[`Tesla`], p=p2:founder, o=o2)\nStep3: In which year was the founder of Tesla born?\nAction3: Retrieval(s=o2, p=p3:yearOfBirth, o=o3)\nStep4: How old will the founder of Tesla be in the year 2027?\nAction4: Math(2027-o3)->math4\nStep5: What is the sum of math1 and math4?\nAction5: Math(math1+math4)->math5\nStep6: output result. \nAction6: Output(math5)"
    },
    {
      "query": "按照2019年前三个季度的增长率，预测第四季度的营业收入是多少？",
      "answer": "Step1: 获取2019年前三个季度的营业收入。\nAction1: Retrieval(s=s1:MetricConstraint[`营业收入`,`2019`], p=p1:dimension, o=o1:Metric)\nStep2: 获取2018年前三个季度的营业收入。\nAction2: Retrieval(s=s1:MetricConstraint[`营业收入`,`2018`], p=p1:dimension, o=o2:Metric)\nStep3: 计算营业收入增长率\nAction3: Math((o1-o2)/o2)->math1\nStep4: 按照增长率计算第四个季度的营业收入\nAction4: Math((o1/3)*(1+math1))->math2\nStep5: 输出math2\nAction5: Output(math2)"
    }
  ],
  "question": "$question"
}
"""

    def __init__(self, language: str):
        super().__init__(language)

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

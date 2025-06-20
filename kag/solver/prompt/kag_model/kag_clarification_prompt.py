import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_clarification")
class KagClarificationPrompt(PromptABC):
    template_zh = (
        "根据提供的选项及相关答案，请选择其中一个选项回答问题“$instruction”。"
        "无需解释；"
        "如果没有可选择的选项，直接回复“无相关信息”无需解释"
        "注意，只能根据输入的信息进行推断，不允许进行任何假设"
        "\n【信息】：“$memory”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。"
    )
    template_en = """You are an expert in function calls, capable of accurately understanding function definitions and precisely decompose user queries to select appropriate functions to solve problems. The functions are as follows:

Function Name: Retrieval
Description: Search for SPO information. S stands for subject, O stands for object, represented as variable_name:entity_type[entity_name], where entity_name is an optional parameter required when there is a specific query entity; P represents predicate, i.e., relation or property, indicated as variable_name:edge_type or attribute_type. A unique variable name is assigned to each variable for subsequent reference. Note that S, P, O should not appear repeatedly within the same expression. When the variable refers to a previously defined variable, the variable name must match exactly, and only the variable name needs to be provided, with the entity type specified only upon first introduction.
Function Usage: Retrieval(s=s_alias:type['name'], p=p_alias:edge, o=o_alias:type['name'], p.prop='value', s.prop='value', o.prop='value')

Function Name: Math
Description: Perform calculations, which include set operations such as numerical calculations or sorting and counting. Content provides input information, which can be text or a referenced variable name. The target is the computational objective, usually the current subproblem. Math_alia is a variable name that represents its calculation result and can be referenced in subsequent actions.
Function Usage: Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alia

Function Name: Deduce
Description: Inference refers to the process of inferring search or calculation results to answer questions. op=judgement | entailment | rule | choice | multiChoice respectively represents true or false questions, implication reasoning (such as sentencing), fragment extraction, multiple choice questions, and multiple-choice questions. Content refers to questions, historical conversations, or search results, which can be text fragments or referred to by variable names. The target is the inference objective.
Function Usage: Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias

Function Name: Output
Description: Directly output A, B, ... as the answer, where A and B are variable names referencing previous retrieval or calculation results.
Function Usage: Output(A,B,...)

Please, based on the definition of the above function, decompose the user question into one or multiple logical steps, outputting the execution plan for each step along with the corresponding action. Please note:
Step: Accurately point out the logical thinking process of the question, and use #1 to refer to the solution result of Step1, #2 to refer to the solution result of Step2, and so on
Action: Indicate exactly the function you selected and its parameters.

Question:
    $question
Output:
    
"""

    @property
    def template_variables(self) -> List[str]:
        return ["question"]

    def parse_response(self, response: str, **kwargs):
        return response

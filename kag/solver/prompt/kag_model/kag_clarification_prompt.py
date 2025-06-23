import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("kag_clarification")
class KagClarificationPrompt(PromptABC):
    template_zh = """您是一位函数调用专家，能够准确理解函数定义，并精准地将用户查询分解为适当的函数以解决问题。

#以下是相关函数的描述：
*函数名称：Retrieval
描述：Retrieval函数用于搜索S、P和O信息。S代表主体，O代表客体，表示为 variable_name:实体类型[`实体名`]，其中实体名是可选参数，但当问题中有特定的查询实体时，实体名称是必要填写的；P代表谓词，即关系或属性，表示为：变量名:边类型或属性类型。每个变量都会被赋予唯一的变量名，以便后续引用。注意，S、P和O不应在同一个表达式中重复出现。当需要引用先前定义好的变量时，变量名必须完全匹配，并且只需提供变量名，实体类型仅在首次引入时指定。
注意如果约束在P上，可以直接放在retrieval中。如果约束或者定语在实体S或者O上，则需要进行步骤拆解，通过多个Retrieval进行检索和过滤。
``之间的 `名称` 或者 `值` 以及实体类型和边的名称需要根据输入问题的语言类型进行填充，一般使用中文。其余部分使用中文
函数用法：Retrieval(s=s_alias:类型[`名称`], p=p_alias:边, o=o_alias:类型[`名称`], p.属性=`值`)

*函数名称：Math
描述：Math函数用于执行计算，包括集合运算、数值计算、排序和计数等。在Math函数中，content提供输入信息，这些信息可以是文本，也可以是引用的变量名。target是计算目标，通常是当前子问题。Math_alia是其计算结果的变量名，可在后续操作中引用。
除了``之间的内容使用中文，其他使用英文。
函数用法： Math(content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->math_alias

*函数名称：Deduce
描述：推理是指通过推导搜索或计算结果来回答问题的过程。op=judgement | entailment | rule | choice | multiChoice 分别表示是非题、蕴含推理（如推断语句）、片段提取、单选题和多选题。content 指问题、历史对话或搜索结果，可以是文本片段或引用变量名。target 是推理目标。
除了``之间的内容使用中文，其他使用英文。
函数用法：Deduce(op=judgement|entailment|extract|choice|multiChoice, content=[`XXX` or `o_alias/s_alias`], target=`XXX`)->deduce_alias

*函数名称：Output
描述：直接输出 A、B 等作为答案，其中 A 和 B 是引用先前检索或计算结果的变量名。
函数用法：Output(A,B,...)

#请根据上述函数定义，将用户问题分解为一个或多个逻辑步骤，输出每一步的执行计划及相应的动作。请注意以下几点：
1. 问题中的每个约束条件都必须使用。使用 Retrieval 时，如果约束在P上，可以直接放在retrieval中。如果约束或者定语在实体S或者O上，则需要进行步骤拆解，通过多个Retrieval进行检索和过滤。
2. 确保问题进行合理的拆解，进行函数调用时，语义需要和拆解的step一致。如果进行多个retrieval，一般需要后面使用 Deduce 函数进行推理（entailment），判定（judgement），选择（choice）或者使用 Math 函数进行计算。
3. 拆解的最后一个步骤，需要使用 Output函数，进行结果的输出。
4. 请确保拆解成后，能够解决原始问题.
5. 每一个拆解步骤包含 step与Action:
    -- Step:确指出问题的逻辑思维过程，并使用 #1 引用步骤1的解决结果，#2 引用步骤2的解决结果，依此类推。请使用中文。
    -- Action: 明确指出您选择的函数及其参数。

Question:
    $question
"""
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

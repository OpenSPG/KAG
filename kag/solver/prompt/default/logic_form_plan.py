import logging
import re
from string import Template
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)

from kag.common.base.prompt_op import PromptOp


class LogicFormPlanPrompt(PromptOp):
    instruct_zh = """"instruction": "你是一个KGQA专家，请根据以下图谱schema和function、function_description，理解最后query的问题，查询意图拆解成多个查询步骤，一步一步地实现查询逻辑",
    "function_description": "functionName为算子名;基本格式为 functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
    "function": [
      {
          "functionName": "get_spo",
          "function_declaration": "get_spo(s=s_alias:entity_type[entity_name], p=p_alias:edge_type, o=o_alias:entity_type[entity_name], p.edge_type=value)",
          "description": "查找spo信息，s代表主体，o代表客体，表示为变量名:实体类型[实体名称]，实体名称作为可选参数，当有明确的查询实体时需要给出；p代表谓词，即关系或属性，表示为变量名:边类型或属性类型；这里为每个变量都分配一个变量名，作为后续提及时的指代；注意，s、p、o不能在同一表达式中反复多次出现；当变量为前文指代的变量名是，变量名必须和指代的变量名一致，且只需给出变量名，实体类型仅在首次引入时给定"
      },
      {
          "functionName": "count",
          "function_declaration": "count_alias=count(alias)",
          "description": "统计节点个数，参数为指定待统计的节点集合，只能是get_spo中出现的变量名；count_alias作为变量名表示计算结果，只能是int类型，变量名可作为下文的指代"
      },
      {
          "functionName": "sum",
          "function_declaration": "sum(alias, num1, num2, ...)->sum_alias",
          "description": "数据求和，参数为指定待求和的集合，可以是数字也可以是前文中出现的变量名，其内容只能是数值类型；sum_alias作为变量名表示计算结果，只能是数值类型，变量名可作为下文的指代"
      },
      {
          "functionName": "sort",
          "function_declaration": "sort(set=alias, orderby=o_alias or count_alias or sum_alias, direction=min or max, limit=N)",
          "description": "对节点集合排序，set指定待排序的节点集合，只能是get_spo中出现的变量名；orderby指定排序的依据，为节点的关系或属性名称，若是前文提及过的，则用别名指代；direction指定排序的方向，只能是min(正序)或max(倒序)排列；limit为输出个数限制，为int类型；可作为最后的输出结果"
      },
      {
          "functionName": "get",
          "function_decl:aration": "get(alias)",
          "description": "返回指定的别名代表的信息，可以是实体、关系路径或get_spo中获取到的属性值；可作为最后的输出结果"
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

    template_zh = f"""
{{
    {instruct_zh}
    {default_case_zh}
    "output_format": "only output `Step`, `Action` and `Output` content",
    "query": "$question"
}}   
    """

    instruct_en = """    "instruction": "You are a KGQA expert. Given the following knowledge graph schema and the function and function description, understand the final query. Break down the query intent into multiple query steps and implement the query logic step by step.",
    "function_description": "functionName is operator name;the function format is functionName(arg_name1=arg_value1,[args_name2=arg_value2, args_name3=arg_value3]),括号中为参数，被[]包含的参数为可选参数，未被[]包含的为必选参数",
    "function": [
      {
          "functionName": "get_spo",
          "function_declaration": "get_spo(s=s_alias:entity_type[entity_name], p=p_alias:edge_type, o=o_alias:entity_type[entity_name])",
          "description": "Find SPO information. 's' represents the subject, 'o' represents the object, and they are denoted as variable_name:entity_type[entity_name]. The entity name is an optional parameter and should be provided when there is a specific entity to query. 'p' represents the predicate, which can be a relationship or attribute, denoted as variable_name:edge_type_or_attribute_type. Each variable is assigned a unique variable name, which is used for reference in subsequent mentions. Note that 's', 'p', and 'o' should not appear repeatedly within the same expression; only one set of SPO should be queried at a time. When a variable is a reference to a previously mentioned variable name, the variable name must match the previously mentioned variable name, and only the variable name needs to be provided; the entity type is only given when it is first introduced."
      },
      {
          "functionName": "count",
          "function_declaration": "count(alias)->count_alias",
          "description": "Count the number of nodes. The parameter should be a specified set of nodes to count, and it can only be variable names that appear in the get_spo query. The variable name 'count_alias' represents the counting result, which must be of int type, and this variable name can be used for reference in subsequent mentions."
      },
      {
          "functionName": "sum",
          "function_declaration": "sum(alias, num1, num2, ...)->sum_alias",
          "description": "Calculate the sum of data. The parameter should be a specified set to sum, which can be either numbers or variable names mentioned earlier, and its content must be of numeric type. The variable name 'sum_alias' represents the result of the calculation, which must be of numeric type, and this variable name can be used for reference in subsequent mentions."      },
      {
          "functionName": "sort",
          "function_declaration": "sort(set=alias, orderby=o_alias or count_alias or sum_alias, direction=min or max, limit=N)",
          "description": "Sort a set of nodes. The 'set' parameter specifies the set of nodes to be sorted and can only be variable names that appear in the get_spo query. The 'orderby' parameter specifies the basis for sorting, which can be the relationship or attribute name of the nodes. If it has been mentioned earlier, an alias should be used. The 'direction' parameter specifies the sorting order, which can only be 'min' (ascending) or 'max' (descending). The 'limit' parameter specifies the limit on the number of output results and must be of int type. The sorted result can be used as the final output."      },
      {
          "functionName": "compare",
          "function_declaration": "compare(set=[alias1, alias2, ...], op=min|max)",
          "description": "Compare nodes or numeric values. The 'set' parameter specifies the set of nodes or values to be compared, which can be variable names that appear in the get_spo query or constants. The 'op' parameter specifies the comparison operation: 'min' to find the smallest and 'max' to find the largest."
      },
      {
          "functionName": "get",
          "function_decl:aration": "get(alias)",
          "description": "Return the information represented by a specified alias. This can be an entity, a relationship path, or an attribute value obtained in the get_spo query. It can be used as the final output result."
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
    template_en = f"""
{{
    {instruct_en}
    {default_case_en}
    "output_format": "output a string, don't warp anything, multiply line, each line only start with Step/Action/Output, don't output other information",
    "query": "$question"
}}
    """

#     template_en = """
# You are a expert at Knowledge Graph based QA system. Please analyze the given problem and break it down into several Solve Steps so that one can answer the question by executing these Solve Steps in a knowledge base. And then express your Solve Steps with the query language we defined below:
# The format of our query language is: QueryFunction(arg1_name=arg1_value, arg2_name=arg2_value, ...)->output_name, The valid QueryFunction are defined as follow:
#
# QueryFunction: get_spo,
# function_arguments: get_spo(s=s_alias:entity_type[entity_name],p=p_alias:edge_type,o=o_alias:entity_type[entity_name]),
# description: Find SPO(Subject, Predicate, Object) triple information. Each variable function is assigned with a unique alias (s_alias, p_alias and o_alias), it is used for re-reference in subsequent functions. The entity_type is the type of s, p or o, it is infered from the question and sub-question context. The first occurrence of a variable must give an entity_type. The entity_name is an optional parameter and should be provided when there is a specific entity to query.
#
# QueryFunction: count,
# function_arguments: count(alias)->count_alias,
# description: Count the number of vaiable value. The parameter should be a specified set of vaiable to count, and it can only be variable alias appeared in previous get_spo query. The 'count_alias' is the counting result, used for re-reference in subsequent functions.
#
# QueryFunction: sum,
# function_arguments: sum(alias,num1,num2, ...)->sum_alias,
# description: Calculate the sum of variables. The parameter should be a specified set to sum, which can be either variable alias from previoud function or numbers, its content must be of numeric type. The 'sum_alias' is the result of the calculation, used for re-reference in subsequent functions.
#
# QueryFunction: sort,
# function_arguments: sort(set=alias,orderby=o_alias or count_alias or sum_alias, direction=min or max),
# description: Sort a set of nodes. The 'set' parameter specifies the variables to be sorted. The 'orderby' specifies the values for sorting, which can be any variable alias mentioned in previoud functions. The 'direction' parameter specifies the sorting order, which can only be 'min' (ascending) or 'max' (descending).
#
# QueryFunction: compare,
# function_arguments: compare(set=[alias1,alias2, ...], op=min|max),
# description: Compare variable or numeric values. The 'set' parameter specifies the set of variables or numbers to be compared. The 'op' parameter specifies the comparison operation: 'min' to find the smallest and 'max' to find the largest.
#
# QueryFunction: get,
# function_arguments: get(alias),
# description: Return the information represented by a alias. It can be used as the final output result.
#
#
# Here ars some examples:
# query: Which sports team for which Cristiano Ronaldo played in 2011 was founded last?
# answer:
#     Step1: Which Sports Teams Cristiano Ronaldo Played for in 2011 ?
#     Step2: In which year were these teams established ?
#     Step3: Which team was founded last ?
#     Action1: get_spo(s=s1:Player[Cristiano Ronaldo],p=p1:PlayedForIn2011Year,o=o1:SportsTeam)
#     Action2: get_spo(s=o1,p=p2:FoundationYear,o=o2:Year)
#     Action3: sort(set=o1,orderby=o2,direction=max,limit=1)
#
# query: Who was the first president of the association which published Journal of Psychotherapy Integration?
# answer:
#     Step1:Which association that publishes the Journal of Psychotherapy Integration ?
#     Step2:Who was the first president of that specific association?
#     Action1:Journal(s=s1:Player[Psychotherapy Integration],p=p1:Publish,o=o1:Association)
#     Action2:get_spo(s=o1,p=p2:FirstPresident,o=o2:Person)
#
# query: When did the state where Pocahontas Mounds is located become part of the United States?
# answer:
#     Step1:Which State Where Pocahontas Mounds is Located ?
#     Step2:When did this state become a part of the United States ？
#     Action1:get_spo(s=s1:HistoricalSite[Pocahontas Mounds],p=p1:LocatedIn,o=o1:State)
#     Action2:get_spo(s=o1,p=p2:YearOfBecamingPartofTheUnitedStates,o=o2:Date)
#
# query: Which of the two tornado outbreaks killed the most people?
# answer:
#     Step1: Which is the first tornado outbreaks ?
#     Step2: Which is the second tornado outbreaks ?)
#     Step3: How many people died in the first tornado outbreak ?
#     Step4: How many people died in the second tornado outbreak ?
#     Step5: To compare the death toll between two tornado outbreaks to determine which one had more fatalities.
#     Action1: get_spo(s=s1:Event[Tornado Outbreak],p=p1:TheFirst,o=o1:Event)
#     Action2: get_spo(s=s2:Event[Tornado Outbreak],p=p2:TheSecond,o=o2:Event
#     Action3: get_spo(s=s1,p=p3:KilledPeopleNumber,o=o3:Number)
#     Action4: get_spo(s=s2,p=p4:KilledPeopleNumber,o=o4:Number)
#     Action5: compare(set=[o3,o4],op=max)
#
# Now, the question query is:
# "$question"
# please first give Solve Steps and then express it with query language we defined above, don't warp anything. Answer with multiply line, each line only start with Step:/Action:/Output:, don't output other information.
#     """.strip()

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
            sub_queries = []
            logic_forms = []
            current_sub_query = ''
            for line in _output_string.split('\n'):
                if line.startswith('Step') or line.startswith('step'):
                    sub_query_regex = re.search(r'[Ss]tep\d?:(.*)', line)
                    if sub_query_regex is not None:
                        sub_queries.append(sub_query_regex.group(1))
                        current_sub_query = sub_query_regex.group(1)
                elif line.startswith('Output') or line.startswith('output'):
                    sub_queries.append("output")
                elif line.startswith('Action') or line.startswith('action'):
                    logic_form_regex = re.search(r'[Aa]ction\d?:(.*)', line)
                    if logic_form_regex:
                        logic_forms.append(logic_form_regex.group(1))
                        if len(logic_forms) - len(sub_queries) == 1:
                            sub_queries.append(current_sub_query)
            return sub_queries, logic_forms
        except Exception as e:
            logger.warning(f"{response} parse logic form faied {e}", exc_info=True)
            return [], []

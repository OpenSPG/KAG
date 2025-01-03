import logging
import re
from string import Template
from typing import List

logger = logging.getLogger(__name__)

from kag.interface import PromptABC


@PromptABC.register("riskmining_lf_plan")
class LogicFormPlanPrompt(PromptABC):
    instruct_zh = """"instruction": "",
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
            "Action": "张*三是一个赌博App的开发者吗?",
            "answer": "Step1:查询是否张*三的分类\nAction1:get_spo(s=s1:自然人[张*三], p=p1:属于, o=o1:风险用户)\nOutput:输出o1\nAction2:get(o1)"
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

    instruct_en = """    "instruction": "",
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
    default_case_en = """"""
    template_en = f"""
{{
    {instruct_en}
    {default_case_en}
    "output_format": "Only output words in answer, for examples: `Step`, `Action` content",
    "query": "$question"
}}   
    """

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

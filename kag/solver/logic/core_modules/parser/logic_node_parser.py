import logging
import re

from kag.solver.logic.core_modules.common.base_model import SPOBase, SPOEntity, SPORelation, Identifer, \
    TypeInfo, LogicNode
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils

logger = logging.getLogger(__name__)\


# get_spg(s, p, o)
class GetSPONode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.s: SPOBase = args.get('s', None)
        self.p: SPOBase = args.get('p', None)
        self.o: SPOBase = args.get('o', None)
        self.sub_query = args.get("sub_query", None)
        self.query = args.get("query", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.s = args.get('s', self.s)
        self.p = args.get('p', self.p)
        self.o = args.get('o', self.o)
        self.sub_query = args.get('sub_query', self.sub_query)

    @staticmethod
    def parse_node(input_str):
        equality_list = re.findall(r'([\w.]+=[^=]+)(,|，|$)', input_str)
        if len(equality_list) < 3:
            raise RuntimeError(f"parse {input_str} error not found s,p,o")
        spo_params = [e[0] for e in equality_list[:3]]
        get_spo_node = GetSPONode.parse_node_spo(spo_params)
        if len(equality_list) > 3:
            value_params = [e[0] for e in equality_list[3:]]
            GetSPONode.parse_node_value(get_spo_node, value_params)
        return get_spo_node

    @staticmethod
    def parse_node_spo(spo_params):
        s = None
        p = None
        o = None
        for spo_param in spo_params:
            key, param = spo_param.split('=')
            if key == "s":
                s = SPOEntity.parse_logic_form(param)
            elif key == "o":
                o = SPOEntity.parse_logic_form(param)
            elif key == "p":
                p = SPORelation.parse_logic_form(param)
        if s is None:
            raise RuntimeError(f"parse {str(spo_params)} error not found s")
        if p is None:
            raise RuntimeError(f"parse {str(spo_params)} error not found p")
        if o is None:
            raise RuntimeError(f"parse {str(spo_params)} error not found o")
        return GetSPONode("get_spo", {
            "s": s,
            "p": p,
            "o": o
        })

    @staticmethod
    def parse_node_value(get_spo_node_op, value_params):
        for value_param in value_params:
            # a.value=123,b.brand=345
            value_pair = re.findall(r'(?:[,\s]*(\w+)\.(\w+)=([^,，]+))', value_param)
            for key, property, value in value_pair:
                node = None
                if key == "s":
                    node = get_spo_node_op.s
                elif key == "p":
                    node = get_spo_node_op.p
                elif key == "o":
                    node = get_spo_node_op.o
                node.value_list.append([str(property), value])


def binary_expr_parse(input_str):
    pattern = re.compile(r'(\w+)=((?:(?!\w+=).)*)')
    matches = pattern.finditer(input_str)
    left_expr = None
    right_expr = None
    op = None
    for match in matches:
        key = match.group(1).strip()
        value = match.group(2).strip().rstrip(',')
        value = value.rstrip('，')
        if key == "left_expr":
            if "," in value:
                left_expr_list = list(set([Identifer(v) for v in value.split(",")]))
            elif "，" in value:
                left_expr_list = list(set([Identifer(v) for v in value.split("，")]))
            else:
                left_expr_list = [Identifer(value)]
            if len(left_expr_list) == 1:
                left_expr = left_expr_list[0]
            else:
                left_expr = left_expr_list
        elif key == "right_expr":
            if value != '':
                right_expr = value
        elif key == "op":
            op = value
    if left_expr is None:
        raise RuntimeError(f"parse {input_str} error not found left_expr")

    if op is None:
        raise RuntimeError(f"parse {input_str} error not found op")
    return {
        "left_expr": left_expr,
        "right_expr": right_expr,
        "op": op
    }


# filter(left_expr=alias, right_expr=other_alias or const_data, op=equal|lt|gt|le|ge|in|contains|and|or|not)
class FilterNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.left_expr = args.get('left_expr', None)
        self.right_expr = args.get('right_expr', None)
        self.op = args.get('op', None)
        self.OP = 'equal|lt|gt|le|ge|in|contains|and|or|not'.split('|')

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.left_expr = args.get('left_expr', self.left_expr)
        self.right_expr = args.get('right_expr', self.right_expr)
        self.op = args.get('op', self.op)

    @staticmethod
    def parse_node(input_str):
        args = binary_expr_parse(input_str)
        return FilterNode("filter", args)


# count(alias)->count_alias
class CountNode(LogicNode):
    def __init__(self, operator, args):
        super(CountNode, self).__init__(operator, args)
        self.alias_name = args.get("alias_name", None)
        self.set = args.get("set", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @staticmethod
    def parse_node(input_str, output_name):
        args = {'alias_name': output_name, 'set': input_str}
        return CountNode("count", args)


# sum(alias)->sum_alias
class SumNode(LogicNode):
    def __init__(self, operator, args):
        super(SumNode, self).__init__(operator, args)
        self.alias_name = args.get("alias_name", None)
        self.set = args.get("set", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @staticmethod
    def parse_node(input_str):
        # count_alias=count(alias)
        match = re.match(r'(\w+)[\(\（](.*)[\)\）](->)?(.*)?', input_str)
        if not match:
            raise RuntimeError(f"parse logic form error {input_str}")
        # print('match:',match.groups())
        if len(match.groups()) == 4:
            operator, params, _, alias_name = match.groups()
        else:
            operator, params = match.groups()
            alias_name = 'sum1'
        params = params.replace('，', ',').split(',')
        args = {'alias_name': alias_name, 'set': params}
        return SumNode("sum", args)


class SortNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.alias_name = args.get("alias_name", None)
        self.set = args.get("set", None)
        self.orderby = args.get("orderby", None)
        self.direction = args.get("direction", None)
        self.limit = args.get("limit", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def __str__(self):
        return f"sort：{self.set} {self.orderby} {self.direction} top{self.limit}"

    def get_set(self):
        if isinstance(self.set, list):
            return set(self.set)
        return {self.set}

    @staticmethod
    def parse_node(input_str):
        equality_list = re.findall(r'([\w.]+=[^=]+)(,|，|$)', input_str)
        if len(equality_list) < 4:
            raise RuntimeError(f"parse {input_str} error not found set,orderby,direction,limit")
        params = [e[0] for e in equality_list[:4]]
        params_dict = {}
        for param in params:
            key, value = param.split('=')
            params_dict[key] = value
        return SortNode("sort", params_dict)


class CompareNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.alias_name = args.get("alias_name", None)
        self.set = args.get("set", None)
        self.op = args.get("op", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def __str__(self):
        return f"compare：{self.set} {self.op} "

    def get_set(self):
        if isinstance(self.set, list):
            return set(self.set)
        return {self.set}

    @staticmethod
    def parse_node(input_str):
        equality_list = re.findall(r'([\w.]+=[^=]+)(,|，|$)', input_str)
        if len(equality_list) < 2:
            raise RuntimeError(f"parse {input_str} error not found set,orderby,direction,limit")
        params = [e[0] for e in equality_list[:2]]
        params_dict = {}
        for param in params:
            key, value = param.split('=')
            if key == 'set':
                value = value.strip().replace('，', ',').replace(' ', '').strip('[').strip(']').split(',')
            params_dict[key] = value
        return CompareNode("compare", params_dict)


class DeduceNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.deduce_ops = args.get("deduce_ops", [])

    def __str__(self):
        return f"deduce(op={','.join(self.deduce_ops)})"

    @staticmethod
    def parse_node(input_str):
        ops = input_str.replace("op=", "")
        input_ops = ops.split(",")
        return DeduceNode("deduce", {
            "deduce_ops": input_ops
        })


# verity(left_expr=alias, right_expr=other_alias or const_data, op=equal|gt|lt|ge|le|in|contains)
class VerifyNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.left_expr = args.get('left_expr', None)
        self.right_expr = args.get('right_expr', None)
        self.op = args.get('op', None)
        self.OP = {'等于': 'equal', '大于': 'gt', '小于': 'lt', '大于等于': 'ge', '小于等于': 'le', '属于': 'in', '包含': 'contains'}

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def __str__(self):
        return f"条件判定：{self.left_expr} {self.op} {self.right_expr}"

    def get_left_expr_set(self):
        if isinstance(self.left_expr, list):
            return set(self.left_expr)
        return {self.left_expr}

    def get_left_expr_name(self):
        if isinstance(self.left_expr, list):
            return ",".join([str(e) for e in self.left_expr])
        return self.left_expr

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.left_expr = args.get('left_expr', self.left_expr)
        self.right_expr = args.get('right_expr', self.right_expr)
        self.op = args.get('op', self.op)
        if self.op in self.OP.values():
            self.op = self.OP[self.op]

    @staticmethod
    def parse_node(input_str):
        if "verify" in input_str:
            match = re.match(r'(\w+)[\(\（](.*)[\)\）](->)?(.*)?', input_str)
            if not match:
                raise RuntimeError(f"parse logic form error {input_str}")
            # print('match:',match.groups())
            if len(match.groups()) == 4:
                operator, input_str, _, output_name = match.groups()
            else:
                operator, input_str = match.groups()
        args = binary_expr_parse(input_str)
        return VerifyNode("verify", args)


class ExtractorNode(LogicNode):
    def __int__(self, operator, args):
        super(ExtractorNode, self).__init__(operator, args)
        self.alias_set = args.get("alias_set")

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @staticmethod
    def parse_node(input_str):
        params = set(input_str.split(","))
        alias_set = [Identifer(p) for p in params]
        ex_node = ExtractorNode("extractor", {
            "alias_set": alias_set
        })
        ex_node.alias_set = alias_set
        return ex_node


# get(alias_name)
class GetNode(LogicNode):
    def __init__(self, operator, args):
        super(GetNode, self).__init__(operator, args)
        self.alias_name = args.get("alias_name")
        self.alias_name_set: list = args.get("alias_name_set")
        self.s = args.get("s", None)
        self.s_alias_map: dict = args.get("s_alias_map", None)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    @staticmethod
    def parse_node(input_str):
        input_args = input_str.split(",")
        return GetNode("get", {
            "alias_name": Identifer(input_args[0]),
            "alias_name_set": [Identifer(e) for e in input_args]
        })


# search_s()
class SearchNode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.s = SPOEntity(None, None, args['type'], None, args['alias'], False)
        self.s.value_list = args['conditions']

    @staticmethod
    def parse_node(input_str):
        pattern = re.compile(r'[,\s]*s=(\w+):([^,\s]+),(.*)')
        matches = pattern.match(input_str)
        args = dict()
        args["alias"] = matches.group(1)
        args["type"] = matches.group(2)
        if len(matches.groups()) > 2:
            search_condition = dict()
            s_condition = matches.group(3)

            condition_pattern = re.compile(r'(?:[,\s]*(\w+)\.(\w+)=([^,，]+))')
            condition_list = condition_pattern.findall(s_condition)
            for condition in condition_list:
                s_property = condition[1]
                s_value = condition[2]
                s_value = SearchNode.check_value_is_reference(s_value)
                search_condition[s_property] = s_value
            args['conditions'] = search_condition

        return SearchNode('search_s', args)

    @staticmethod
    def check_value_is_reference(value_str):
        if '.' in value_str:
            return value_str.split('.')
        return value_str


class ParseLogicForm:
    def __init__(self, schema: SchemaUtils, schema_retrieval):
        self.schema = schema
        self.schema_retrieval = schema_retrieval

    def std_parse_kg_node(self, entity: SPOBase, parsed_entity_set):
        alias_name = entity.alias_name
        if alias_name in parsed_entity_set.keys():
            exist_node = parsed_entity_set[alias_name]
            exist_node.value_list.extend(entity.value_list)
            return parsed_entity_set[alias_name]

        zh_types = entity.get_entity_type_zh_set()
        std_entity_type_set = []
        if isinstance(entity, SPOEntity):
            for entity_type in zh_types:
                type_info = self.get_node_type_info(entity_type)
                if type_info.entity_type is None and self.schema is not None:
                    entity.is_attribute = True
                std_entity_type_set.append(type_info)
        elif isinstance(entity, SPORelation):
            s_type_zh = entity.s.get_entity_first_type_or_en()
            o_type_zh = entity.o.get_entity_first_type_or_en()
            s_type_en = entity.s.get_entity_first_type_or_zh()
            o_type_en = entity.o.get_entity_first_type_or_zh()
            for entity_type in zh_types:
                type_info = TypeInfo()
                type_info.entity_type_zh = entity_type
                if self.schema is not None:
                    if o_type_zh == "Entity":
                        sp_index = (s_type_zh, entity_type)
                        if sp_index in self.schema.sp_o:
                            o_candis_set = self.schema.sp_o[sp_index]
                            for candis in o_candis_set:
                                spo_zh = f"{s_type_zh}_{entity_type}_{candis}"
                                type_info.entity_type = self.schema.get_spo_with_p(self.schema.spo_zh_en[spo_zh])
                                break

                    if not type_info.entity_type and s_type_zh == "Entity":
                        op_index = (o_type_zh, entity_type)
                        if op_index in self.schema.op_s:
                            s_candis_set = self.schema.op_s[op_index]
                            for candis in s_candis_set:
                                spo_zh = f"{candis}_{entity_type}_{o_type_zh}"
                                type_info.entity_type = self.schema.get_spo_with_p(self.schema.spo_zh_en[spo_zh])
                                break

                    if not type_info.entity_type and o_type_zh != "Entity" and s_type_zh != "Entity":
                        so_index = (s_type_zh, o_type_zh)
                        if so_index not in self.schema.so_p:
                            so_index = (o_type_zh, s_type_zh)
                        candis_set = self.schema.so_p[so_index]
                        for p_candis in candis_set:
                            if p_candis == entity_type:
                                spo_zh = f"{s_type_zh}_{p_candis}_{o_type_zh}"
                                type_info.entity_type = self.schema.get_spo_with_p(self.schema.spo_zh_en[spo_zh])

                    if not type_info.entity_type:
                        # maybe a property
                        s_attr_zh_en = self.schema.attr_zh_en_by_label.get(s_type_en, [])
                        if s_attr_zh_en and entity_type in s_attr_zh_en:
                            type_info.entity_type = s_attr_zh_en[entity_type]
                        if not type_info.entity_type:
                            o_attr_zh_en = self.schema.attr_zh_en_by_label.get(o_type_en, [])
                            if o_attr_zh_en and entity_type in o_attr_zh_en:
                                type_info.entity_type = o_attr_zh_en[entity_type]
                std_entity_type_set.append(type_info)

        entity.type_set = std_entity_type_set
        parsed_entity_set[alias_name] = entity

        return entity

    def std_parse_node(self, entity: SPOEntity, parsed_entity_set):
        alias_name = entity.alias_name
        if alias_name in parsed_entity_set.keys():
            exist_node = parsed_entity_set[alias_name]
            exist_node.value_list.extend(entity.value_list)
            return parsed_entity_set[alias_name]

        zh_types = entity.get_entity_type_zh_set()
        std_entity_type_set = []
        for entity_type in zh_types:
            type_info = self.get_node_type_info(entity_type)
            if type_info.entity_type is None and self.schema is not None:
                entity.is_attribute = True
            std_entity_type_set.append(type_info)
        entity.type_set = std_entity_type_set
        parsed_entity_set[alias_name] = entity
        return entity

    def std_parse_edge(self, edge: SPORelation, parsed_entity_set):
        alias_name = edge.alias_name
        if alias_name in parsed_entity_set.keys():
            return parsed_entity_set[alias_name]
        zh_types = edge.get_entity_type_zh_set()
        std_edge_type_set = []
        for entity_type in zh_types:
            type_info = self.get_edge_type_info(entity_type)
            if type_info.entity_type is None and self.schema is not None:
                edge.is_attribute = True
            std_edge_type_set.append(type_info)
        edge.type_set = std_edge_type_set

        parsed_entity_set[alias_name] = edge
        return edge

    def parse_logic_form(self, input_str: str, parsed_entity_set={}, sub_query=None, query=None):
        match = re.match(r'(\w+)[\(\（](.*)[\)\）](->)?(.*)?', input_str.strip())
        if not match:
            raise RuntimeError(f"parse logic form error {input_str}")
        if len(match.groups()) == 4:
            operator, args_str, _, output_name = match.groups()
        else:
            operator, args_str = match.groups()
            output_name = None
        low_operator = operator.lower()
        if low_operator == "get":
            node: GetNode = GetNode.parse_node(args_str)
            if node.alias_name in parsed_entity_set.keys():
                s = parsed_entity_set[node.alias_name]
                node.s = s
        elif low_operator in ["get_spo", "retrieval"]:
            node: GetSPONode = GetSPONode.parse_node(args_str)
            s_node = self.std_parse_kg_node(node.s, parsed_entity_set)
            o_node = self.std_parse_kg_node(node.o, parsed_entity_set)
            node.p.s = s_node
            node.p.o = o_node
            p_node = self.std_parse_kg_node(node.p, parsed_entity_set)
            node.to_std({
                "s": s_node,
                "p": p_node,
                "o": o_node,
                "sub_query": sub_query,
            })
        elif low_operator in ["filter"]:
            node: FilterNode = FilterNode.parse_node(args_str)
        elif low_operator in ["deduce"]:
            node: DeduceNode = DeduceNode.parse_node(args_str)
        elif low_operator in ["verify"]:
            node: VerifyNode = VerifyNode.parse_node(args_str)
        elif low_operator in ["count"]:
            node: CountNode = CountNode.parse_node(args_str, output_name)
        elif low_operator in ["sum"]:
            node: SumNode = SumNode.parse_node(args_str)
        elif low_operator in ["sort"]:
            node: SortNode = SortNode.parse_node(args_str)
        elif low_operator in ["compare"]:
            node: SortNode = CompareNode.parse_node(args_str)
        elif low_operator in ["extractor"]:
            node: ExtractorNode = ExtractorNode.parse_node(args_str)
        elif low_operator in ['search_s']:
            node: SearchNode = SearchNode.parse_node(args_str)
            self.std_parse_node(node.s, parsed_entity_set)
        else:
            raise NotImplementedError(f"not impl {input_str}")

        node.to_std({
            "sub_query": sub_query
        })

        return node

    def parse_logic_form_set(self, input_str_set: list, sub_querys: list, question: str):
        parsed_cached_map = {}
        parsed_node = []
        for i, input_str in enumerate(input_str_set):
            if sub_querys and i < len(sub_querys):
                sub_query = sub_querys[i]
            else:
                sub_query = None
            try:
                logic_node = self.parse_logic_form(input_str, parsed_cached_map, sub_query=sub_query, query=question)
                parsed_node.append(logic_node)
            except Exception as e:
                logger.warning(f"parse node {input_str} error", exc_info=True)
        return parsed_node

    def std_node_type_name(self, type_name):
        if self.schema_retrieval is None:
            return type_name
        search_entity_labels = self.schema_retrieval.retrieval_entity(SPOEntity(entity_name=type_name))
        if len(search_entity_labels) > 0:
            return search_entity_labels[0].name
        return type_name

    def get_edge_type_en_by_name(self, type_name):
        if self.schema is None:
            return None
        if type_name in self.schema.edge_en_zh.keys():
            return type_name
        return self.schema.edge_zh_en.get(type_name, None)

    def get_node_type_en_by_name(self, type_name):
        if self.schema is None:
            return type_name
        if type_name in self.schema.node_en_zh.keys():
            return type_name
        return self.schema.node_zh_en.get(type_name, None)

    def get_node_type_zh_by_name(self, type_name):
        if self.schema is None:
            return type_name
        if type_name in self.schema.node_zh_en.keys():
            return type_name
        return self.schema.node_en_zh.get(type_name, None)

    def get_node_type_info(self, type_name):
        zh = self.get_node_type_zh_by_name(type_name)
        en = self.get_node_type_en_by_name(type_name)
        if zh == en:
            en = self.std_node_type_name(type_name)
            zh = en
        type_info = TypeInfo()
        type_info.entity_type = en
        type_info.entity_type_zh = zh
        if type_info.entity_type_zh is None:
            type_info.entity_type_zh = type_name
        return type_info

    def get_edge_type_info(self, type_name):
        # Edge is not standardized currently
        type_info = TypeInfo()
        type_info.entity_type = self.get_edge_type_en_by_name(type_name)
        type_info.entity_type_zh = type_name
        return type_info

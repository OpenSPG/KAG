import logging
from kag.solver.logic.common.base_model import SPOBase, SPOEntity, SPORelation, Identifer

from kag.solver.logic.common.schema import Schema
from kag.solver.logic.parser.logic_node_parser import GetSPONode, GetNode, \
    SearchNode, ExtractorNode, VerifyNode, FilterNode

logger = logging.getLogger()


class DslGenerator:
    def __init__(self, schema: Schema, filter_with_name=False):
        self.alias_index = 0
        self.start_alias = []
        self.graphs = []
        self.rules = []
        self.action = []
        self.alias_set_map = {}
        self.id_set_to_alias_map = {}
        self.start_id_info = None
        self.schema = schema
        self.alias_in_graph = []
        self.entity_attr_alias_name = {}
        self.alias_dependence_map = {}
        self.final_alias_set = []
        self.has_start_with_id = []
        self.p_alias = []
        self.filter_with_name = filter_with_name

    def generate_start_info(self, e: SPOEntity):
        start_infos = e.generate_start_infos(None)
        if len(start_infos) == 0:
            return None
        return start_infos[0]

    def generate_gql_edge_format(self, s: SPORelation):
        entity_types = s.get_type_with_gql_format()
        return f"{s.alias_name}{':' + entity_types if entity_types is not None else ''}"

    def generate_gql_node_by_entity(self, s: SPOEntity):
        s_type = s.get_type_with_gql_format()
        node_type = "" if s_type is None else s_type
        return f"{s.alias_name}:{node_type if '.' in node_type else node_type}"

    def std_alias_to_map(self, s: SPOBase):
        if s.alias_name not in self.alias_set_map.keys():
            self.alias_set_map[s.alias_name] = s

        if isinstance(s, SPOEntity):

            if s.entity_name is not None:
                self.has_start_with_id.append(s.alias_name)

            id_key = s.generate_id_key()
            if id_key is not None and id_key in self.id_set_to_alias_map.keys():
                return self.id_set_to_alias_map[id_key]

            if id_key is not None:
                self.id_set_to_alias_map[id_key] = s
                self.rules.append(f"R{len(self.rules)}: {s.alias_name}.id in [{id_key}]")
                self.start_alias.append(s.alias_name)
                self.has_start_with_id.append(s.alias_name)
        return s

    def add_alias_dependence(self, alias, dep_alias):
        if alias in self.alias_dependence_map.keys():
            self.alias_dependence_map[alias] = list(set(self.alias_dependence_map[alias] + [dep_alias]))
        else:
            self.alias_dependence_map[alias] = [dep_alias]

    def parse_get_spo(self, info: GetSPONode):
        s = self.std_alias_to_map(info.s)
        p = self.std_alias_to_map(info.p)
        o = self.std_alias_to_map(info.o)

        # TODO this is basic data type,like string\int\float\date, current all call attribute
        if o.is_attribute:
            rule_format = f"{o.alias_name} = {s.alias_name}.{p.get_type_with_gql_format()}"
            self.rules.append(rule_format)
            self.entity_attr_alias_name[o.alias_name] = s.alias_name
            self.add_alias_dependence(o.alias_name, s.alias_name)
            self.add_alias_dependence(o.alias_name, p.alias_name)
            self.add_alias_dependence(p.alias_name, s.alias_name)
            if s.alias_name not in self.alias_in_graph:
                gql_format = f"({self.generate_gql_node_by_entity(s)})"
                self.graphs.append(gql_format)
                self.alias_in_graph.append(s.alias_name)
            return
        self.add_alias_dependence(p.alias_name, o.alias_name)
        self.add_alias_dependence(p.alias_name, s.alias_name)
        if s.alias_name in self.has_start_with_id:
            self.add_alias_dependence(o.alias_name, s.alias_name)
            self.add_alias_dependence(o.alias_name, p.alias_name)
            self.has_start_with_id.append(o.alias_name)

        if o.alias_name in self.has_start_with_id:
            self.add_alias_dependence(s.alias_name, o.alias_name)
            self.add_alias_dependence(s.alias_name, p.alias_name)
            self.has_start_with_id.append(s.alias_name)

        gql_format = f"({self.generate_gql_node_by_entity(s)})-[{self.generate_gql_edge_format(p)}]-({self.generate_gql_node_by_entity(o)})"
        self.graphs.append(gql_format)
        self.graphs.append(f"({self.generate_gql_node_by_entity(s)})")
        self.graphs.append(f"({self.generate_gql_node_by_entity(o)})")
        self.alias_in_graph.append(s.alias_name)
        self.alias_in_graph.append(p.alias_name)
        self.alias_in_graph.append(o.alias_name)
        self.p_alias.append(p.alias_name)
        return

    def ret_value(self, expr):
        if expr in self.alias_set_map.keys():
            return expr
        return f'"{expr}"'

    def equal_op(self, left, right):
        if left not in self.alias_set_map.keys():
            return None
        left_alias_name = left
        if left_alias_name in self.entity_attr_alias_name.keys():
            left_alias_name = self.entity_attr_alias_name[left_alias_name]
        spo_base = self.alias_set_map[left_alias_name]
        if isinstance(spo_base, SPOEntity):
            if spo_base.generate_id_key() is not None and not isinstance(right, Identifer):
                return None

        left_alias_name = left
        if not self.alias_set_map[left_alias_name].is_attribute:
            left_alias_name = f"{left_alias_name}.name"

        if isinstance(right, Identifer):
            return f"R{len(self.rules)}: {left_alias_name} == {right.alias_name}"
        return f"R{len(self.rules)}: {left_alias_name} rlike '{right}'"

    def lt_op(self, left, right):
        return f"R{len(self.rules)}: {left.alias_name} > {self.ret_value(right.alias_name)}"

    def gt_op(self, left, right):
        return f"R{len(self.rules)}: {left.alias_name} < {self.ret_value(right.alias_name)}"

    def le_op(self, left, right):
        return f"R{len(self.rules)}: {left.alias_name} >= {self.ret_value(right.alias_name)}"

    def ge_op(self, left, right):
        return f"R{len(self.rules)}: {left.alias_name} <= {self.ret_value(right.alias_name)}"

    def in_op(self, left, right):
        return None

    def contains_op(self, left, right):
        return None

    def and_op(self, left, right):
        return None

    def or_op(self, left, right):
        return None

    def not_op(self, left, right):
        return None

    def parse_left_expr_list(self, left_expr_obj):
        if isinstance(left_expr_obj, Identifer):
            return [left_expr_obj]
        elif isinstance(left_expr_obj, list):
            return left_expr_obj
        else:
            return None

    def process_binary_expr(self, left_expr, right_expr):
        left_expr_list = self.parse_left_expr_list(left_expr)
        if left_expr_list is not None:
            self.final_alias_set = self.final_alias_set + left_expr_list
        if isinstance(right_expr, Identifer):
            self.final_alias_set.append(right_expr)

    def parse_extractor(self, f: ExtractorNode):
        self.final_alias_set = self.final_alias_set + list(f.alias_set)

    def parse_verify(self, f: VerifyNode):
        self.process_binary_expr(f.left_expr, f.right_expr)

    def parse_search_s(self, node: SearchNode):
        self.alias_set_map[node.s.alias_name] = node.s
        self.has_start_with_id.append(node.s.alias_name)
        value_map = node.s.value_map
        has_reference = False
        reference_key_set = set()
        for key in value_map.keys():
            value = value_map[key]
            if isinstance(value, list):
                has_reference = True
                reference_key_set.add(value[0])
        if has_reference:
            for reference_key in reference_key_set:
                self.add_alias_dependence(node.s.alias_name.alias_name, reference_key)

    def parse_filter(self, f: FilterNode):
        """
        op是算子,包括数值计算: [equal,lt,gt,le,ge]，分别表示等于、大于、小于、大于等于、小于等于，以及逻辑计算: [in,contains,and,or,not], 分别表达属于、包含、与、或、非
        :param f:
        :return:
        """
        op_map = {
            "equal": self.equal_op,
            "lt": self.lt_op,
            "gt": self.gt_op,
            "le": self.le_op,
            "ge": self.ge_op,
            "in": self.in_op,
            "contains": self.contains_op,
            "and": self.and_op,
            "or": self.or_op,
            "not": self.not_op
        }
        rule = op_map[f.op](f.left_expr, f.right_expr)
        if rule is not None:
            if not self.filter_alias_need(f):
                self.final_alias_set.append(f.left_expr)
            if isinstance(f.right_expr, Identifer):
                self.final_alias_set.append(f.right_expr)
            self.rules.append(rule)

    def parse_get(self, g: GetNode):
        for alias_name in g.alias_name_set:
            self.final_alias_set.append(alias_name)
            if alias_name in self.alias_set_map.keys() and not self.alias_set_map[alias_name].is_attribute:
                if alias_name in self.p_alias:
                    self.action.append(str(alias_name) + ".__label__")
                else:
                    self.action.append(str(alias_name) + ".name")
            else:
                self.action.append(str(alias_name))
        return g.alias_name

    def is_use_el_link(self, alias):
        if alias not in self.alias_set_map.keys():
            return False
        entity = self.alias_set_map[alias]
        if isinstance(entity, SPOEntity):
            if self.filter_with_name is True and \
                    (entity.entity_name is not None and entity.entity_name != ''):
                return True
            if entity.generate_id_key() is not None:
                return True
        return False

    def get_unused_alias(self):
        used_alias = []
        all_set = set(self.alias_set_map.keys())

        def get_all_used_alias(alias: str, all_alias_set: set):
            if alias not in self.alias_dependence_map.keys():
                return
            if self.is_use_el_link(alias):
                # enough to search ,break
                return
            for dep_alias in self.alias_dependence_map[alias]:
                if dep_alias in used_alias:
                    continue
                used_alias.append(dep_alias)
                get_all_used_alias(dep_alias, all_alias_set)

        # get unused alias
        for final_alias in self.final_alias_set:
            used_alias.append(final_alias)
            get_all_used_alias(final_alias, all_set)
        unused_alias_set = all_set.difference(set(used_alias))
        return unused_alias_set

    def filter_alias_need(self, n: FilterNode):
        if n.left_expr in self.alias_set_map.keys():
            left_alias_name = n.left_expr
            if left_alias_name in self.entity_attr_alias_name.keys():
                left_alias_name = self.entity_attr_alias_name[left_alias_name]
            if self.is_use_el_link(left_alias_name):
                return True
        return False

    def filter_alias_judge(self, n: FilterNode, unused_alias_set):
        if n.left_expr.alias_name in unused_alias_set:
            return True
        if self.filter_alias_need(n):
            return True
        if isinstance(n.right_expr, Identifer):
            if n.right_expr.alias_name in self.alias_set_map.keys():
                right_alias_name = n.right_expr.alias_name
                if right_alias_name in self.entity_attr_alias_name.keys():
                    right_alias_name = self.entity_attr_alias_name[right_alias_name]
                if right_alias_name in unused_alias_set:
                    return True
        return False

    def prune_nodes(self, nodes):
        for n in nodes:
            if n.operator == "get_spo":
                self.parse_get_spo(n)
            if n.operator == "get":
                self.parse_get(n)
            if n.operator == "filter":
                self.parse_filter(n)
            if n.operator == "verify":
                self.parse_verify(n)
            if n.operator == "extractor":
                self.parse_extractor(n)
            if n.operator == 'search_s':
                self.parse_search_s(n)
        if len(self.action) == 0:
            # not get,we will get all
            for alias in self.alias_set_map.keys():
                if alias not in self.alias_in_graph:
                    continue
                self.action.append(str(alias))
                self.final_alias_set.append(alias)
        unused_alias_set = self.get_unused_alias()
        if len(unused_alias_set) == 0:
            return nodes
        updated_nodes = []
        for n in nodes:
            if n.operator == "get_spo":
                if n.s.alias_name in self.alias_set_map.keys() and n.s.alias_name in unused_alias_set:
                    continue

                if n.p.alias_name in self.alias_set_map.keys() and n.p.alias_name in unused_alias_set:
                    continue

                if n.o.alias_name in self.alias_set_map.keys() and n.o.alias_name in unused_alias_set:
                    continue

                updated_nodes.append(n)
            if n.operator == "get":
                updated_nodes.append(n)
            if n.operator == "filter":
                if self.filter_alias_judge(n, unused_alias_set):
                    continue
                updated_nodes.append(n)
        return updated_nodes

    def simply_dsl(self):
        unused_alias_set = self.get_unused_alias()
        if len(unused_alias_set) == 0:
            return
        new_graph = []
        new_rule = []
        # rmv unused start id
        self.start_alias = list(set(self.start_alias).difference(unused_alias_set))
        for g in self.graphs:
            is_in = False
            for unused_alias in unused_alias_set:
                if unused_alias.alias_name in g:
                    is_in = True
                    break
            if not is_in:
                new_graph.append(g)
        for r in self.rules:
            is_in = False
            for unused_alias in unused_alias_set:
                if unused_alias.alias_name in r:
                    is_in = True
                    break
            if not is_in:
                new_rule.append(r)
        self.graphs = new_graph
        self.rules = new_rule

    def generate_start_info_final(self):
        if len(self.start_alias) > 0:
            self.start_id_info = self.generate_start_info(self.alias_set_map[self.start_alias[0]])

    def clean_graph_decl(self):
        edge_set = []
        node_set = []
        for g in self.graphs:
            if "]-" in g:
                edge_set.append(g)
            else:
                node_set.append(g)
        new_graphs = list(edge_set)
        for node_str in node_set:
            is_in = False
            for e in edge_set:
                if node_str in e:
                    is_in = True
                    break
            if not is_in:
                new_graphs.append(node_str)
        self.graphs = new_graphs

    def to_dsl(self, nodes):
        for n in nodes:
            if n.operator == "get_spo":
                self.parse_get_spo(n)
            if n.operator == "get":
                self.parse_get(n)
            if n.operator == "filter":
                self.parse_filter(n)
        if len(self.action) == 0:
            # not get,we will get all
            for alias in self.alias_set_map.keys():
                if alias not in self.alias_in_graph:
                    continue
                self.action.append(str(alias))
                self.final_alias_set.append(alias)
        self.simply_dsl()
        self.generate_start_info_final()
        self.clean_graph_decl()
        current_graph = set(self.graphs)
        graphs_str = '\n        '.join(current_graph)
        rules_str = '\n        '.join(self.rules)
        # output
        return (f"""
GraphStructure {{
        {graphs_str}
}}
Rule {{
        {rules_str}
}}
Action {{
    get({','.join(self.action)})
}}
        """, self.start_id_info)

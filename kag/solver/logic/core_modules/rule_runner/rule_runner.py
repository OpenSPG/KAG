import logging
import time
from enum import Enum

from kag.solver.logic.core_modules.common.base_model import Identifer
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData, RelationData
from kag.solver.logic.core_modules.parser.logic_node_parser import FilterNode, ExtractorNode, \
    VerifyNode


class MatchRes(Enum):
    MATCH = 1
    UN_MATCH = 2
    UN_RELATED = 3
    RELATED = 4


class MatchInfo:
    def __init__(self, res: MatchRes, desc: str = ''):
        self.res = res
        self.desc = desc

    def trans_match_res_to_str(self):
        if self.res == MatchRes.RELATED:
            return "相关"
        elif self.res == MatchRes.MATCH:
            return "满足"
        elif self.res == MatchRes.UN_MATCH:
            return "不满足"
        else:
            return "不相关"

def trans_str_res_to_match(res: str):
    if res is None or res == '' or "无相关信息" in res \
            or "不相关" in res:
        return MatchRes.UN_RELATED
    return MatchRes.RELATED


class RuleRunner:
    def __init__(self):
        self.op_map = {
            "equal": self.run_equal,
            "lt": self.run_lt,
            "gt": self.run_gt,
            "le": self.run_le,
            "ge": self.run_ge,
            "in": self.run_in,
            "contains": self.run_contains,
            "and": self.run_and,
            "or": self.run_or,
            "not": self.run_not,
            "match": self.run_match,
            "exist": self.run_exists,
            "necessary": self.run_necessary,
            "collect_in": self.run_collect_in,
            "collect_contains": self.run_collect_contains
        }

    def run_rule(self, op_name: str, left_value, right_value):
        pass

    def run_equal(self, left_value, right_value):
        pass

    def run_gt(self, left_value, right_value):
        pass

    def run_lt(self, left_value, right_value):
        pass

    def run_ge(self, left_value, right_value):
        pass

    def run_le(self, left_value, right_value):
        pass

    def run_in(self, left_value, right_value):
        pass

    def run_contains(self, left_value, right_value):
        pass

    def run_and(self, left_value, right_value):
        pass

    def run_or(self, left_value, right_value):
        pass

    def run_not(self, left_value):
        pass

    def run_match(self, left_value, right_value):
        pass

    def run_exists(self, left_value):
        pass

    def run_necessary(self, left_value):
        pass

    def run_collect_in(self, left_value, right_value):
        pass

    def run_collect_contains(self, left_value, right_value):
        pass


class StrRuleRunner(RuleRunner):
    def __init__(self):
        super().__init__()

    def run_equal(self, left_value, right_value):
        return left_value == right_value

    def run_gt(self, left_value, right_value):
        return str(left_value) > str(right_value)

    def run_lt(self, left_value, right_value):
        return str(left_value) < str(right_value)

    def run_ge(self, left_value, right_value):
        return str(left_value) >= str(right_value)

    def run_le(self, left_value, right_value):
        return str(left_value) <= str(right_value)

    def run_in(self, left_value, right_value):
        return left_value in right_value

    def run_contains(self, left_value, right_value):
        return right_value in left_value

    def run_and(self, left_value, right_value):
        return left_value and right_value

    def run_or(self, left_value, right_value):
        return left_value or right_value

    def run_not(self, left_value):
        return not left_value

    def run_match(self, left_value, right_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_MATCH)
        if not isinstance(left_value, list):
            return MatchInfo(MatchRes.UN_MATCH)
        for v in left_value:
            if v in right_value or right_value in v:
                return MatchInfo(MatchRes.MATCH)
        return MatchInfo(MatchRes.UN_MATCH)

    def run_exists(self, left_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_MATCH)
        if isinstance(left_value, list) and len(left_value) != 0:
            return MatchInfo(MatchRes.MATCH)
        return MatchInfo(MatchRes.UN_MATCH)

    def run_necessary(self, left_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_MATCH)
        if isinstance(left_value, list) and len(left_value) == 1:
            return MatchInfo(MatchRes.MATCH)
        return MatchInfo(MatchRes.UN_MATCH)

    def run_collect_in(self, left_value, right_value):
        pass

    def run_collect_contains(self, left_value, right_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_MATCH)
        if not isinstance(left_value, list):
            return MatchInfo(MatchRes.UN_MATCH)
        for v in left_value:
            if str(right_value) in str(v):
                return MatchInfo(MatchRes.MATCH)
        return MatchInfo(MatchRes.UN_MATCH)


class ModelRunner(StrRuleRunner):
    def __init__(self, llm, kg_graph: KgGraph, query:str, req_id: str):
        super().__init__()
        self.llm = llm
        self.kg_graph = kg_graph
        self.query = query
        self.req_id = req_id
    def _get_kg_graph_data(self):
        return self.kg_graph.to_spo()

    def run_match(self, left_value, right_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        if not isinstance(left_value, list):
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        start_time = time.time()
        prompt = "根据提供的检索文档，请首先判断是否能够直接回答指令“{}”。如果可以直接回答，请直接回复答案，无需解释；如果不能直接回答但存在关联信息，请总结其中与指令“{}”相关的关键信息，并明确解释为何与指令相关；如果没有任何相关信息，直接回复“无相关信息”无需解释。\n【检索文档】：“{}”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。".format(
            right_value, right_value, str(self._get_kg_graph_data())
        )
        res = self.llm.generate(prompt, max_output_len=100)
        logging.info(f"ModelRunner {self.req_id} cost={time.time() - start_time} prompt={prompt} res={res}")
        return MatchInfo(trans_str_res_to_match(res), res)

    def run_collect_in(self, left_value, right_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        if not isinstance(left_value, list):
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        start_time = time.time()
        prompt = "根据提供的检索文档，请首先判断是否能够直接回答指令“{}”。如果可以直接回答，请直接回复答案，无需解释；如果不能直接回答但存在关联信息，请总结其中与指令“{}”相关的关键信息，并明确解释为何与指令相关；如果没有任何相关信息，直接回复“无相关信息”无需解释。\n【检索文档】：“{}”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。".format(
            right_value, right_value, str(self._get_kg_graph_data())
        )
        res = self.llm.generate(prompt, max_output_len=100)
        logging.info(f"ModelRunner {self.req_id} cost={time.time() - start_time} prompt={prompt} res={res}")
        return MatchInfo(trans_str_res_to_match(res), res)

    def run_collect_contains(self, left_value, right_value):
        if left_value is None:
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        if not isinstance(left_value, list):
            return MatchInfo(MatchRes.UN_RELATED, "判定信息不足")
        start_time = time.time()
        prompt = "根据提供的检索文档，请首先判断是否能够直接回答指令“{}”。如果可以直接回答，请直接回复答案，无需解释；如果不能直接回答但存在关联信息，请总结其中与指令“{}”相关的关键信息，并明确解释为何与指令相关；如果没有任何相关信息，直接回复“无相关信息”无需解释。\n【检索文档】：“{}”\n请确保所提供的信息直接准确地来自检索文档，不允许任何自身推测。".format(
            right_value, right_value, str(self._get_kg_graph_data())
        )
        res = self.llm.generate(prompt, max_output_len=100)
        logging.info(f"ModelRunner {self.req_id} cost={time.time() - start_time} prompt={prompt} res={res}")
        return MatchInfo(trans_str_res_to_match(res), res)


class OpRunner:
    def __init__(self, kg_graph: KgGraph, llm, query: str, req_id: str):
        self.kg_graph = kg_graph
        self.query = query
        if llm is None:
            self.runner: RuleRunner = StrRuleRunner()
        else:
            self.runner: ModelRunner = ModelRunner(llm, kg_graph, query, req_id)
        self.llm = llm

    def _get_identifer_to_doc(self, alias:Identifer):
        data = self.kg_graph.get_entity_by_alias(alias)
        if data is None:
            return []
        ret_data = []
        for d in data:
            if isinstance(d, EntityData):
                if d.type == "attribute":
                    ret_data.append(d.biz_id)
                else:
                    ret_data.append(d.to_json())
            elif isinstance(d, RelationData):
                ret_data.append(d.to_json())
            else:
                ret_data.append(d)
        return ret_data

    def _get_alias_to_doc(self, alias):
        if not isinstance(alias, list):
            alias_set = [alias]
        else:
            alias_set = set(alias)
        ret_data = []
        for alias_ele in alias_set:
            if isinstance(alias_ele, Identifer):
                ret_data = ret_data + self._get_identifer_to_doc(alias_ele)
            else:
                ret_data.append(alias)
        return ret_data

    def _get_value_ins_identifer(self, alias: Identifer):
        data = self.kg_graph.get_entity_by_alias(alias)
        if data is None:
            return []
        ret_data = []
        for d in data:
            if isinstance(d, EntityData) and d.type == "attribute":
                ret_data.append(d.biz_id)
            else:
                ret_data.append(d)
        return ret_data

    def _get_value_ins(self, alias):
        if isinstance(alias, list):
            alias_set = set(alias)
        else:
            alias_set = {alias}
        ret_data = []
        for alias_ele in alias_set:
            if isinstance(alias_ele, Identifer):
                ret_data = ret_data + self._get_value_ins_identifer(alias_ele)
            else:
                return alias
        return ret_data

    def run_single_binary_exec_rule(self, op_name: str, left_value, right_value):
        left_value = self._get_value_ins(left_value)
        right_value = self._get_value_ins(right_value)
        if left_value is None:
            return {}
        res = {}
        for left_value_ins in left_value:
            # 可能是实体或文本值
            left_value_text = left_value_ins
            if isinstance(left_value_ins, EntityData):
                left_value_text = left_value_ins.biz_id
            single_rule_res = self.runner.op_map[op_name](left_value_text, right_value)
            res[left_value_text] = single_rule_res
        return res

    def run_single_unary_exec_rule(self, op_name: str, left_value):
        left_value = self._get_value_ins(left_value)
        if left_value is None:
            return {}
        res = {}
        for left_value_ins in left_value:
            single_rule_res = self.runner.op_map[op_name](left_value_ins)
            res[left_value_ins] = single_rule_res
        return res

    def single_rule_dispatch(self, op_name: str, left_value, right_value):
        op_name = self._get_op_zh_2_en(op_name)

        binary_op = ['equal', 'lt', 'gt', 'le', 'ge', 'in', 'contains', 'and', 'or']
        unary_op = ['not']

        if op_name in binary_op:
            return self.run_single_binary_exec_rule(op_name, left_value, right_value)
        elif op_name in unary_op:
            return self.run_single_unary_exec_rule(op_name, left_value)
        else:
            raise RuntimeError(f"not impl op {op_name}")

    def collect_rule_dispatch(self, op_name: str, left_value, right_value):
        op_name = self._get_op_zh_2_en(op_name)
        collect_binary_op = ['match', 'contains', 'in']
        collect_unary_op = ['exist', 'necessary']
        if op_name in collect_unary_op:
            return self.run_collect_unary_exec_rule(op_name, left_value)
        elif op_name in collect_binary_op:
            return self.run_collect_binary_exec_rule(op_name, left_value, right_value)
        else:
            # agg by self
            res = self.single_rule_dispatch(op_name, left_value, right_value)
            if res is not None and True in res.values():
                return MatchInfo(MatchRes.MATCH, '')
            return MatchInfo(MatchRes.UN_MATCH, '')

    def run_collect_binary_exec_rule(self, op_name: str, left_value, right_value):
        collect_op_name_map = {
            "in": "collect_in",
            "contains": "collect_contains",
            "necessary": "necessary",
            "match": "match"
        }
        left_value = self._get_value_ins(left_value)
        right_value = self._get_value_ins(right_value)
        """
        res = MatchRes
        """
        res: MatchRes = self.runner.op_map[collect_op_name_map[op_name]](left_value, right_value)
        return res

    def run_collect_unary_exec_rule(self, op_name: str, left_value):
        left_value = self._get_value_ins(left_value)
        """
                res = MatchRes
                """
        res: MatchInfo = self.runner.op_map[op_name](left_value)
        return res

    def _get_op_zh_2_en(self, op_name):
        name_map = {
            "包含": "contains",
            "存在": "exist",
            "匹配": "match",
            "必要": "necessary",
            "等于": "equal",
            "大于": "gt",
            "小于": "lt"
        }
        if op_name not in name_map.keys():
            return op_name
        return name_map[op_name]

    def run_filter_op(self, f: FilterNode):
        # 对边不执行过滤
        if isinstance(f.left_expr, Identifer) and f.left_expr in self.kg_graph.edge_alias:
            return
        res = self.single_rule_dispatch(f.op, f.left_expr, f.right_expr)
        failed_list = []
        for r in res.keys():
            if not res[r]:
                failed_list.append(r)
        self.kg_graph.rmv_ins(f.left_expr, failed_list)

    def run_extractor_op(self, f: ExtractorNode):
        update_verify = VerifyNode("verify", {
            "left_expr": f.alias_set,
            "right_expr": self.query,
            "op": "匹配"
        })
        return self.run_verify_op(update_verify)

    def run_verify_op(self, f: VerifyNode):
        verify_kg_graph = KgGraph()
        left_expr_name = f.get_left_expr_name()
        s_alias_name = f"verify_s_{left_expr_name}"
        p_alias_name = f"verify_p_{left_expr_name}"
        o_alias_name = f"verify_o_{left_expr_name}"
        verify_kg_graph.query_graph[p_alias_name] = {
            "s": s_alias_name,
            "p": p_alias_name,
            "o": o_alias_name
        }
        left_value = self._get_alias_to_doc(f.left_expr)
        if len(left_value) == 0:
            return None, None, None

        verify_kg_graph.nodes_alias.append(s_alias_name)
        verify_kg_graph.nodes_alias.append(p_alias_name)
        verify_kg_graph.edge_alias.append(o_alias_name)
        s_entity_data = EntityData()
        s_entity_data.type = "verify_op"
        s_entity_data.type_zh = "判定"
        s_entity_data.biz_id = f"{left_expr_name}"
        s_entity_data.name = "检索信息"
        s_entity_data.description = "检索信息"
        left_expr_set = f.get_left_expr_set()
        description = []
        for left_epxr in left_expr_set:
            if left_epxr in self.kg_graph.logic_form_base.keys():
                description.append(f"{self.kg_graph.logic_form_base[left_epxr]}")
        if len(description) > 0:
            s_entity_data.description = "\n\n".join(description)
        right_value = f.right_expr
        if right_value is None or right_value == '':
            right_value = self.query
        right_value = self._get_alias_to_doc(right_value)
        match_info = self.collect_rule_dispatch(f.op, f.left_expr, f.right_expr)
        o_entity_data = EntityData()
        o_entity_data.type = "verify_op_result"
        o_entity_data.type_zh = "问题"
        o_entity_data.biz_id = match_info.trans_match_res_to_str()
        o_entity_data.name = match_info.trans_match_res_to_str()
        o_entity_data.description = match_info.desc
        rel = RelationData()
        rel.from_id = s_entity_data.biz_id
        rel.from_type = s_entity_data.type_zh
        rel.end_id = o_entity_data.biz_id
        rel.end_type = o_entity_data.type_zh
        rel.from_entity = s_entity_data
        rel.end_entity = o_entity_data
        rel.type = f"是否{f.op} {right_value}"

        verify_kg_graph.entity_map[s_alias_name] = [s_entity_data]
        verify_kg_graph.edge_map[p_alias_name] = [rel]

        self.kg_graph.merge_kg_graph(verify_kg_graph)
        return match_info, rel, p_alias_name

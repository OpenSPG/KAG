from kag.solver.logic.core_modules.common.base_model import SPOEntity, LogicNode
from kag.solver.logic.core_modules.common.one_hop_graph import KgGraph, EntityData, RelationData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.op_executor.op_executor import OpExecutor
from kag.solver.logic.core_modules.parser.logic_node_parser import GetNode
from kag.solver.logic.core_modules.retriver.entity_linker import spo_entity_linker, EntityLinkerBase
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunner


class GetExecutor(OpExecutor):
    def __init__(self, nl_query: str, kg_graph: KgGraph, schema: SchemaUtils, el: EntityLinkerBase,
                 dsl_runner: DslRunner, cached_map: dict, debug_info: dict, **kwargs):
        super().__init__(nl_query, kg_graph, schema, debug_info, **kwargs)

        self.el = el
        self.dsl_runner = dsl_runner
        self.cached_map = cached_map

    def executor(self, logic_node: LogicNode, req_id: str, param: dict) -> list:
        kg_qa_result = []
        if not isinstance(logic_node, GetNode) or not self.debug_info.get('exact_match_spo', False):
            return kg_qa_result

        n = logic_node
        s_data_set = self.kg_graph.get_entity_by_alias(n.alias_name)
        if isinstance(n.s, SPOEntity) and s_data_set is None:
            if len(n.s.id_set) > 0:
                start_info_set = n.s.generate_start_infos()
                for start_info in start_info_set:
                    id_info = EntityData()
                    id_info.type = start_info['type']
                    id_info.biz_id = start_info['id']
                    s_data_set = [id_info]
            elif n.s.entity_name:
                el_results, el_request, err_msg, call_result_data = spo_entity_linker(self.kg_graph,
                                                                                      n,
                                                                                      self.nl_query,
                                                                                      self.el,
                                                                                      self.schema,
                                                                                      req_id,
                                                                                      param)
                self.debug_info['el'] = self.debug_info['el'] + el_results
                self.debug_info['el_detail'] = self.debug_info['el_detail'] + [{
                    "el_request": el_request,
                    'el_results': el_results,
                    'el_debug_result': call_result_data,
                    'err_msg': err_msg
                }]
                n.to_std(n.args)
                s_data_set = self.kg_graph.get_entity_by_alias(n.alias_name)
        if s_data_set is None:
            self.debug_info['get_empty'].append(n.to_dict())
            return kg_qa_result

        s_biz_id_set = []
        for s_data in s_data_set:
            if isinstance(s_data, EntityData):
                if s_data.name == '':
                    s_biz_id_set.append(s_data.biz_id)
                else:
                    kg_qa_result.append(s_data.name)
            if isinstance(s_data, RelationData):
                kg_qa_result.append(str(s_data))
        if len(s_biz_id_set) > 0:
            one_hop_cached_map = self.dsl_runner.query_vertex_property_by_s_ids(s_biz_id_set,
                                                                                n.s.get_entity_first_type(),
                                                                                self.cached_map)

            self.kg_graph.nodes_alias.append(n.alias_name)
            entities = []
            for one_hop in one_hop_cached_map.keys():
                kg_qa_result.append(one_hop_cached_map[one_hop].s.name)
                entities.append(one_hop_cached_map[one_hop].s)

            if n.alias_name not in self.kg_graph.entity_map.keys():
                self.kg_graph.entity_map[n.alias_name] = entities
            else:
                self.kg_graph.entity_map[n.alias_name] = self.kg_graph.entity_map[n.alias_name] + entities
        return kg_qa_result

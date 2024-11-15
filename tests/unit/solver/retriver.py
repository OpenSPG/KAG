import unittest

from kag.solver.logic.core_modules.common.one_hop_graph import EntityData
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from kag.solver.logic.core_modules.retriver.graph_retriver.dsl_executor import DslRunnerOnGraphStore


class KgRetriverTest(unittest.TestCase):
    def test_reason_dsl(self):
        config = LogicFormConfiguration({
            "prefix": "KQA2",
            "project_id": "5"
        })
        schema = SchemaUtils(config)
        schema.get_schema()
        dsl_runner = DslRunnerOnGraphStore(config.project_id, schema, config)
        s_data = EntityData()
        s_data.type = "KQA2.Others"
        s_data.biz_id = "Panic disorder"
        ret = dsl_runner.query_vertex_one_graph_by_s_o_ids([s_data], [], {})
        assert len(ret) == 1
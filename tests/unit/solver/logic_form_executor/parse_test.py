import unittest

from kag.interface.solver.base_model import SPOEntity, SPORelation
from kag.common.parser.logic_node_parser import binary_expr_parse, ParseLogicForm

parser = ParseLogicForm(None, None)


class ParseTest(unittest.TestCase):
    def test_entity_parse0(self):
        spo_entity = SPOEntity.parse_logic_form("s1:政务事项")
        assert spo_entity.entity_name == None
        assert len(spo_entity.id_set) == 0
        assert len(spo_entity.type_set) == 1
        assert spo_entity.type_set[0].un_std_entity_type == "政务事项"
        assert spo_entity.alias_name == "s1"

    def test_binary_expr_parse_1(self):
        test_str = "left_expr=o1, right_expr=杭州市， op=等于"
        out = binary_expr_parse(test_str)
        print(out)
        assert out["op"] == "等于"

    def test_binary_expr_parse_2(self):
        test_str = "left_expr=o1, right_expr=杭州市，abc， op=等于"
        out = binary_expr_parse(test_str)
        print(out)
        assert out["op"] == "等于"
        assert out['right_expr'] == '杭州市，abc'

    def test_entity_parse(self):
        spo_entity = SPOEntity.parse_logic_form("s1:政务事项[浙江省-杭州市-西湖区申领]")
        assert spo_entity.entity_name == "浙江省-杭州市-西湖区申领"
        assert len(spo_entity.id_set) == 0
        assert len(spo_entity.type_set) == 1
        assert spo_entity.type_set[0].un_std_entity_type == "政务事项"
        assert spo_entity.alias_name == "s1"

    def test_entity_parse2(self):
        spo_entity = SPOEntity.parse_logic_form("s1:电影明星|电影导演[张三]")
        assert spo_entity.entity_name == "张三"
        assert len(spo_entity.id_set) == 0
        assert len(spo_entity.type_set) == 2
        assert spo_entity.type_set[0].un_std_entity_type == "电影明星"
        assert spo_entity.alias_name == "s1"

    def test_entity_parse3(self):
        spo_entity = SPOEntity.parse_logic_form("s1:`电影明星`[张三][1]")
        assert spo_entity.entity_name == "张三"
        assert len(spo_entity.id_set) == 1
        assert spo_entity.id_set[0] == "1"
        assert len(spo_entity.type_set) == 1
        assert spo_entity.type_set[0].un_std_entity_type == "电影明星"
        assert spo_entity.alias_name == "s1"

    def test_entity_parse4(self):
        spo_entity = SPOEntity.parse_logic_form("s1:电影（，明星|电影导演[张三][`1|3`|2]")
        assert spo_entity.entity_name == "张三"
        assert len(spo_entity.id_set) == 2
        assert spo_entity.id_set[0] == "1|3"
        assert spo_entity.id_set[1] == "2"
        assert len(spo_entity.type_set) == 2
        assert spo_entity.type_set[0].un_std_entity_type == "电影（，明星"
        assert spo_entity.type_set[1].un_std_entity_type == "电影导演"
        assert spo_entity.alias_name == "s1"

    def test_entity_parse5(self):
        spo_entity = SPOEntity.parse_logic_form("s1")
        assert spo_entity.alias_name == "s1"

    def test_rel_parse1(self):
        spo_rel = SPORelation.parse_logic_form("p1")
        assert spo_rel.alias_name == "p1"

    def test_rel_parse2(self):
        spo_rel = SPORelation.parse_logic_form("p1:演）员")
        assert spo_rel.alias_name == "p1"
        assert len(spo_rel.type_set) == 1
        assert spo_rel.type_set[0].un_std_entity_type == "演）员"

    def test_rel_parse3(self):
        spo_rel = SPORelation.parse_logic_form("p1:`参演`|`导演`")
        assert spo_rel.alias_name == "p1"
        assert len(spo_rel.type_set) == 2
        assert spo_rel.type_set[0].un_std_entity_type == "参演"
        assert spo_rel.type_set[1].un_std_entity_type == "导演"

    def test_get_spo_parse(self):
        spo_node = parser.parse_logic_form("get_spo(s=s1:政务事项[身份证挂失], p=p1:线上办事渠道， o=o1:办事渠道）", {})
        assert spo_node.o.get_un_std_entity_first_type_or_std() == "办事渠道"
        print(spo_node.to_dict())

    def test_get_spo_parse2(self):
        spo_node = parser.parse_logic_form("get_spo(s=s1:政务事项[身份证挂失],p=p1:线上办事渠道,o=o1:办事渠道)", {})
        assert spo_node.o.get_un_std_entity_first_type_or_std() == "办事渠道"
        print(spo_node.to_dict())

    def test_get_spo_parse3(self):
        spo_node = parser.parse_logic_form("get_spo(s=s1:政务事项[身份）证(挂失], p=p1:线上办事渠道， o=o1:办事渠道）", {})
        assert spo_node.s.entity_name == "身份）证(挂失"
        print(spo_node.to_dict())

    def test_get_spo_parse4(self):
        spo_node = parser.parse_logic_form("get_spo(s=s1:政务事项[身份（证）挂失],p=p1:线上办事渠道,o=o1:办事渠道)", {})
        assert spo_node.s.entity_name == "身份（证）挂失"
        print(spo_node.to_dict())
        print(spo_node)

    def test_get_parse(self):
        spo_node = parser.parse_logic_form("get(o1)", {})
        assert spo_node.alias_name == "o1"
        print(spo_node.to_dict())

    def test_get_parse2(self):
        spo_node = parser.parse_logic_form("get(o1）", {})
        assert spo_node.alias_name == "o1"
        print(spo_node.to_dict())

    def test_get_parse3(self):
        spo_node = parser.parse_logic_form("get(o1,o2）", {})
        assert spo_node.alias_name == "o1"
        print(spo_node.to_dict())

    def test_verify_parse(self):
        verify_node = parser.parse_logic_form("verify(left_expr=o1,o1, right_expr=, op=存在）", {})
        assert verify_node.left_expr == "o1"
        assert verify_node.right_expr == None
        assert verify_node.op == "存在"
        print(verify_node.to_dict())

    def test_verify_parse2(self):
        verify_node = parser.parse_logic_form("verify(left_expr=o1,o1,  op=存在）", {})
        assert verify_node.left_expr == "o1"
        assert verify_node.right_expr == None
        assert verify_node.op == "存在"
        print(verify_node.to_dict())

    def test_extractor_parse(self):
        extractor_node = parser.parse_logic_form("extractor(o1,o2)")
        assert len(extractor_node.alias_set) == 2

    def test_verify_parse_2(self):
        verify_node = parser.parse_logic_form("verify(left_expr=o1, right_expr=身份证还没有到期,可以更换吗, op=存在）", {})
        assert verify_node.right_expr == "身份证还没有到期,可以更换吗"

    def test_get_spo_parse5(self):
        spo_node = parser.parse_logic_form(
            "get_spo(s=s1:检查检验结果术语[血压], p=p1:关联术语，  o=o1:检查检验结果, s.value=>160, s.brand=权健)", {})
        assert len(spo_node.s.value_list) == 2
        for v in spo_node.s.value_list:
            if v[0] == "value":
                assert v[1] == ">160"
            if v[0] == "brand":
                assert v[1] == "权健"
        print(spo_node.to_dict())

    def test_search_s_parse1(self):
        spo_node = parser.parse_logic_form("search_s(s=s1:医院, s.省份=浙江省, s.城市=杭州市)", {})
        assert spo_node.s.alias_name == "s1"
        assert spo_node.s.type_set[0].un_std_entity_type == '医院'
        assert '省份' in spo_node.s.value_list.keys()
        assert '城市' in spo_node.s.value_list.keys()

        spo_node = parser.parse_logic_form("search_s(s=s2:医生, s.主执业医院=s1.name, s.主执业科室=心内科)", {})
        assert spo_node.s.alias_name == "s2"
        assert spo_node.s.type_set[0].un_std_entity_type == '医生'
        assert '主执业医院' in spo_node.s.value_list.keys()
        assert '主执业科室' in spo_node.s.value_list.keys()
        assert spo_node.s.value_list['主执业医院'] == ['s1', 'name']

    def test_Retrieval_parse(self):
        retrieval_node = parser.parse_logic_form("Retrieval(s=s1:医院[`,]`], p=p1:关联术语, o=o1:检查检验结果, s.value=>160, s.brand=权健)", {})
        assert retrieval_node.s.entity_name == ',]'

if __name__ == '__main__':
    unittest.main()
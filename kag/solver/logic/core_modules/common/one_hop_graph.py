import json
import logging
import re

from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils

logger = logging.getLogger()


def find_and_extra_prop_objects(text):
    """
    Extracts and parses serialized objects from the given text.

    This function searches for all strings in the provided text that match the serialized format,
    then parses each found serialized string to extract object properties,
    and finally stores the parsed objects as dictionaries in a list which is returned.

    Parameters:
    text (str): The text containing serialized objects.

    Returns:
    list: A list of dictionaries representing the parsed objects.
    """

    pattern = re.compile(r'\001(.*?)\003')

    matches = pattern.findall(text)

    objects = []

    for match in matches:
        attributes = match.split('\002')
        if len(attributes) != 3:
            logger.info(f"find_and_extra_prop_objects attribute not match {match}")
            continue

        objects.append({
            "id": attributes[1],
            "name": attributes[0],
            "type": attributes[2]
        })

    return objects


class Prop:
    def __init__(self):
        self.origin_prop_map = {}
        self.extend_prop_map = {}
        self.linked_prop_map = {}

    def get_properties_map_list_value(self):
        result = {}
        for k in self.origin_prop_map.keys():
            result[k] = [self.origin_prop_map[k]]
        for k in self.extend_prop_map.keys():
            result[k] = [self.extend_prop_map[k]]
        return result

    @staticmethod
    def _get_ext_json_prop(schema: SchemaUtils):
        if schema is None:
            return []
        return schema.get_ext_json_prop()

    @staticmethod
    def _get_attr_en_zh_by_label(label_name, schema: SchemaUtils):
        if schema is None:
            return {}
        return schema.get_attr_en_zh_by_label(label_name)

    @staticmethod
    def from_dict(json_dict: dict, label_name: str, schema: SchemaUtils):
        prop = Prop()
        ext_attrs = Prop._get_ext_json_prop(schema)
        attr_en_zh = Prop._get_attr_en_zh_by_label(label_name, schema)
        black_attr = ["biz_node_id", "gdb_timestamp"]
        for k in json_dict.keys():
            if json_dict[k] == '' or k in black_attr:
                continue
            if k.startswith("_") or k in ext_attrs:
                continue
            if k in attr_en_zh.keys():
                key = attr_en_zh[k]
            else:
                key = k
            prop.origin_prop_map[key] = json_dict[k]

        for ext_attr in ext_attrs:
            if ext_attr not in json_dict.keys():
                continue
            try:
                basic_info = json.loads(json_dict[ext_attr])
                for k in basic_info.keys():
                    v = basic_info[k]
                    link_res = find_and_extra_prop_objects(v)
                    prop.linked_prop_map[k] = link_res
                prop.extend_prop_map = basic_info
            except Exception as e:
                logger.warning(f"parse basic info failed reasone: {json_dict[ext_attr]}", exc_info=True)
        return prop

    def to_json(self):
        return {
            "origin_prop_map": self.origin_prop_map,
            "extend_prop_map": self.extend_prop_map
        }

    def get_prop_value(self, p):
        if p in self.origin_prop_map.keys():
            return self.origin_prop_map[p]
        if p in self.extend_prop_map.keys():
            return self.extend_prop_map[p]
        return None


class EntityData:
    def __init__(self):
        self.prop: Prop = None
        self.biz_id: str = None
        self.name: str = ""
        self.description: str = ""
        self.type: str = None
        self.type_zh: str = None
        self.score = 1.0

    def get_properties_map_list_value(self):
        if self.prop is None:
            return {}
        return self.prop.get_properties_map_list_value()

    def to_show_id(self):
        if self.type in ['verify_op_result'] and self.description is not None and self.description != '':
            return f"{self.type_zh}[{self.name}]({self.description})"
        if self.name == self.biz_id:
            return f"{self.type_zh}[{self.name}]"
        return f"{self.type_zh}[{self.name}]({self.biz_id})"

    def to_json(self):
        return {
            "prop": {} if self.prop is None else self.prop.to_json(),
            "biz_id": self.biz_id,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "type_zh": self.type_zh
        }

    def get_attribute_value(self, p):
        if self.prop is None:
            return None
        return self.prop.get_prop_value(p)

    def merge_entity_data(self, other):
        if other.prop is not None:
            self.prop = other.prop
        if other.name is not None and other.name != '':
            self.name = other.name

        if other.description is not None and other.description != '':
            self.description = other.description

        if other.type is not None and other.type != '':
            self.type = other.type

        if other.type_zh is not None and other.type_zh != '':
            self.type_zh = other.type_zh

    def to_spo_list(self):
        spo_list = []
        spo_list.append(json.dumps({
            "s": self.name,
            "p": "归属类型",
            "o": self.type
        }, ensure_ascii=False))
        if self.prop is not None:
            for prop_key in self.prop.origin_prop_map.keys():
                if prop_key.startswith("_"):
                    continue
                if prop_key in ['id', 'name']:
                    continue
                spo_list.append(json.dumps({
                    "s": self.name,
                    "p": prop_key,
                    "o": self.prop.origin_prop_map[prop_key]
                }, ensure_ascii=False))
            for prop_key in self.prop.extend_prop_map.keys():
                spo_list.append(json.dumps({
                    "s": self.name,
                    "p": prop_key,
                    "o": self.prop.extend_prop_map[prop_key]
                }, ensure_ascii=False))
        return spo_list

    # def __repr__(self):
    #     return f"({self.name} [{self.type}] ({self.biz_id}) {self.description}"
    def __repr__(self):
        return f"{self.name} [{self.type}]"


def get_label_without_prefix(schema: SchemaUtils, label):
    if schema is None:
        return label
    return schema.get_label_without_prefix(label)


class RelationData:
    def __init__(self):
        self.prop: Prop = None
        self.from_id: str = None
        self.end_id: str = None
        self.from_entity: EntityData = None
        self.from_type: str = None
        self.from_alias = "s"
        self.end_type: str = None
        self.end_entity: EntityData = None
        self.end_alias = "o"
        self.type: str = None

    def get_spo_type(self):
        return f"{self.from_type}_{self.type}_{self.end_type}"

    def get_spo_show_id(self):
        return self.from_entity.to_show_id(), self.type, self.end_entity.to_show_id()

    def to_show_id(self):
        return f"{self.from_entity.to_show_id()} {self.type} {self.end_entity.to_show_id()}"

    def get_properties_map_list_value(self):
        if self.prop is None:
            return {}
        return self.prop.get_properties_map_list_value()

    def to_json(self):
        return {
            "prop": {} if self.prop is None else self.prop.to_json(),
            "from_id": self.from_id,
            "end_id": self.end_id,
            "from_entity_name": self.from_entity.name,
            "from_type": self.from_type,
            "end_entity_name": self.end_entity.name,
            "end_type": self.end_type,
            "type": self.type
        }

    def _get_entity_description(self, entity: EntityData):
        if entity is None:
            return None
        if entity.description is None or entity.description == '':
            return None
        if entity.type == "attribute":
            return None
        return entity.description

    def _get_entity_id(self, name: str, id: str):
        if id == name:
            return ""
        else:
            return f"[{id}]"

    def to_spo_list(self):
        spo_list = []
        rel = {
            "s": self.from_entity.name,
            "p": self.type,
            "o": self.end_entity.name
        }
        spo_list.append(json.dumps(rel, ensure_ascii=False))
        # prop
        if self.prop is not None:
            for prop_key in self.prop.origin_prop_map.keys():
                spo_list.append(json.dumps({
                    "s": rel,
                    "p": prop_key,
                    "o": self.prop.origin_prop_map[prop_key]
                }, ensure_ascii=False))
            for prop_key in self.prop.extend_prop_map.keys():
                spo_list.append(json.dumps({
                    "s": rel,
                    "p": prop_key,
                    "o": self.prop.extend_prop_map[prop_key]
                }, ensure_ascii=False))
        return spo_list

    def __repr__(self):
        from_entity_desc = self._get_entity_description(self.from_entity)
        from_entity_desc_str = "" if from_entity_desc is None else f"({from_entity_desc})"
        to_entity_desc = self._get_entity_description(self.end_entity)
        to_entity_desc_str = "" if to_entity_desc is None else f"({to_entity_desc})"
        return f"({self.from_entity.name}{from_entity_desc_str} {self.type} {self.end_entity.name}{to_entity_desc_str})"

    @staticmethod
    def from_dict(json_dict: dict, schema: SchemaUtils):
        rel = RelationData()

        rel.from_id = json_dict["__from_id__"]
        rel.from_type = get_label_without_prefix(schema, json_dict["__from_id_type__"])
        rel.end_id = json_dict["__to_id__"]
        rel.end_type = get_label_without_prefix(schema, json_dict["__to_id_type__"])
        rel.type = json_dict["__label__"]
        spo_label_name = f"{rel.from_type}_{rel.type}_{rel.end_type}"
        rel.prop = Prop.from_dict(json_dict, spo_label_name, schema)
        if schema is not None:
            if spo_label_name in schema.spo_en_zh.keys():
                rel.type = schema.get_spo_with_p(schema.spo_en_zh[spo_label_name])
        return rel

    def revert_spo(self):
        rel = RelationData()
        rel.from_id = self.end_id
        rel.from_type = self.end_type
        rel.from_entity = self.end_entity

        rel.end_id = self.from_id
        rel.end_type = self.from_type
        rel.end_entity = self.from_entity

        rel.type = self.type
        rel.prop = self.prop
        return rel

    @staticmethod
    def from_prop_value(s: EntityData, p: str, o: EntityData):
        rel = RelationData()
        rel.type = p

        rel.from_id = s.biz_id
        rel.from_type = s.type
        rel.from_entity = s

        rel.end_id = o.biz_id
        rel.end_type = o.type
        rel.end_entity = o
        return rel


class OneHopGraphData:
    def __init__(self, schema, alias_name):
        self.s_alias_name = alias_name
        self.s: EntityData = None
        self.in_relations: dict = {}
        self.out_relations: dict = {}
        self.schema = schema

    def to_graph_detail(self):
        s_po_map = {}
        prop_map = self.s.get_properties_map_list_value()
        # get out edge map
        for k in self.out_relations.keys():
            for rel in self.out_relations[k]:
                s, p, o = rel.get_spo_show_id()
                rel_prop_map = rel.get_properties_map_list_value()
                if len(rel_prop_map) > 0:
                    s_po_map[f"{s} {p} {o}"] = rel_prop_map
                if p in prop_map.keys():
                    prop_map[p].append(o)
                else:
                    prop_map[p] = [o]
                end_prop_map = rel.end_entity.get_properties_map_list_value()
                if o not in s_po_map.keys():
                    s_po_map[o] = end_prop_map

        s_po_map[self.s.to_show_id()] = prop_map

        for k in self.in_relations.keys():
            for rel in self.in_relations[k]:
                s, p, o = rel.get_spo_show_id()
                rel_prop_map = rel.get_properties_map_list_value()
                if len(rel_prop_map) > 0:
                    s_po_map[f"{s} {p} {o}"] = rel_prop_map
                start_prop_map = rel.from_entity.get_properties_map_list_value()
                if s not in s_po_map.keys():
                    s_po_map[s] = {
                        p: [o]
                    }
                else:
                    s_po_map[s].update({
                        p: [o]
                    })
                s_po_map[s].update(start_prop_map)
        return s_po_map

    def _schema_attr_en_to_zh(self, k):
        if self.schema is None:
            return k
        return self.schema.attr_en_zh.get(k)

    def get_s_all_attribute_spo(self):
        # spo_list = []
        attr_name_set_map = {}
        if self.s.prop is None:
            return attr_name_set_map
        if len(self.s.prop.origin_prop_map) > 0:
            for k in self.s.prop.origin_prop_map.keys():
                if k in ['id', 'name']:
                    continue
                if k.startswith("_"):
                    continue
                spo_list = []
                if isinstance(self.s.prop.origin_prop_map[k], list):
                    for v in self.s.prop.origin_prop_map[k]:
                        spo_list.append(str(v))
                else:
                    spo_list.append(str(self.s.prop.origin_prop_map[k]))
                attr_name_set_map[k] = spo_list
        if len(self.s.prop.extend_prop_map) > 0:
            for k in self.s.prop.extend_prop_map.keys():
                if k in ['id', 'name']:
                    continue
                if k.startswith("_"):
                    continue
                spo_list = []
                if isinstance(self.s.prop.origin_prop_map[k], list):
                    for v in self.s.prop.origin_prop_map[k]:
                        spo_list.append(str(v))
                else:
                    spo_list.append(str(self.s.prop.origin_prop_map[k]))
                attr_name_set_map[k] = spo_list
        return attr_name_set_map

    def get_s_all_attribute_name(self):
        attribute_name_set = []
        if self.s.prop is None:
            return attribute_name_set
        if len(self.s.prop.origin_prop_map) > 0:
            for k in self.s.prop.origin_prop_map.keys():
                attribute_name_set.append(self._schema_attr_en_to_zh(k))
        if len(self.s.prop.extend_prop_map) > 0:
            for k in self.s.prop.extend_prop_map.keys():
                attribute_name_set.append(k)
        return attribute_name_set

    def get_std_attribute_value(self, p):
        return self.s.get_attribute_value(p)

    def get_std_relation_value(self, p):
        relation_value_set = []
        if p in self.in_relations.keys():
            for rel in self.in_relations[p]:
                if "s" == self.s_alias_name:
                    relation_value_set.append(rel.revert_spo())
                else:
                    relation_value_set.append(rel)
        if p in self.out_relations.keys():
            for rel in self.out_relations[p]:
                if "o" == self.s_alias_name:
                    relation_value_set.append(rel.revert_spo())
                else:
                    relation_value_set.append(rel)
        return relation_value_set

    def get_all_relation_value(self):
        relation_value_set = []
        for p in self.in_relations.keys():
            for rel in self.in_relations[p]:
                if "s" == self.s_alias_name:
                    relation_value_set.append(rel.revert_spo())
                else:
                    relation_value_set.append(rel)
        for p in self.out_relations.keys():
            for rel in self.out_relations[p]:
                if "o" == self.s_alias_name:
                    relation_value_set.append(rel.revert_spo())
                else:
                    relation_value_set.append(rel)
        return relation_value_set

    def _prase_attribute_relation(self, std_p: str, attr_value: str):
        # new a RelationData
        prop_entity = EntityData()
        prop_entity.biz_id = attr_value
        prop_entity.name = attr_value
        prop_entity.type = "attribute"
        prop_entity.type_zh = "文本"

        return self._prase_entity_relation(std_p, prop_entity)

    def _prase_entity_relation(self, std_p: str, o_value: EntityData):
        s_entity = self.s
        o_entity = o_value
        if self.s_alias_name == "o":
            o_entity = self.s
            s_entity = o_value
        if o_value.description is None or o_value.description == '':
            o_value.description = f"{s_entity.name} {std_p} {o_entity.name}"
        return RelationData.from_prop_value(s_entity, std_p, o_entity)


    def get_std_attr_value_by_spo_text(self, p, spo_text):

        spo_list = []
        if self.s.prop is None:
            return spo_list
        if len(self.s.prop.origin_prop_map) > 0:
            for k in self.s.prop.origin_prop_map.keys():
                if k in ['id', 'name']:
                    continue
                if k.startswith("_"):
                    continue
                if isinstance(self.s.prop.origin_prop_map[k], list):
                    for v in self.s.prop.origin_prop_map[k]:
                        if spo_text == str(v):
                            spo_list.append(self._prase_attribute_relation(p, v))
                else:
                    if spo_text == str(self.s.prop.origin_prop_map[k]):
                        spo_list.append(self._prase_attribute_relation(p, spo_text))
        return spo_list

    def get_std_p_value_by_spo_text(self, p, spo_text):
        relation_value_set = []
        if p in self.in_relations.keys():
            for rel in self.in_relations[p]:
                if spo_text == str(rel).strip('(').strip(')'):
                    if "s" == self.s_alias_name:
                        relation_value_set.append(rel.revert_spo())
                    else:
                        relation_value_set.append(rel)
        if p in self.out_relations.keys():
            for rel in self.out_relations[p]:
                if spo_text == str(rel).strip('(').strip(')'):
                    if "o" == self.s_alias_name:
                        relation_value_set.append(rel.revert_spo())
                    else:
                        relation_value_set.append(rel)
        prop = self.s.prop.get_properties_map_list_value()
        if p in prop.keys():
            v_set = prop[p]
            for rel in v_set:
                relation_value_set.append(self._prase_attribute_relation(p, str(rel)))
        return relation_value_set


    def get_edge_en_to_zh(self, k):
        if self.schema is None:
            return k
        return self.schema.edge_en_zh.get(k, k)

    def get_s_all_relation_spo(self):
        # spo_list = []
        relation_name_set_map = {}
        if len(self.in_relations) > 0:
            for k in self.in_relations.keys():
                if k in ['similarity']:
                    continue
                spo_list = []
                for v in self.in_relations[k]:
                    spo_list.append(str(v).strip('(').strip(')'))
                relation_name_set_map[k] = spo_list
        if len(self.out_relations) > 0:
            for k in self.out_relations.keys():
                if k in ['similarity']:
                    continue
                spo_list = []
                for v in self.out_relations[k]:
                    spo_list.append(str(v).strip('(').strip(')'))
                relation_name_set_map[k] = spo_list
        return relation_name_set_map

    def get_s_all_relation_name(self):
        relation_name_set = []
        if len(self.in_relations) > 0:
            for k in self.in_relations.keys():
                relation_name_set.append(self.get_edge_en_to_zh(k))
        if len(self.out_relations) > 0:
            for k in self.out_relations.keys():
                relation_name_set.append(self.get_edge_en_to_zh(k))
        return relation_name_set


def copy_one_hop_graph_data(other: OneHopGraphData, alias_name: str):
    ret = OneHopGraphData(other.schema, alias_name)
    ret.s = other.s
    ret.in_relations = other.in_relations
    ret.out_relations = other.out_relations
    return ret


class KgGraph:
    def __init__(self):
        self.logic_form_base = {}
        self.start_node_alias_name = []
        self.start_node_name = []
        self.query_graph = {}
        self.nodes_alias = []
        self.edge_alias = []
        self.entity_map = {}
        self.edge_map = {}

    def merge_kg_graph(self, other, wo_intersect=True):
        self.nodes_alias = list(set(self.nodes_alias + other.nodes_alias))
        self.edge_alias = list(set(self.edge_alias + other.edge_alias))
        for n_alias in other.entity_map.keys():
            if n_alias in self.entity_map.keys():
                alias_entity_id_map = {}
                for n_data in other.entity_map[n_alias]:
                    alias_entity_id_map[n_data.biz_id] = n_data
                n_alias_merged_list = []
                for n_data in self.entity_map[n_alias]:
                    if n_data.biz_id in alias_entity_id_map.keys():
                        n_data.merge_entity_data(alias_entity_id_map[n_data.biz_id])
                        alias_entity_id_map.pop(n_data.biz_id)
                    n_alias_merged_list.append(n_data)
                n_alias_merged_list.extend(list(alias_entity_id_map.values()))
                self.entity_map[n_alias] = n_alias_merged_list
            else:
                self.entity_map[n_alias] = other.entity_map[n_alias]

        for e_alias in other.edge_map.keys():
            if e_alias in self.edge_map.keys():
                self.edge_map[e_alias] = self.edge_map[e_alias] + other.edge_map[e_alias]
            else:
                self.edge_map[e_alias] = other.edge_map[e_alias]
        for p in other.query_graph.keys():
            self.query_graph[p] = other.query_graph[p]
        if not wo_intersect:
            for p in other.query_graph.keys():
                self.query_graph[p] = other.query_graph[p]
                o_alias = self.query_graph[p]["o"]
                spo = self.get_all_relation_spo(o_alias)
                for s1, p1, o1 in spo:
                    if p1 == p:
                        continue
                    p_rels = self.edge_map[p] if p in self.edge_map.keys() else []
                    if p1 not in self.edge_map.keys():
                        continue
                    rels = self.edge_map[p1]
                    intersect_rels = []
                    for rel in rels:
                        for p_rel in p_rels:
                            if o1 == o_alias and rel.end_id == p_rel.end_id:
                                intersect_rels.append(rel)
                                break
                            if s1 == o_alias and rel.from_id == p_rel.end_id:
                                intersect_rels.append(rel)
                                break
                    self.edge_map[p1] = intersect_rels

    def to_edge_evidence(self):
        edge_map_str = []
        for k in self.edge_map.keys():
            rels = []
            for d in self.edge_map[k]:
                rels.append(str(d))
            edge_map_str.append(f"spo:{k} value:{','.join(rels)}")
        return edge_map_str

    def _entity_map_to_json(self):
        result_dict = {}
        for k in self.entity_map.keys():
            k_nodes = []
            for d in self.entity_map[k]:
                k_nodes.append(d.to_json())
            result_dict[k] = k_nodes
        return result_dict

    def _edge_map_to_json(self):
        result_dict = {}
        for k in self.edge_map.keys():
            rels = []
            for d in self.edge_map[k]:
                rels.append(d.to_json())
            result_dict[k] = rels
        return result_dict

    def to_answer_path(self):
        answer_path = []
        sp_o_map = {}
        for k in self.edge_map.keys():
            for d in self.edge_map[k]:
                s, p, o = d.get_spo_show_id()
                if (s, p) in sp_o_map.keys():
                    if o not in sp_o_map[(s, p)]:
                        sp_o_map[(s, p)].append(o)
                else:
                    sp_o_map[(s, p)] = [o]
        used_entities = []
        for k in sp_o_map.keys():
            answer_path.append({
                "s": k[0],
                "p": k[1],
                "o": sp_o_map[k]
            })
            used_entities.append(k[0])
            used_entities = used_entities + sp_o_map[k]
            used_entities = list(set(used_entities))
        return answer_path

    def get_all_entity_id(self):
        all_entity_id = []
        for k in self.edge_map.keys():
            for d in self.edge_map[k]:
                all_entity_id.append(d.from_id)
                all_entity_id.append(d.end_id)
        for k in self.entity_map.keys():
            for d in self.entity_map[k]:
                all_entity_id.append(d.biz_id)
        return list(set(all_entity_id))

    def get_all_entity(self):
        all_entity = []
        for k in self.edge_map.keys():
            for d in self.edge_map[k]:
                all_entity.append(d.from_entity)
                all_entity.append(d.end_entity)
        for k in self.entity_map.keys():
            for d in self.entity_map[k]:
                all_entity.append(d)
        return list(set(all_entity))

    def _graph_to_json(self):
        total_entity_map = {}
        edge_dict = {}
        has_entity = False
        for k in self.edge_map.keys():
            rels = []
            s_alias = self.query_graph[k]["s"]
            total_entity_map[s_alias] = []
            o_alias = self.query_graph[k]["o"]
            total_entity_map[o_alias] = []
            for d in self.edge_map[k]:
                has_entity = True
                rels.append(d.to_json())
                if d.from_alias == "s" and d.from_entity not in total_entity_map[s_alias]:
                    total_entity_map[s_alias].append(d.from_entity)
                if d.from_alias == "o" and d.from_entity not in total_entity_map[o_alias]:
                    total_entity_map[o_alias].append(d.from_entity)

                if d.end_alias == "s" and d.end_entity not in total_entity_map[s_alias]:
                    total_entity_map[s_alias].append(d.end_entity)
                if d.end_alias == "o" and d.end_entity not in total_entity_map[o_alias]:
                    total_entity_map[o_alias].append(d.end_entity)

            edge_dict[k] = rels
        if not has_entity:
            node_dict = self._entity_map_to_json()
        else:
            node_dict = {}
            for k in total_entity_map.keys():
                k_nodes = []
                for d in total_entity_map[k]:
                    k_nodes.append(d.to_json())
                node_dict[k] = k_nodes
        return edge_dict, node_dict

    def add_start_node_name_and_alias(self, alias_name, node_name_list):
        if alias_name not in self.start_node_alias_name:
            self.start_node_alias_name.append(alias_name)
        for n in node_name_list:
            if n not in self.start_node_name:
                self.start_node_name.append(n)

    def to_json(self):
        edge_dict, node_dict = self._graph_to_json()
        return {
            "query_graph": self.query_graph,
            "nodes_alias": self.nodes_alias,
            "edge_alias": self.edge_alias,
            "start_node_alias_name": list(set(self.start_node_alias_name)),
            "start_node_name": list(set(self.start_node_name)),
            "entity_map": node_dict,
            "edge_map": edge_dict
        }

    def to_edge_str(self):
        return "\n".join(self.to_edge_evidence())

    def to_node_evidence(self):
        node_map_str = []
        for k in self.entity_map.keys():
            k_node = []
            for d in self.entity_map[k]:
                k_node.append(str(d))
            node_map_str.append(f"alias {k}, value:{','.join(k_node)}")
        return node_map_str

    def to_node_str(self):
        return "\n".join(self.to_node_evidence())

    def to_evidence(self):
        if len(self.query_graph) == 0:
            return self.to_node_evidence()
        return self.to_edge_evidence()

    def to_spo(self):
        recored_ids = []
        spo_list = []
        for k in self.entity_map.keys():
            for d in self.entity_map[k]:
                spo_list = spo_list + d.to_spo_list()
                recored_ids.append(f"{d.type}_{d.biz_id}")

        for k in self.edge_map.keys():
            for d in self.edge_map[k]:
                spo_list = spo_list + d.to_spo_list()
                from_id_with_type = f"{d.from_type}_{d.from_id}"
                if from_id_with_type not in recored_ids and d.from_type != "attribute":
                    spo_list = spo_list + d.from_entity.to_spo_list()
                    recored_ids.append(from_id_with_type)

                end_id_with_type = f"{d.end_type}_{d.end_id}"
                if end_id_with_type not in recored_ids and d.end_type != "attribute":
                    spo_list = spo_list + d.end_entity.to_spo_list()
                    recored_ids.append(end_id_with_type)
        return spo_list

    def rmv_edge_ins(self, alias_name, alias_ins_set):
        if alias_name not in self.edge_map.keys():
            return
        update_rel_list = []
        for d in self.edge_map[alias_name]:
            if d not in alias_ins_set:
                update_rel_list.append(d)
        self.edge_map[alias_name] = update_rel_list

    def append_into_map(self, map: dict, key, value):
        old_list = []
        if key in map.keys():
            old_list = map[key]
        old_list.append(value)
        map[key] = old_list

    def rmv_node_ins(self, alias_name, alias_ins_set):
        if alias_name in self.entity_map.keys():
            entity_list = self.entity_map[alias_name]
            updated_entity_list = []
            for d in entity_list:
                if d.biz_id not in alias_ins_set:
                    updated_entity_list.append(d)
            self.entity_map[alias_name] = updated_entity_list

        # need generate with edge
        spo_set = self.get_all_relation_spo(alias_name)

        allowed_entity_dict = {}
        visited_p_dict = {}
        for s, p, o in spo_set:
            if p not in self.edge_map.keys():
                continue
            rel_list = []
            allowed_entity_dict[s.alias_name] = []
            allowed_entity_dict[o.alias_name] = []
            for rel in self.edge_map[p]:
                if (s.alias_name == alias_name and rel.from_id not in alias_ins_set) \
                        or (o.alias_name == alias_name and rel.end_id not in alias_ins_set):
                    rel_list.append(rel)
                    self.append_into_map(allowed_entity_dict, s.alias_name, rel.from_id)
                    self.append_into_map(allowed_entity_dict, o.alias_name, rel.end_id)
            self.edge_map[p] = rel_list
            visited_p_dict[p] = rel_list

        # 去除其余edge_map[p]中在filtered_entity_dict中的边
        for p in self.edge_map.keys():
            if p in visited_p_dict.keys():
                continue
            rel_list = []
            spo = self.query_graph[p]
            allowed_s = None
            allowed_o = None
            if spo["s"] in allowed_entity_dict.keys():
                allowed_s = allowed_entity_dict[spo["s"]]
            if spo["o"] in allowed_entity_dict.keys():
                allowed_o = allowed_entity_dict[spo["o"]]

            for rel in self.edge_map[p]:
                if allowed_s is not None and rel.from_id not in allowed_s:
                    continue
                if allowed_o is not None and rel.end_id not in allowed_o:
                    continue
                rel_list.append(rel)
            self.edge_map[p] = rel_list

    def rmv_ins(self, alias_name, alias_ins_set):
        if len(alias_ins_set) == 0:
            return
        if alias_name in self.nodes_alias:
            self.rmv_node_ins(alias_name.alias_name, alias_ins_set)
        elif alias_name in self.edge_alias:
            self.rmv_edge_ins(alias_name.alias_name, alias_ins_set)

    def rmv_node_alias(self, alias):
        if alias not in self.nodes_alias:
            return
        self.entity_map.pop(alias)
        self.nodes_alias.remove(alias)

    def get_all_relation_spo(self, alias):
        res = []
        for p in self.query_graph.keys():
            spo = self.query_graph[p]
            if spo["o"] == alias or spo["s"] == alias:
                res.append((spo["s"], spo["p"], spo["o"]))
        return res

    def get_entity_by_alias(self, alias):
        if alias in self.nodes_alias:
            if alias in self.entity_map.keys():
                return self.entity_map[alias]
            else:
                # need generate with edge
                spo_set = self.get_all_relation_spo(alias)
                ret_entity = []
                for s, p, o in spo_set:
                    if p not in self.edge_map.keys():
                        continue
                    for rel in self.edge_map[p]:
                        if s == alias:
                            ret_entity.append(rel.from_entity)
                        if o == alias:
                            ret_entity.append(rel.end_entity)
                if len(ret_entity) == 0:
                    return None
                return ret_entity
        if alias in self.edge_map.keys():
            return self.edge_map[alias]
        return None

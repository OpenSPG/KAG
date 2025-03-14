

from ast import Dict
import json
from typing import List
from kag.builder.model.chunk import Chunk
from kag.builder.model.sub_graph import SubGraph
from kag.common.utils import processing_phrases
from kag.interface.builder.extractor_abc import ExtractorABC
from kag.builder.component.extractor.schema_free_extractor import SchemaFreeExtractor
from kag.interface.common.llm_client import LLMClient
from tenacity import retry, stop_after_attempt
import logging

from datetime import datetime, timezone, timedelta
import collections
logger = logging.getLogger(__name__)


entity_type_list = set(["组织", "地点", "人物", "体育", "法律", "产品", "政治人物", "娱乐人物", "科学家", "学者", "历史人物", "国家", "城市", "自然景观", "省", "县", "行政区域", "公司", "企业", "机构", "政府机构", "历史事件", "运动赛事", "文化活动", "绘画", "音乐", "文学作品", "电子产品", "食品", "服饰", "文化习俗", "体育项目", "运动员", "历史时期", "地形", "气候", "法律条款", "法律机构", "疾病", "医疗技术", "政策", "交通工具", "台风", "洪水", "地震", "飓风", "泥石", "雪崩", "自然灾害"])

def parser_one(d_one):
    d_one = d_one.strip().strip('"').strip("'").strip()
    for before_str, replace_str in {"[论元1]": "", "[触发词]": "", "[论元2]": ""}.items():
        d_one = d_one.replace(before_str, replace_str)
    res = d_one.split(':')[0].strip('"')
    if res in ["论元1", "触发词", "论元2"]:
        return ""
    return res

@ExtractorABC.register("event_extractor")
@ExtractorABC.register("event_extractor_3b")
class KAGEventExtractor3B(SchemaFreeExtractor):

    def __init__(self, llm: LLMClient, **kwargs):
        super().__init__(llm = llm,**kwargs)
        self.llm = llm

    def invoke(self, input, **kwargs):
        title = input.name
        passage = title + "\n" + input.content
        if input.type == 'DOC':
            return []
        try:
            chunk, entity_res, event_res = self.extract_one_doc(input)
            events = self.__event_extraction(event_res)
            entities = self.__named_entity_recognition(entity_res)
            sub_graph, entities = self.assemble_sub_graph_with_spg_records(entities)
            filtered_entities = [
                {k: v for k, v in ent.items() if k in ["entity", "category"]}
                for ent in entities
            ]
            # triples = self.triples_extraction(passage, filtered_entities)
            triples = []
            sub_graph = self.__assemble_sub_graph(
                sub_graph, input, entities, triples, events
            )
            for node in sub_graph.nodes:
                if node.label == "Event":
                    node.properties["name"] = node.name
                    node.properties["id"] = node.id
                    node.properties["trunk_content"] = passage

                if node.label == 'Chunk':
                    node.properties['pid'] = node.id.split('_')[0]
            return [sub_graph]
        except Exception as e:
            logger.info(e)
            sub_graph = SubGraph([], [])
            sub_graph.add_node(
                input.id,
                input.name,
                'Chunk',
                {
                    "id": input.id,
                    "name": input.name,
                    "content": input.content,
                    'pid': input.id.split('_')[0]
                },
            )
            return [sub_graph]



    def get_entity_type(self,entity, content):
        features = {
            "messages": [
                {
                    "role": "user",
                    "content": json.dumps({"instruction": f"请为内容\n"
                                                          f"{entity}"
                                                          f"\n 选择合适的类别标签，结合候选标签类型输出唯一匹配的标签，如果没有匹配的标签就输出'Others', 不需要推理结果,直接给结论",
                                        #"input": content,
                                        "候选类型标签": "，".join(list(entity_type_list))}, ensure_ascii=False)
                }
            ],
            "temperature": 0,
            "source_token": "xj169860"
        }
        if hasattr(self.llm, "_client"):
            result = self.llm.client.call_service(features, debug=False) 
        else:
            result = self.llm(features["messages"][0]["content"])
        try:
            #res_type = json.loads(result[0]["res"])["answer"]
            res_type = result
        except Exception as e:
            res_type = ""

        #if res_type not in entity_type_list:
        #    return "Others"
        return res_type

    def get_event_extract_result(self,content):
        content = content.replace("\n", "")
        features = {
            "messages": [
                {
                    "role": "user",
                    "content": f"""你是一个专门执行开放式信息抽取（OpenIE）的专家。帮我分析下文，并提取出其中的事件(包括论元1、触发词、论元2)；请用("论元1":论元1, "触发词":触发词, "论元2":论元2)\n的结构来表示，若无相应事件则留空。返回结果必须为可解析的json格式\n\n{content}""",
                    # "content":content,
                }
            ],
            "temperature": 0,
            "source_token": "xj169860"
        }
        if hasattr(self.llm, "_client"):
            result = self.llm.client.call_service(features, debug=False)
        else:
            result = self.llm(features["messages"][0]["content"])
        if not result:
            return None
        # 解析结果
        events = []
        # print("===", result[0]["res"])
        result_triple = json.loads(result.replace('```json', '').replace('```', ''))
        for one in result_triple:
            if len(one) != 3:
                continue
            subject = one["论元1"]
            trigger = one["触发词"]
            object = one["论元2"]
            if not trigger:
                continue
            # print(f"<{subject}, {trigger}, {object}>")
            events.append([subject, trigger, object, content])
        '''
        r_arr = result[0]["res"].split("\n")
        for one in r_arr:
            one = one.strip('(\\"').strip('])').strip(']')
            arr = one.split(',')
            if len(arr) != 3:
                continue
            subject = parser_one(arr[0])
            trigger = parser_one(arr[1])
            object = parser_one(arr[2])
            if not trigger:
                continue
            # print(f"<{subject}, {trigger}, {object}>")
            events.append([subject, trigger, object, content])
        '''
        return events


    def extract_one_doc(self,chunk):
        events = []
        event_res = self.get_event_extract_result(chunk.content)
        events.extend(event_res)

        # 去重和过滤垃圾
        event_map, entitys = {}, {}
        for event in events:
            if not event[0] and not event[2]:
                continue
            key = f"<{event[0]}, {event[1]}, {event[2]}>"
            if key in event_map:
                continue
            if event[0] and event[0] not in entitys:
                entitys[event[0]] = event[3]
            if event[2] and event[2] not in entitys:
                entitys[event[2]] = event[3]
            event_map[key] = event
        # print(f"before {len(events)} after {len(event_map)}")

        entity_type_map = {}
        event_res = []
        for entity, entity_content in entitys.items():
            entity_type = self.get_entity_type(entity, entity_content)
            entity_type_map[entity] = entity_type

        for event in events:
            sub_type, obj_type = "", ""
            if event[0]:
                sub_type = entity_type_map[event[0]]
            if event[2]:
                obj_type = entity_type_map[event[2]]
            event_res.append(
                {"subName": event[0], "subType": sub_type, "pName": event[1], "objName": event[2], "objType": obj_type})
        entity_res = [{"id": e, "name": e, "entityType": e_type} for e, e_type in entity_type_map.items()]
        return chunk, entity_res, event_res

    @retry(stop=stop_after_attempt(3))
    def __event_extraction(self,event_res):
        # return self.llm.invoke({"input": passage, "entity_list": []}, self.event_prompt)
        def convert_res_to_events(event_res):
            for event in event_res:
                event["pType"] = "pType"
            return event_res
        return convert_res_to_events(event_res)
        

    def __named_entity_recognition(self, entity_res):
        # ner_result = self.llm.invoke({"input": content}, self.ner_prompt)
        # return ner_result
        def convert_res_to_entities(entity_res):
            res = []
            for entity in entity_res:
                ent = {}
                ent['entity'] = entity['id']
                ent['name'] = entity['name']
                ent['category'] = entity['entityType']
                res.append(ent)
            return res
        return convert_res_to_entities(entity_res)

    def __assemble_sub_graph(
        self,
        sub_graph: SubGraph,
        chunk: Chunk,
        entities: List[Dict],
        triples: List[list],
        events: List[Dict],
    ):
        self.assemble_sub_graph_with_entities(sub_graph, entities)
        self.assemble_sub_graph_with_triples(sub_graph, entities, triples)
        self.__assemble_sub_graph_with_events(sub_graph, entities, events, chunk)
        self.assemble_sub_graph_with_chunk(sub_graph, chunk)
        return sub_graph

    def __assemble_sub_graph_with_events(
            self,
            sub_graph: SubGraph,
            entities: List[Dict],
            events: List[Dict],
            chunk: Chunk,
        ):
            for event in events:
                if len(event) < 3:
                    continue
                event["subName"] = processing_phrases(event["subName"])
                s_category = "Entity"
                o_category = "Event"
                event_node_id = (
                    event["subName"]
                    + "_"
                    + event["subType"]
                    + "_"
                    + event["pName"]
                    + "_"
                    + event["pType"]
                    + "_"
                    + event["objName"]
                    + "_"
                    + event["objType"]
                )
                event["subId"] = event["subName"]
                event["objId"] = event["objName"]
                event_name = event["subName"] + event["pName"] + event["objName"]
                sub_graph.add_node(event_node_id, event_name, o_category, event)
                sub_graph.add_edge(
                    event_node_id,
                    o_category,
                    "subId",
                    event["subId"],
                    s_category,
                )
                sub_graph.add_edge(
                    event_node_id,
                    o_category,
                    "objId",
                    event["objId"],
                    s_category,
                )
                sub_graph.add_edge(
                    event_node_id, 'Event', "sourceChunk", chunk.id, "Chunk"
                )
            return sub_graph

    def __get_category(self, entities_data, entity_name):
        for entity in entities_data:
            if entity["entity"] == entity_name:
                return entity["category"]
        return None

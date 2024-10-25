#
# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import json
import logging
import re
from abc import ABC
from typing import List, Dict, Any
from collections import defaultdict

from knext.schema.model.schema_helper import SPGTypeName
from kag.builder.model.spg_record import SPGRecord
from kag.builder.prompt.spg_prompt import SPGPrompt
import uuid

logger = logging.getLogger(__name__)


class OneKEPrompt(SPGPrompt, ABC):
    template_zh: str = ""
    template_en: str = ""

    def __init__(self, **kwargs):
        types_list = kwargs.get("types_list", [])
        language = kwargs.get("language", "zh")
        with_description = kwargs.get("with_description", False)
        split_num = kwargs.get("split_num", 4)
        super().__init__(types_list, **kwargs)
        self.language = language
        if language == "zh":
            self.template = self.template_zh
        else:
            self.template = self.template_en
        self.with_description = with_description
        self.split_num = split_num

        self._init_render_variables()
        self._render()

        self.params = kwargs

    def build_prompt(self, variables: Dict[str, str]) -> List[str]:
        instructions = []
        for schema in self.schema_list:
            instructions.append(
                json.dumps(
                    {
                        "instruction": self.template,
                        "schema": schema,
                        "input": variables.get("input"),
                    },
                    ensure_ascii=False,
                )
            )
        return instructions

    def parse_response(self, response: str) -> List[SPGRecord]:
        raise NotImplementedError

    def _render(self):
        raise NotImplementedError

    def multischema_split_by_num(self, split_num, schemas: List[Any]):
        negative_length = max(len(schemas) // split_num, 1) * split_num
        total_schemas = []
        for i in range(0, negative_length, split_num):
            total_schemas.append(schemas[i : i + split_num])

        remain_len = max(1, split_num // 2)
        tmp_schemas = schemas[negative_length:]
        if len(schemas) - negative_length >= remain_len and len(tmp_schemas) > 0:
            total_schemas.append(tmp_schemas)
        elif len(tmp_schemas) > 0:
            total_schemas[-1].extend(tmp_schemas)
        return total_schemas


class OneKE_NERPrompt(OneKEPrompt):
    template_zh: str = (
        "你是专门进行实体抽取的专家。请从input中抽取出符合schema定义的实体，不存在的实体类型返回空列表。请按照JSON字符串的格式回答。"
    )
    template_en: str = "You are an expert in named entity recognition. Please extract entities that match the schema definition from the input. Return an empty list if the entity type does not exist. Please respond in the format of a JSON string."

    def __init__(
        self,
        entity_types: List[SPGTypeName],
        language: str = "zh",
        with_description: bool = False,
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(
            types_list=entity_types,
            language=language,
            with_description=with_description,
            split_num=split_num,
            **kwargs,
        )

    def parse_response(self, response: str) -> List[SPGRecord]:
        if isinstance(response, list) and len(response) > 0:
            response = response[0]
        try:
            ent_obj = json.loads(response)
        except json.decoder.JSONDecodeError:
            logger.error("OneKE_NERPrompt response JSONDecodeError error.")
            return []
        if type(ent_obj) != dict:
            logger.error("OneKE_NERPrompt response type error.")
            return []

        spg_records = []
        for type_zh, values in ent_obj.items():
            if type_zh not in self.spg_type_schema_info_zh:
                logger.warning(f"Unrecognized entity_type: {type_zh}")
                continue
            type_en, _ = self.spg_type_schema_info_zh[type_zh]
            for value in values:
                spg_record = SPGRecord(type_en)
                spg_record.upsert_properties({"id": value, "name": value})
                spg_records.append(spg_record)
        return spg_records

    def _render(self):
        entity_list = []
        for spg_type in self.spg_types:
            entity_list.append(spg_type.name_zh)
        self.schema_list = self.multischema_split_by_num(self.split_num, entity_list)


class OneKE_SPOPrompt(OneKEPrompt):
    template_zh: str = (
        "你是专门进行SPO三元组抽取的专家。请从input中抽取出符合schema定义的spo关系三元组，不存在的关系返回空列表。请按照JSON字符串的格式回答。"
    )
    template_en: str = "You are an expert in spo(subject, predicate, object) triples extraction. Please extract SPO relationship triples that match the schema definition from the input. Return an empty list for relationships that do not exist. Please respond in the format of a JSON string."

    def __init__(
        self,
        spo_types: List[SPGTypeName],
        language: str = "zh",
        with_description: bool = False,
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(
            types_list=spo_types,
            language=language,
            with_description=with_description,
            split_num=split_num,
            **kwargs,
        )
        self.properties_mapper = {}
        self.relations_mapper = {}

    def parse_response(self, response: str) -> List[SPGRecord]:
        if isinstance(response, list) and len(response) > 0:
            response = response[0]
        try:
            re_obj = json.loads(response)
        except json.decoder.JSONDecodeError:
            logger.error("OneKE_REPrompt response JSONDecodeError error.")
            return []
        if type(re_obj) != dict:
            logger.error("OneKE_REPrompt response type error.")
            return []

        relation_dcir = defaultdict(list)
        for relation_zh, values in re_obj.items():
            if relation_zh not in self.property_info_zh[relation_zh]:
                logger.warning(f"Unrecognized relation: {relation_zh}")
                continue
            if values and isinstance(values, list):
                for value in values:
                    if (
                        type(value) != dict
                        or "subject" not in value
                        or "object" not in value
                    ):
                        logger.warning("OneKE_REPrompt response type error.")
                        continue
                    s_zh, o_zh = value.get("subject", ""), value.get("object", "")
                    relation_dcir[relation_zh].append((s_zh, o_zh))

        spg_records = []
        for relation_zh, sub_obj_list in relation_dcir.items():
            sub_dict = defaultdict(list)
            for s_zh, o_zh in sub_obj_list:
                sub_dict[s_zh].append(o_zh)
            for s_zh, o_list in sub_dict.items():
                if s_zh in self.spg_type_schema_info_zh:
                    logger.warning(f"Unrecognized subject_type: {s_zh}")
                    continue
                object_value = ",".join(o_list)
                s_type_zh = self.properties_mapper.get(relation_zh, None)
                if s_type_zh is not None:
                    s_type_en, _ = self.spg_type_schema_info_zh[s_type_zh]
                    relation_en, _ = self.property_info_zh[relation_zh]
                    spg_record = SPGRecord(s_type_en).upsert_properties(
                        {"id": s_zh, "name": s_zh}
                    )
                    spg_record.upsert_property(relation_en, object_value)
                else:
                    s_type_zh, o_type_zh = self.relations_mapper.get(
                        relation_zh, [None, None]
                    )
                    if s_type_zh is None or o_type_zh is None:
                        logger.warning(f"Unrecognized relation: {relation_zh}")
                        continue
                    s_type_en, _ = self.spg_type_schema_info_zh[s_type_zh]
                    spg_record = SPGRecord(s_type_en).upsert_properties(
                        {"id": s_zh, "name": s_zh}
                    )
                    relation_en, _, object_type = self.relation_info_zh[s_type_zh][
                        relation_zh
                    ]
                    spg_record.upsert_relation(relation_en, object_type, object_value)
                spg_records.append(spg_record)
        return spg_records

    def _render(self):
        spo_list = []
        for spg_type in self.spg_types:
            type_en, _ = self.spg_type_schema_info_zh[spg_type]
            for v in spg_type.properties.values():
                spo_list.append(
                    {
                        "subject_type": spg_type.name_zh,
                        "predicate": v.name_zh,
                        "object_type": "文本",
                    }
                )
                self.properties_mapper[v.name_zh] = spg_type
            for v in spg_type.relations.values():
                _, _, object_type = self.relation_info_en[type_en][v.name]
                spo_list.append(
                    {
                        "subject_type": spg_type.name_zh,
                        "predicate": v.name_zh,
                        "object_type": object_type,
                    }
                )
                self.relations_mapper[v.name_zh] = [spg_type, object_type]
        self.schema_list = self.multischema_split_by_num(self.split_num, spo_list)


class OneKE_REPrompt(OneKE_SPOPrompt):
    template_zh: str = (
        "你是专门进行关系抽取的专家。请从input中抽取出符合schema定义的关系三元组，不存在的关系返回空列表。请按照JSON字符串的格式回答。"
    )
    template_en: str = "You are an expert in relationship extraction. Please extract relationship triples that match the schema definition from the input. Return an empty list for relationships that do not exist. Please respond in the format of a JSON string."

    def __init__(
        self,
        relation_types: List[SPGTypeName],
        language: str = "zh",
        with_description: bool = False,
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(
            relation_types, language, with_description, split_num, **kwargs
        )

    def _render(self):
        re_list = []
        for spg_type in self.spg_types:
            type_en, _ = self.spg_type_schema_info_zh[spg_type]
            for v in spg_type.properties.values():
                re_list.append(v.name_zh)
                self.properties_mapper[v.name_zh] = spg_type
            for v in spg_type.relations.values():
                v_zh, _, object_type = self.relation_info_en[type_en][v.name]
                re_list.append(v.name_zh)
                self.relations_mapper[v.name_zh] = [spg_type, object_type]
        self.schema_list = self.multischema_split_by_num(self.split_num, re_list)


class OneKE_KGPrompt(OneKEPrompt):
    template_zh: str = "你是一个图谱实体知识结构化专家。根据输入实体类型(entity type)的schema描述，从文本中抽取出相应的实体实例和其属性信息，不存在的属性不输出, 属性存在多值就返回列表，并输出为可解析的json格式。"
    template_en: str = "You are an expert in structured knowledge systems for graph entities. Based on the schema description of the input entity type, you extract the corresponding entity instances and their attribute information from the text. Attributes that do not exist should not be output. If an attribute has multiple values, a list should be returned. The results should be output in a parsable JSON format."

    def __init__(
        self,
        entity_types: List[SPGTypeName],
        language: str = "zh",
        with_description: bool = False,
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(
            types_list=entity_types,
            language=language,
            with_description=with_description,
            split_num=split_num,
            **kwargs,
        )

    def parse_response(self, response: str) -> List[SPGRecord]:
        if isinstance(response, list) and len(response) > 0:
            response = response[0]
        try:
            re_obj = json.loads(response)
        except json.decoder.JSONDecodeError:
            logger.error("OneKE_KGPrompt response JSONDecodeError error.")
            return []
        if type(re_obj) != dict:
            logger.error("OneKE_KGPrompt response type error.")
            return []

        spg_records = []
        for type_zh, type_value in re_obj.items():
            if type_zh not in self.spg_type_schema_info_zh:
                logger.warning(f"Unrecognized entity_type: {type_zh}")
                continue
            type_en, _ = self.spg_type_schema_info_zh[type_zh]
            if type_value and isinstance(type_value, dict):
                for name, attrs in type_value.items():
                    spg_record = SPGRecord(type_en).upsert_properties(
                        {"id": name, "name": name}
                    )
                    for attr_zh, attr_value in attrs.items():
                        if isinstance(attr_value, list):
                            attr_value = ",".join(attr_value)
                        if attr_zh in self.property_info_zh[type_zh]:
                            attr_en, _, object_type = self.property_info_zh[type_zh][
                                attr_zh
                            ]
                            spg_record.upsert_property(attr_en, attr_value)
                        elif attr_zh in self.relation_info_zh[type_zh]:
                            attr_en, _, object_type = self.relation_info_zh[type_zh][
                                attr_zh
                            ]
                            spg_record.upsert_relation(attr_en, object_type, attr_value)
                        else:
                            logger.warning(f"Unrecognized attribute: {attr_zh}")
                            continue
                        if object_type == "Integer":
                            matches = re.findall(r"\d+", attr_value)
                            if matches:
                                spg_record.upsert_property(attr_en, matches[0])
                        elif object_type == "Float":
                            matches = re.findall(r"\d+(?:\.\d+)?", attr_value)
                            if matches:
                                spg_record.upsert_property(attr_en, matches[0])
                    spg_records.append(spg_record)
        return spg_records

    def _render(self):
        spo_list = []
        for spg_type in self.spg_types:
            if not self.with_description:
                attributes = []
                attributes.extend(
                    [
                        v.name_zh
                        for k, v in spg_type.properties.items()
                        if k not in self.ignored_properties
                    ]
                )
                attributes.extend(
                    [
                        v.name_zh
                        for k, v in spg_type.relations.items()
                        if v.name_zh not in attributes
                        and k not in self.ignored_relations
                    ]
                )
            else:
                attributes = {}
                attributes.update(
                    {
                        v.name_zh: v.desc or ""
                        for k, v in spg_type.properties.items()
                        if k not in self.ignored_properties
                    }
                )
                attributes.update(
                    {
                        v.name_zh: v.desc or ""
                        for k, v in spg_type.relations.items()
                        if v.name_zh not in attributes
                        and k not in self.ignored_relations
                    }
                )
            entity_type = spg_type.name_zh
            spo_list.append({"entity_type": entity_type, "attributes": attributes})

        self.schema_list = self.multischema_split_by_num(self.split_num, spo_list)


class OneKE_EEPrompt(OneKEPrompt):
    template_zh: str = "你是专门进行事件提取的专家。请从input中抽取出符合schema定义的事件，不存在的事件返回空列表，不存在的论元返回NAN，如果论元存在多值请返回列表。请按照JSON字符串的格式回答。"
    template_en: str = "You are an expert in event extraction. Please extract events from the input that conform to the schema definition. Return an empty list for events that do not exist, and return NAN for arguments that do not exist. If an argument has multiple values, please return a list. Respond in the format of a JSON string."

    def __init__(
        self,
        event_types: List[SPGTypeName],
        language: str = "zh",
        with_description: bool = False,
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(
            types_list=event_types,
            language=language,
            with_description=with_description,
            split_num=split_num,
            **kwargs,
        )

    def parse_response(self, response: str) -> List[SPGRecord]:
        if isinstance(response, list) and len(response) > 0:
            response = response[0]
        try:
            ee_obj = json.loads(response)
        except json.decoder.JSONDecodeError:
            logger.error("OneKE_EEPrompt response JSONDecodeError error.")
            return []
        if type(ee_obj) != dict:
            logger.error("OneKE_EEPrompt response type error.")
            return []

        spg_records = []
        for type_zh, type_values in ee_obj.items():
            if type_zh not in self.spg_type_schema_info_zh:
                logger.warning(f"Unrecognized event_type: {type_zh}")
                continue
            type_en, _ = self.spg_type_schema_info_zh[type_zh]
            if type_values and isinstance(type_values, list):
                for type_value in type_values:
                    uuid_4 = uuid.uuid4()
                    spg_record = (
                        SPGRecord(type_en)
                        .upsert_property("id", str(uuid_4))
                        .upsert_property("name", type_zh)
                    )
                    arguments = type_value.get("arguments")
                    if arguments and isinstance(arguments, dict):
                        for attr_zh, attr_value in arguments.items():
                            if isinstance(attr_value, list):
                                attr_value = ",".join(attr_value)
                            if attr_zh in self.property_info_zh[type_zh]:
                                attr_en, _, object_type = self.property_info_zh[
                                    type_zh
                                ][attr_zh]
                                spg_record.upsert_property(attr_en, attr_value)
                            elif attr_zh in self.relation_info_zh[type_zh]:
                                attr_en, _, object_type = self.relation_info_zh[
                                    type_zh
                                ][attr_zh]
                                spg_record.upsert_relation(
                                    attr_en, object_type, attr_value
                                )
                            else:
                                logger.warning(f"Unrecognized attribute: {attr_zh}")
                                continue
                            if object_type == "Integer":
                                matches = re.findall(r"\d+", attr_value)
                                if matches:
                                    spg_record.upsert_property(attr_en, matches[0])
                            elif object_type == "Float":
                                matches = re.findall(r"\d+(?:\.\d+)?", attr_value)
                                if matches:
                                    spg_record.upsert_property(attr_en, matches[0])
                    spg_records.append(spg_record)
        return spg_records

    def _render(self):
        event_list = []
        for spg_type in self.spg_types:
            if not self.with_description:
                arguments = []
                arguments.extend(
                    [
                        v.name_zh
                        for k, v in spg_type.properties.items()
                        if k not in self.ignored_properties
                    ]
                )
                arguments.extend(
                    [
                        v.name_zh
                        for k, v in spg_type.relations.items()
                        if v.name_zh not in arguments
                        and k not in self.ignored_relations
                    ]
                )
            else:
                arguments = {}
                arguments.update(
                    {
                        v.name_zh: v.desc or ""
                        for k, v in spg_type.properties.items()
                        if k not in self.ignored_properties
                    }
                )
                arguments.update(
                    {
                        v.name_zh: v.desc or ""
                        for k, v in spg_type.relations.items()
                        if v.name_zh not in arguments
                        and k not in self.ignored_relations
                    }
                )
            event_type = spg_type.name_zh
            event_list.append(
                {"event_type": event_type, "trigger": True, "arguments": arguments}
            )
        self.schema_list = self.multischema_split_by_num(self.split_num, event_list)

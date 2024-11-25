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
from typing import List, Dict

from kag.common.base.prompt_op import PromptOp
from kag.schema.client import SchemaClient
from kag.schema.model.base import BaseSpgType
from kag.schema.model.schema_helper import SPGTypeName
from kag.builder.model.spg_record import SPGRecord

logger = logging.getLogger(__name__)


class SPGPrompt(PromptOp, ABC):
    spg_types: Dict[str, BaseSpgType]
    ignored_types: List[str] = ["Chunk"]
    ignored_properties: List[str] = ["id", "name", "description", "stdId", "eventTime"]
    ignored_relations: List[str] = ["isA"]
    basic_types = {"Text": "文本", "Integer": "整型", "Float": "浮点型"}

    def __init__(
        self,
        spg_type_names: List[SPGTypeName],
        language: str = "zh",
        split_num: int = 4,
        **kwargs,
    ):
        super().__init__(language=language)
        schema_types = SchemaClient().load()
        self.spg_type_names = spg_type_names
        if not spg_type_names:
            self.spg_types = schema_types
        else:
            self.spg_types = {k: v for k, v in schema_types.items() if k in spg_type_names}
        self.schema_list = []
        self.split_num = split_num

        self._init_render_variables()
        self.params = kwargs

    @property
    def template_variables(self) -> List[str]:
        return []

    def _init_render_variables(self):
        self.property_info_zh = {}
        self.property_info_en = {}
        self.relation_info_zh = {}
        self.relation_info_en = {}
        self.spg_type_schema_info_en = {
            "Text": ("文本", None),
            "Integer": ("整型", None),
            "Float": ("浮点型", None),
        }
        self.spg_type_schema_info_zh = {
            "文本": ("Text", None),
            "整型": ("Integer", None),
            "浮点型": ("Float", None),
        }
        for type_name, spg_type in self.spg_types.items():
            self.property_info_zh[spg_type.name_zh] = {}
            self.relation_info_zh[spg_type.name_zh] = {}
            self.property_info_en[type_name] = {}
            self.relation_info_en[type_name] = {}
            for _rel in spg_type.relations.values():
                if _rel.is_dynamic:
                    continue
                self.relation_info_zh[spg_type.name_zh][_rel.name_zh] = (
                    _rel.name,
                    _rel.desc,
                    _rel.object_type_name_en,
                )
                self.relation_info_en[type_name][_rel.name] = (
                    _rel.name_zh,
                    _rel.desc,
                    _rel.object_type_name_zh,
                )
            for _prop in spg_type.properties.values():
                self.property_info_zh[spg_type.name_zh][_prop.name_zh] = (
                    _prop.name,
                    _prop.desc,
                    _prop.object_type_name_en,
                )
                self.property_info_en[type_name][_prop.name] = (
                    _prop.name_zh,
                    _prop.desc,
                    _prop.object_type_name_zh,
                )
        for _name, _type in self.spg_types.items():
            self.spg_type_schema_info_zh[_type.name_zh] = (_name, _type.desc)
            self.spg_type_schema_info_en[_name] = (_type.name_zh, _type.desc)

    def _render(self):
        raise NotImplementedError


class SPG_KGPrompt(SPGPrompt):
    template_zh: str = """你是一个图谱知识抽取的专家, 基于constraint 定义的schema，从input 中抽取出所有的实体及其属性，input中未明确提及的属性返回NAN，以标准json 格式输出，结果返回list"""
    template_en: str = """You are an expert in knowledge graph extraction. Based on the schema defined by the constraint, extract all entities and their attributes from the input. Return NAN for attributes not explicitly mentioned in the input. Output the results in standard JSON format, as a list."""

    def __init__(
        self,
        spg_type_names: List[SPGTypeName],
        language: str = "zh",
        split_num: int = 4,
        project_id: int = None,
    ):
        super().__init__(
            spg_type_names=spg_type_names,
            language=language,
            split_num=split_num,
            project_id=project_id,
        )
        self._render()

    def build_prompt(self, variables: Dict[str, str]) -> List[str]:
        instructions = []
        for schema in self.schema_list:
            instructions.append(
                json.dumps(
                    {
                        "instruction": self.template,
                        "constraint": schema,
                        "input": variables.get("input"),
                    },
                    ensure_ascii=False,
                )
            )
        return instructions

    def parse_response(self, response: str, **kwargs) -> List[SPGRecord]:
        types = kwargs.get("types", [])
        idx = kwargs.get("idx", 0)
        type_en = types[idx]
        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.decoder.JSONDecodeError:
                logger.error("SPG_KGPrompt response JSONDecodeError error.")
                return []
        if type(response) != list:
            logger.error("SPG_KGPrompt response type error.")
            return []

        standard_response = []
        spg_records = []
        object_spg_records = []
        for type_value in response:
            if (
                isinstance(type_value, dict)
                and len(type_value) == 1
                and type_en in type_value
            ):
                if "properties" in type_value[type_en]:
                    properties = type_value[type_en]["properties"]
                else:
                    properties = type_value[type_en]
            else:
                properties = type_value
            standard_properties = {}
            for prop_name, prop_value in properties.items():
                if not prop_value or prop_value == "NAN":
                    continue
                if isinstance(prop_value, list):
                    prop_value = ",".join(prop_value)
                prop_value = (
                    prop_value.replace("《", "").replace("》", "").replace("'", "`")
                )
                standard_properties[prop_name] = prop_value
            standard_response.append(standard_properties)
        for type_value in standard_response:
            for attr_en, attr_value in type_value.items():
                if attr_en in self.property_info_en[type_en]:
                    _, _, object_type = self.property_info_en[type_en].get(attr_en)
                    if object_type not in self.basic_types:
                        if isinstance(attr_value, list):
                            attr_value = ",".join(attr_value)
                        attr_value = re.split("[,，、;；]", attr_value)
                        for _value in attr_value:
                            object_spg_records.append(
                                SPGRecord(object_type).upsert_properties(
                                    {"name": _value}
                                )
                            )
                        type_value[attr_en] = ",".join(attr_value)
            _dict = {"spgTypeName": type_en, "properties": type_value}
            spg_record = SPGRecord.from_dict(_dict)
            spg_records.append(spg_record)
        return spg_records + object_spg_records

    def _render(self):
        spo_list = []
        for type_name, spg_type in self.spg_types.items():
            constraint = {
                "desc": (
                    f"{spg_type.name_zh}"
                    if not spg_type.desc
                    else f"{spg_type.name_zh}，{spg_type.desc}"
                ) if self.language == "zh" else (
                    f"{type_name}"
                    if not spg_type.desc
                    else f"{type_name}, {spg_type.desc}"
                )
            }
            properties = {}
            properties.update(
                {
                    v.name: (f"{v.name_zh}" if not v.desc else f"{v.name_zh}，{v.desc}") if self.language == "zh" else (f"{v.name}" if not v.desc else f"{v.name}, {v.desc}")
                    for k, v in spg_type.properties.items()
                    if k not in self.ignored_properties
                }
            )
            properties.update(
                {
                    f"{v.name}#{v.object_type_name_en}": (
                        f"{v.name_zh}，类型是{v.object_type_name_zh}"
                        if not v.desc
                        else f"{v.name_zh}，{v.desc}，类型是{v.object_type_name_zh}"
                    ) if self.language == "zh" else (
                        f"{v.name}, the type is {v.object_type_name_en}"
                        if not v.desc
                        else f"{v.name}，{v.desc}, the type is {v.object_type_name_en}"
                    )
                    for k, v in spg_type.relations.items()
                    if not v.is_dynamic and k not in self.ignored_relations
                }
            )
            constraint.update({"properties": properties})
            spo_list.append({type_name: constraint})

        self.schema_list = spo_list


class SPG_EEPrompt(SPGPrompt):
    template_zh: str = "你是一个图谱知识抽取的专家, 基于constraint 定义的schema，从input 中抽取出所有的事件及其属性，input中未明确提及的属性返回NAN，以标准json 格式输出，结果返回list"
    template_en: str = "You are an expert in knowledge graph extraction. Based on the schema defined by the constraint, extract all events and their attributes from the input. Return NAN for attributes not explicitly mentioned in the input. Output the results in standard JSON format, as a list."

    def __init__(
        self,
        spg_type_names: List[SPGTypeName],
        language: str = "zh",
        split_num: int = 4,
        project_id: int = None,
    ):
        super().__init__(
            spg_type_names=spg_type_names,
            language=language,
            split_num=split_num,
            project_id=project_id,
        )
        self._render()

    def build_prompt(self, variables: Dict[str, str]) -> List[str]:
        instructions = []
        for schema in self.schema_list:
            instructions.append(
                json.dumps(
                    {
                        "instruction": self.template,
                        "constraint": schema,
                        "input": variables.get("input"),
                    },
                    ensure_ascii=False,
                )
            )
        return instructions

    def parse_response(self, response: str, **kwargs) -> List[SPGRecord]:
        types = kwargs.get("types", [])
        idx = kwargs.get("idx", 0)
        type_en = types[idx]

        if isinstance(response, str):
            try:
                response = json.loads(response)
            except json.decoder.JSONDecodeError:
                logger.error("SPG_EEPrompt response JSONDecodeError error.")
                return []
        if type(response) != list:
            logger.error("SPG_EEPrompt response type error.")
            return []

        standard_response = []
        spg_records = []
        object_spg_records = []
        for type_value in response:
            if (
                isinstance(type_value, dict)
                and len(type_value) == 1
                and type_en in type_value
            ):
                if "properties" in type_value[type_en]:
                    properties = type_value[type_en]["properties"]
                else:
                    properties = type_value[type_en]
            else:
                properties = type_value
            standard_properties = {}
            for prop_name, prop_value in properties.items():
                if not prop_value or prop_value == "NAN":
                    continue
                if isinstance(prop_value, list):
                    prop_value = ",".join(prop_value)
                prop_value = (
                    prop_value.replace("《", "").replace("》", "").replace("'", "`")
                )
                standard_properties[prop_name] = prop_value
            standard_response.append(standard_properties)
        for type_value in standard_response:
            for attr_en, attr_value in type_value.items():
                if attr_en in self.property_info_en[type_en]:
                    _, _, object_type = self.property_info_en[type_en].get(attr_en)
                    if object_type not in self.basic_types:
                        if isinstance(attr_value, list):
                            attr_value = ",".join(attr_value)
                        attr_value = re.split("[,，、;；]", attr_value)
                        for _value in attr_value:
                            object_spg_records.append(
                                SPGRecord(object_type).upsert_properties(
                                    {"name": _value}
                                )
                            )
                        type_value[attr_en] = ",".join(attr_value)
            type_zh, _ = self.spg_type_schema_info_en[type_en]
            sub_type = type_value.get("eventType", "")
            event_summary = type_value.get("eventSummary", "")
            type_value["name"] = f"{type_zh}-{sub_type}-{event_summary}" if self.language == "zh" else f"{type_en}-{sub_type}-{event_summary}"
            _dict = {"spgTypeName": type_en, "properties": type_value}
            spg_record = SPGRecord.from_dict(_dict)
            spg_records.append(spg_record)
        return spg_records + object_spg_records

    def _render(self):
        event_list = []
        for type_name, spg_type in self.spg_types.items():
            constraint = {
                "desc": (
                    f"{spg_type.name_zh}"
                    if not spg_type.desc
                    else f"{spg_type.name_zh}，{spg_type.desc}"
                ) if self.language == "zh" else (
                    f"{type_name}"
                    if not spg_type.desc
                    else f"{type_name}, {spg_type.desc}"
                )
            }
            properties = {}
            properties.update(
                {
                    v.name: (f"{v.name_zh}" if not v.desc else f"{v.name_zh}，{v.desc}")  if self.language == "zh" else (f"{v.name}" if not v.desc else f"{v.name}, {v.desc}")
                    for k, v in spg_type.properties.items()
                    if k not in self.ignored_properties
                }
            )
            properties.update(
                {
                    f"{v.name}#{v.object_type_name_en}": (
                        f"{v.name_zh}，类型是{v.object_type_name_zh}"
                        if not v.desc
                        else f"{v.name_zh}，{v.desc}，类型是{v.object_type_name_zh}"
                    ) if self.language == "zh" else (
                        f"{v.name}, the type is {v.object_type_name_en}"
                        if not v.desc
                        else f"{v.name}, {v.desc}, the type is {v.object_type_name}"
                    )
                    for k, v in spg_type.relations.items()
                    if not v.is_dynamic
                }
            )
            constraint.update({"properties": properties})
            event_list.append({type_name: constraint})
        self.schema_list = event_list

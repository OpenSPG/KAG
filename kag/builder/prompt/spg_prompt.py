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
from abc import ABC
from typing import List, Dict

from kag.common.base.prompt_op import PromptOp
from knext.schema.client import SchemaClient
from knext.schema.model.base import BaseSpgType, SpgTypeEnum
from knext.schema.model.schema_helper import SPGTypeName
from kag.builder.model.spg_record import SPGRecord

logger = logging.getLogger(__name__)


class SPGPrompt(PromptOp, ABC):
    spg_types: Dict[str, BaseSpgType]
    ignored_types: List[str] = ["Chunk"]
    ignored_properties: List[str] = ["id", "name", "description", "stdId", "eventTime", "desc", "semanticType"]
    ignored_relations: List[str] = ["isA"]
    basic_types = {"Text": "文本", "Integer": "整型", "Float": "浮点型"}

    def __init__(
        self,
        spg_type_names: List[SPGTypeName],
        language: str = "zh",
        **kwargs,
    ):
        super().__init__(language=language, **kwargs)
        self.all_schema_types = SchemaClient(project_id=self.project_id).load()
        self.spg_type_names = spg_type_names
        if not spg_type_names:
            self.spg_types = self.all_schema_types
        else:
            self.spg_types = {k: v for k, v in self.all_schema_types.items() if k in spg_type_names}
        self.schema_list = []

        self._init_render_variables()

    @property
    def template_variables(self) -> List[str]:
        return ["schema", "input"]

    def _init_render_variables(self):
        self.type_en_to_zh = {"Text": "文本", "Integer": "整型", "Float": "浮点型"}
        self.type_zh_to_en = {
            "文本": "Text",
            "整型": "Integer",
            "浮点型": "Float",
        }
        self.prop_en_to_zh = {}
        self.prop_zh_to_en = {}
        for type_name, spg_type in self.all_schema_types.items():
            self.type_en_to_zh[type_name] = spg_type.name_zh
            self.type_en_to_zh[spg_type.name_zh] = type_name
            self.prop_zh_to_en[type_name] = {}
            self.prop_en_to_zh[type_name] = {}
            for _prop in spg_type.properties.values():
                if _prop.name in self.ignored_properties:
                    continue
                self.prop_en_to_zh[type_name][_prop.name] = _prop.name_zh
                self.prop_zh_to_en[type_name][_prop.name_zh] = _prop.name
            for _rel in spg_type.relations.values():
                if _rel.is_dynamic:
                    continue
                self.prop_en_to_zh[type_name][_rel.name] = _rel.name_zh
                self.prop_zh_to_en[type_name][_rel.name_zh] = _rel.name

    def _render(self):
        raise NotImplementedError


class SPG_KGPrompt(SPGPrompt):
    template_zh: str = """
    {
        "instruction": "你是一个图谱知识抽取的专家, 基于constraint 定义的schema，从input 中抽取出所有的实体及其属性，input中未明确提及的属性返回NAN，以标准json 格式输出，结果返回list",
        "schema": $schema,
        "example": [
        {
            "input": "甲状腺结节是指在甲状腺内的肿块，可随吞咽动作随甲状腺而上下移动，是临床常见的病症，可由多种病因引起。临床上有多种甲状腺疾病，如甲状腺退行性变、炎症、自身免疫以及新生物等都可以表现为结节。甲状腺结节可以单发，也可以多发，多发结节比单发结节的发病率高，但单发结节甲状腺癌的发生率较高。患者通常可以选择在普外科，甲状腺外科，内分泌科，头颈外科挂号就诊。有些患者可以触摸到自己颈部前方的结节。在大多情况下，甲状腺结节没有任何症状，甲状腺功能也是正常的。甲状腺结节进展为其它甲状腺疾病的概率只有1%。有些人会感觉到颈部疼痛、咽喉部异物感，或者存在压迫感。当甲状腺结节发生囊内自发性出血时，疼痛感会更加强烈。治疗方面，一般情况下可以用放射性碘治疗，复方碘口服液(Lugol液)等，或者服用抗甲状腺药物来抑制甲状腺激素的分泌。目前常用的抗甲状腺药物是硫脲类化合物，包括硫氧嘧啶类的丙基硫氧嘧啶(PTU)和甲基硫氧嘧啶(MTU)及咪唑类的甲硫咪唑和卡比马唑。",
            "schema": {
                "Disease": {
                    "properties": {
                        "complication": "并发症",
                        "commonSymptom": "常见症状",
                        "applicableMedicine": "适用药品",
                        "department": "就诊科室",
                        "diseaseSite": "发病部位",
                    }
                },"Medicine": {
                    "properties": {
                    }
                }
            }
            "output": [
                {
                    "entity": "甲状腺结节",
                    "category":"Disease"
                    "properties": {
                        "complication": "甲状腺癌",
                        "commonSymptom": ["颈部疼痛", "咽喉部异物感", "压迫感"],
                        "applicableMedicine": ["复方碘口服液(Lugol液)", "丙基硫氧嘧啶(PTU)", "甲基硫氧嘧啶(MTU)", "甲硫咪唑", "卡比马唑"],
                        "department": ["普外科", "甲状腺外科", "内分泌科", "头颈外科"],
                        "diseaseSite": "甲状腺",
                    }
                },{
                    "entity":"复方碘口服液(Lugol液)",
                    "category":"Medicine"
                },{
                    "entity":"丙基硫氧嘧啶(PTU)",
                    "category":"Medicine"
                },{
                    "entity":"甲基硫氧嘧啶(MTU)",
                    "category":"Medicine"
                },{
                    "entity":"甲硫咪唑",
                    "category":"Medicine"
                },{
                    "entity":"卡比马唑",
                    "category":"Medicine"
                }
            ],
    "input": "$input"
    }
    """

    template_en: str = """
    {
        "instruction": "You are an expert in knowledge graph extraction. Based on the schema defined by constraints, extract all entities and their attributes from the input. For attributes not explicitly mentioned in the input, return NAN. Output the results in standard JSON format as a list.",
        "schema": $schema,
        "example": [
        {
            "input": "Thyroid nodules refer to lumps within the thyroid gland that can move up and down with swallowing, and they are a common clinical condition that can be caused by various etiologies. Clinically, many thyroid diseases, such as thyroid degeneration, inflammation, autoimmune conditions, and neoplasms, can present as nodules. Thyroid nodules can occur singly or in multiple forms; multiple nodules have a higher incidence than single nodules, but single nodules have a higher likelihood of being thyroid cancer. Patients typically have the option to register for consultation in general surgery, thyroid surgery, endocrinology, or head and neck surgery. Some patients can feel the nodules in the front of their neck. In most cases, thyroid nodules are asymptomatic, and thyroid function is normal. The probability of thyroid nodules progressing to other thyroid diseases is only about 1%. Some individuals may experience neck pain, a foreign body sensation in the throat, or a feeling of pressure. When spontaneous intracystic bleeding occurs in a thyroid nodule, the pain can be more intense. Treatment options generally include radioactive iodine therapy, Lugol's solution (a compound iodine oral solution), or antithyroid medications to suppress thyroid hormone secretion. Currently, commonly used antithyroid drugs are thiourea compounds, including propylthiouracil (PTU) and methylthiouracil (MTU) from the thiouracil class, and methimazole and carbimazole from the imidazole class.",
            "schema": {
                "Disease": {
                    "properties": {
                        "complication": "Disease",
                        "commonSymptom": "Symptom",
                        "applicableMedicine": "Medicine",
                        "department": "HospitalDepartment",
                        "diseaseSite": "HumanBodyPart"
                    }
                },"Medicine": {
                    "properties": {
                    }
                }
            }
            "output": [
                {
                    "entity": "Thyroid Nodule",
                    "category": "Disease",
                    "properties": {
                        "complication": "Thyroid Cancer",
                        "commonSymptom": ["Neck Pain", "Foreign Body Sensation in the Throat", "Feeling of Pressure"],
                        "applicableMedicine": ["Lugol's Solution (Compound Iodine Oral Solution)", "Propylthiouracil (PTU)", "Methylthiouracil (MTU)", "Methimazole", "Carbimazole"],\n            "department": ["General Surgery", "Thyroid Surgery", "Endocrinology", "Head and Neck Surgery"],\n            "diseaseSite": "Thyroid"\n        }\n    },\n    {\n        "entity": "Lugol's Solution (Compound Iodine Oral Solution)",
                    "category": "Medicine"
                },
                {
                    "entity": "Propylthiouracil (PTU)",
                    "category": "Medicine"
                },
                {
                    "entity": "Methylthiouracil (MTU)",
                    "category": "Medicine"
                },
                {
                    "entity": "Methimazole",
                    "category": "Medicine"
                },
                {
                    "entity": "Carbimazole",
                    "category": "Medicine"
                }
            ],
    "input": "$input"
    }
    """

    def __init__(
        self,
        spg_type_names: List[SPGTypeName],
        language: str = "zh",
        **kwargs
    ):
        super().__init__(
            spg_type_names=spg_type_names,
            language=language,
            **kwargs
        )
        self._render()

    def build_prompt(self, variables: Dict[str, str]) -> str:
        schema = {}
        for tmpSchema in self.schema_list:
            schema.update(tmpSchema)

        return super().build_prompt({"schema": schema, "input": variables.get("input")})

    def parse_response(self, response: str, **kwargs) -> List[SPGRecord]:
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            rsp = rsp["output"]
        if isinstance(rsp, dict) and "named_entities" in rsp:
            entities = rsp["named_entities"]
        else:
            entities = rsp

        return entities

    def _render(self):
        spo_list = []
        for type_name, spg_type in self.spg_types.items():
            if spg_type.spg_type_enum not in [SpgTypeEnum.Entity, SpgTypeEnum.Concept, SpgTypeEnum.Event]:
                continue
            constraint = {}
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

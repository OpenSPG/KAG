# -*- coding: utf-8 -*-
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

import re

from kag.schema import rest
from kag.schema.client import SchemaClient
from kag.schema.model.base import SpgTypeEnum


class SPGConceptRuleMarkLang:
    """
    SPG Concept Rule Mark Language Parser
    Feature: parse rule script and then alter the schema of project
    """

    namespace = None
    rule_quote_open = False
    rule_text = ""
    src_concept = ()
    dst_concept = ()

    def __init__(self, filename):
        self.current_line_num = 0
        self.session = SchemaClient().create_session()
        self.concept_client = rest.ConceptApi()
        self.load_script(filename)

    def error_msg(self, msg):
        return f"Line# {self.current_line_num}: {msg}"

    def parse_concept(self, expression):
        """
        parse the concept definition
        """

        namespace_match = re.match(r"^namespace\s+([a-zA-Z0-9]+)$", expression)
        if namespace_match:
            assert self.namespace is None, self.error_msg(
                "Duplicated namespace define, please ensure define it only once"
            )

            self.namespace = namespace_match.group(1)
            return

        type_match = re.match(
            r"^`([a-zA-Z0-9\.]+)`/`([^`]+)`:(\s*?([a-zA-Z0-9\.]+)/`([^`]+)`)?$",
            expression,
        )
        if type_match:
            assert self.namespace is not None, self.error_msg(
                "please define namespace first"
            )

            self.src_concept = (type_match.group(1), type_match.group(2))
            if len(type_match.groups()) > 4:
                self.dst_concept = (type_match.group(4), type_match.group(5))

        else:
            raise Exception(
                self.error_msg("parse error, expect `ConceptType`/`ConceptName`:")
            )

    def parse_rule(self, rule):
        """
        parse the logic rule from text
        """

        strip_rule = rule.strip()
        if strip_rule.startswith("[["):
            self.rule_quote_open = True
            if len(strip_rule) > 2:
                if strip_rule.endswith("]]"):
                    self.rule_quote_open = False
                    self.rule_text = strip_rule[2 : len(strip_rule) - 2].lstrip()
                else:
                    self.rule_text = strip_rule[2].lstrip()
            else:
                self.rule_text = ""
        else:
            self.rule_text = rule

    def complete_rule(self, rule):
        """
        Auto generate define statement and append namespace to the entity name
        """

        pattern = re.compile(r"Define\s*\(", re.IGNORECASE)
        match = pattern.match(rule.strip())
        if not match:
            subject_type = None
            subject_name = None
            if self.dst_concept[0] is not None:
                predicate_name = "leadTo"
                subject_type = f"{self.namespace}.{self.src_concept[0]}"
                subject_name = self.src_concept[1]
                object_type = f"{self.namespace}.{self.dst_concept[0]}"
                object_name = self.dst_concept[1]
            else:
                predicate_name = "belongTo"
                object_type = f"{self.namespace}.{self.src_concept[0]}"
                object_name = self.src_concept[1]
                assert object_type in self.session.spg_types, self.error_msg(
                    f"{object_type} not found in schema"
                )

                concept_type = self.session.get(object_type)
                assert (
                    concept_type.spg_type_enum == SpgTypeEnum.Concept
                ), self.error_msg(f"{object_type} is not concept type")

                for spg_type in self.session.spg_types.values():
                    for relation_name in spg_type.relations:
                        if relation_name.startswith(f"belongTo_{object_type}"):
                            subject_type = spg_type.name
                            break

            if subject_name is None:
                head = (
                    f"Define (s:{subject_type})-[p:{predicate_name}]->(o:`{object_type}`/`{object_name}`)"
                    + " {\n"
                )
            else:
                head = (
                    f"Define "
                    f"(s:`{subject_type}`/`{subject_name}`)-[p:{predicate_name}]->(o:`{object_type}`/`{object_name}`)"
                    + " {\n"
                )
            rule = head + rule
            rule += "\n}"

        # complete the namespace of concept type
        pattern = re.compile(r"\(([\w\s]*?:)`([\w\s\.]+)`/`([^`]+)`\)", re.IGNORECASE)
        replace_list = []
        matches = re.findall(pattern, rule)
        if matches:
            for group in matches:
                if "." in group[1]:
                    continue
                replace_list.append(
                    (
                        f"({group[0]}`{group[1]}`",
                        f"({group[0]}`{self.namespace}.{group[1].strip()}`",
                    )
                )

        # complete the namespace of non-concept type
        pattern = re.compile(r"\(([\w\s]*?:)([\w\s\.]+)\)", re.IGNORECASE)
        matches = re.findall(pattern, rule)
        if matches:
            for group in matches:
                if "." not in group[1]:
                    replace_list.append(
                        (
                            f"({group[0]}{group[1]})",
                            f"({group[0]}{self.namespace}.{group[1].strip()})",
                        )
                    )

        # complete the namespace of type in action clause
        pattern = re.compile(
            r"createNodeInstance\s*?\([^)]+(type=)([^,]+),", re.IGNORECASE
        )
        matches = re.findall(pattern, rule)
        if matches:
            for group in matches:
                if "." not in group[1]:
                    replace_list.append(
                        (
                            f"{group[0]}{group[1]}",
                            f"{group[0]}{self.namespace}.{group[1].strip()}",
                        )
                    )

        if len(replace_list) > 0:
            for t in replace_list:
                rule = rule.replace(t[0], t[1])

        return rule

    def clear_session(self):
        self.src_concept = ()
        self.dst_concept = ()
        self.rule_text = ""

    def submit_rule(self):
        """
        submit the rule definition, make them available for inference
        """

        if self.dst_concept[0] is None:
            # belongTo rule
            self.concept_client.concept_define_dynamic_taxonomy_post(
                define_dynamic_taxonomy_request=rest.DefineDynamicTaxonomyRequest(
                    concept_type_name=f"{self.namespace}.{self.src_concept[0]}",
                    concept_name=self.src_concept[1],
                    dsl=self.rule_text,
                )
            )
            print(
                f"Defined belongTo rule for `{self.src_concept[0]}`/`{self.src_concept[1]}`"
            )

        else:
            # leadTo rule
            self.concept_client.concept_define_logical_causation_post(
                define_logical_causation_request=rest.DefineLogicalCausationRequest(
                    subject_concept_type_name=f"{self.namespace}.{self.src_concept[0]}",
                    subject_concept_name=self.src_concept[1],
                    predicate_name="leadTo",
                    object_concept_type_name=f"{self.namespace}.{self.dst_concept[0]}",
                    object_concept_name=self.dst_concept[1],
                    dsl=self.rule_text,
                )
            )
            print(
                f"Defined leadTo rule for "
                f"`{self.src_concept[0]}`/`{self.src_concept[1]}` -> `{self.dst_concept[0]}`/`{self.dst_concept[1]}`"
            )
        self.clear_session()

    def load_script(self, filename):
        """
        Load and then parse the script file
        """

        file = open(filename, "r", encoding="utf-8")
        lines = file.read().splitlines()
        last_indent_level = 0

        for line in lines:
            self.current_line_num += 1
            strip_line = line.strip()
            if strip_line == "" or strip_line.startswith("#"):
                # skip empty or comments line
                continue

            if self.rule_quote_open:
                # process the multi-line assignment [[ .... ]]
                right_strip_line = line.rstrip()
                if strip_line.endswith("]]"):
                    self.rule_quote_open = False
                    if len(right_strip_line) > 2:
                        self.rule_text += right_strip_line[: len(right_strip_line) - 2]
                    self.rule_text = self.complete_rule(self.rule_text)
                    self.submit_rule()

                else:
                    self.rule_text += line + "\n"
                continue
            elif len(self.rule_text) > 0:
                self.submit_rule()

            indent_count = len(line) - len(line.lstrip())
            if indent_count == 0:
                # the line without indent is namespace definition or a concept definition
                self.clear_session()
                self.parse_concept(strip_line)

            elif indent_count > last_indent_level:
                # the line is the sub definition of the previous line
                if strip_line.startswith("rule:"):
                    if len(strip_line) > 5:
                        self.parse_rule(strip_line[5:])
                else:
                    raise Exception(self.error_msg("parse error, expect rule:"))

            last_indent_level = indent_count

        # if rule is the last line of file, then submit it
        if len(self.rule_text) > 0:
            self.submit_rule()

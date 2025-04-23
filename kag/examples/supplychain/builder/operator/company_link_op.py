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
from typing import List
from kag.common.conf import KAG_PROJECT_CONF
from kag.builder.model.sub_graph import Node
from kag.builder.operator.base import LinkOpABC
from knext.search.client import SearchClient


class CompanyLinkOp(LinkOpABC):

    bind_to = "Company"

    def invoke(self, source: Node, prop_value: str, target_type: str) -> List[str]:
        sc = SearchClient(KAG_PROJECT_CONF.host_addr, KAG_PROJECT_CONF.project_id)
        company_id = []
        records = sc.search_text(prop_value, label_constraints=[target_type], topk=1)
        if records:
            company_id.append(records[0]["node"]["id"])
        return company_id

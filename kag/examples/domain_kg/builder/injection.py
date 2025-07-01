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
import logging

from kag.interface import KAGBuilderChain

logger = logging.getLogger(__name__)


def buildKB():
    from kag.common.conf import KAG_CONFIG

    # inject graph,
    domain_knowledge_graph_chain = KAGBuilderChain.from_config(
        KAG_CONFIG.all_config["domain_kg_inject_chain"]
    )

    domain_knowledge_graph_chain.invoke(None)

    logger.info(f"Done dump domain kg to graph store")


if __name__ == "__main__":
    buildKB()

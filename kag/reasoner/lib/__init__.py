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

LOCAL_REASONER_JAR = "reasoner-local-runner-0.0.1-SNAPSHOT-jar-with-dependencies.jar"

LOCAL_GRAPH_STORE_URL = "neo4j://127.0.0.1:7687"

LOCAL_GRAPH_STATE_CLASS = (
    "com.antgroup.openspg.reasoner.warehouse.cloudext.CloudExtGraphState"
)

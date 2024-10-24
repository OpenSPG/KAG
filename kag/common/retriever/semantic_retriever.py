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

import os
from typing import Any, Iterable, Tuple
from typing import Dict
import logging


from kag.common.utils import processing_phrases
from kag.common.semantic_infer import SemanticEnhance
from kag.common.retriever.kag_retriever import DefaultRetriever

from kag.common.retriever.kag_retriever import DefaultRetriever

logger = logging.getLogger(__name__)


Item = Dict[str, Any]
RetrievalResult = Iterable[Tuple[Item, float]]


class SemanticRetriever(DefaultRetriever, SemanticEnhance):
    def __init__(self, project_id: str = None, **kwargs):
        DefaultRetriever.__init__(self, project_id)
        SemanticEnhance.__init__(self, **kwargs)
        self.general_label = "Entity"
        self.max_expand = 2
        self.concept_sim_t = 0.9

    def get_top_phrases(self, query_ner_list, query_ner_type_list, context=None):
        """
        语义增强改造: entity -[sim]-> node ==> entity -[semantic]-> node
        """
        phrase_ids = []
        query_phrases = []
        max_scores = []
        for query, query_type in zip(query_ner_list, query_ner_type_list):
            query = processing_phrases(query)
            query_phrases.append(query)
            query_node = self.graph_store.get_node(
                label=self.general_label, id_value=query
            )
            if query_node is not None:
                n_type = [i for i in query_node.labels if i != self.general_label][0]
                phrase_ids.append(
                    {
                        "name": query_node["name"],
                        "type": n_type,
                        "_source": "exact_match",
                    }
                )
                max_scores.append(self.pagerank_threshold)

            query_concepts = [
                n
                for n in self.expand_semantic_concept(query, context=context)
                if processing_phrases(n["name"]) not in [processing_phrases(query)]
            ]
            for ix, concept in enumerate(query_concepts):
                if ix >= self.max_expand:
                    continue
                concept["name"] = processing_phrases(concept["name"])
                concept_node = self.graph_store.get_node(
                    label=self.concept_label, id_value=concept["name"]
                )
                if concept_node is not None:
                    phrase_ids.append(
                        {
                            "name": concept_node["name"],
                            "type": self.concept_label,
                            "_source": "expand_concept",
                        }
                    )
                    max_scores.append(self.pagerank_threshold)
                else:
                    # pass
                    recall_concepts = self.graph_store.vector_search(
                        label=self.concept_label,
                        property_key="name",
                        query_text_or_vector=concept["name"],
                        topk=5,
                    )
                    all_nodes = [
                        n["node"]["name"]
                        for n in recall_concepts
                        if n["score"] >= self.concept_sim_t
                    ]
                    for name in all_nodes:
                        if name in {n["name"] for n in phrase_ids}:
                            continue
                        semantic_node = {
                            "name": name,
                            "type": self.concept_label,
                            "_source": "sim_concept",
                        }
                        phrase_ids.append(semantic_node)
                        max_scores.append(self.pagerank_threshold)
                        break

        # top_phrase_vec = np.zeros(self.num_vertices)
        if len(phrase_ids) == 0:
            logger.error(
                f"ERROR, no phrases found for {query_ner_list}, {query_ner_type_list}"
            )

        return phrase_ids, max_scores

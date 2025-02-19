import copy
import json
import pandas as pd
from typing import Type, Dict, List

from kag.common.utils import processing_phrases, to_camel_case
from kag.solver.logic.core_modules.common.schema_utils import SchemaUtils
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity
from kag.solver.logic.core_modules.config import LogicFormConfiguration
from knext.search.client import SearchClient

from kag.builder.model.sub_graph import SubGraph
from knext.common.base.runnable import Input, Output
from kag.common.conf import KAG_PROJECT_CONF
from knext.schema.client import SchemaClient

from kag.interface import LLMClient, PromptABC, VectorizeModelABC, ExtractorABC


@ExtractorABC.register("law_schema_constraint_extractor")
class LawSchemaConstraintExtractor(ExtractorABC):
    """
    Perform knowledge extraction for enforcing schema constraints, including entities, events and their edges.
    The types of entities and events, along with their respective attributes, are automatically inherited from the project's schema.
    """

    def __init__(
            self,
            vectorize_model: VectorizeModelABC,
            llm: LLMClient
    ):
        """
        Initializes the SchemaBasedExtractor instance.

        Args:
            llm (LLMClient): The language model client used for extraction.
        """
        super().__init__()
        self.llm = llm
        self.vectorize_model = vectorize_model
        self.text_similarity = TextSimilarity(vectorize_model)
        self.schema: SchemaUtils = SchemaUtils(
            LogicFormConfiguration(
                {
                    "KAG_PROJECT_ID": KAG_PROJECT_CONF.project_id,
                    "KAG_PROJECT_HOST_ADDR": KAG_PROJECT_CONF.host_addr,
                }
            )
        )
        self._init_search()
        self.df = pd.read_csv('/Users/peilong/Downloads/chargeInLaw.csv')
        self.df.set_index("name", inplace=True)
        self.charge_law = self.df.to_dict(orient='index')

        self.item_2_charge = {}
        for k,v in self.charge_law.items():
            legal_item = v['legalRepresentative']
            if legal_item in self.item_2_charge:
                self.item_2_charge[legal_item].append(k)
            else:
                self.item_2_charge[legal_item] = [k]


    def _init_search(self):
        """
        Initializes the search client for entity linking.
        """
        self._search_client = SearchClient(
            KAG_PROJECT_CONF.host_addr, KAG_PROJECT_CONF.project_id
        )

    @property
    def input_types(self) -> Type[Input]:
        return Dict

    @property
    def output_types(self) -> Type[Output]:
        return SubGraph

    def parse_nodes_and_edges(self, entities: List[Dict], category: str = None):
        """
        Parses nodes and edges from a list of entities.

        Args:
            entities (List[Dict]): The list of entities.

        Returns:
            Tuple[List[Node], List[Edge]]: The parsed nodes and edges.
        """
        graph = SubGraph([], [])
        entities = copy.deepcopy(entities)
        root_nodes = []
        for record in entities:
            if record is None:
                continue
            if isinstance(record, str):
                record = {"name": record}
            s_name = record.get("name", "")
            s_label = record.get("category", category)
            linked_entity = self.link_entity(entity_name=s_name, entity_type=s_label)
            s_name = linked_entity.get("name", "")
            s_label = linked_entity.get("category", category)

            properties = record.get("properties", {})
            # At times, the name and/or label is placed in the properties.
            if not s_name:
                s_name = properties.pop("name", "")
            if not s_label:
                s_label = properties.pop("category", "")
            if not s_name or not s_label:
                continue
            s_name = processing_phrases(s_name)
            root_nodes.append((s_name, s_label))
            lined_properties = linked_entity.get("properties", {})
            lined_properties.update(properties)
            tmp_properties = copy.deepcopy(lined_properties)
            for prop_name, prop_value in properties.items():
                if prop_value is None:
                    tmp_properties.pop(prop_name)
                    continue
            record["properties"] = tmp_properties
            # NOTE: For property converted to nodes/edges, we keep a copy of the original property values.
            #       Perhaps it is not necessary?
            graph.add_node(id=s_name, name=s_name, label=s_label, properties=properties)

            if "official_name" in record:
                official_name = processing_phrases(record["official_name"])
                if official_name != s_name:
                    graph.add_node(
                        id=official_name,
                        name=official_name,
                        label=s_label,
                        properties=properties,
                    )
                    graph.add_edge(
                        s_id=s_name,
                        s_label=s_label,
                        p="OfficialName",
                        o_id=official_name,
                        o_label=s_label,
                    )

        return root_nodes, graph.nodes, graph.edges

    @staticmethod
    def add_relations_to_graph(
            sub_graph: SubGraph, entities: List[Dict], relations: List[list]
    ):
        """
        Add edges to the subgraph based on a list of relations and entities.
        Args:
            sub_graph (SubGraph): The subgraph to add edges to.
            entities (List[Dict]): A list of entities, for looking up category information.
            relations (List[list]): A list of relations, each representing a relationship to be added to the subgraph.
        Returns:
            The constructed subgraph.

        """

        for rel in relations:
            if len(rel) != 5:
                continue
            s_name, s_category, predicate, o_name, o_category = rel
            s_name = processing_phrases(s_name)
            sub_graph.add_node(s_name, s_name, s_category)
            o_name = processing_phrases(o_name)
            sub_graph.add_node(o_name, o_name, o_category)
            edge_type = to_camel_case(predicate)
            if edge_type:
                sub_graph.add_edge(s_name, s_category, edge_type, o_name, o_category)
        return sub_graph

    def assemble_subgraph(
            self,
            entities: List[Dict],
            relations: List[list],
    ):
        """
        Assembles a subgraph from the given chunk, entities, events, and relations.

        Args:
            entities (List[Dict]): The list of entities.

        Returns:
            The constructed subgraph.
        """
        graph = SubGraph([], [])
        _, entity_nodes, entity_edges = self.parse_nodes_and_edges(entities)
        graph.nodes.extend(entity_nodes)
        graph.edges.extend(entity_edges)
        self.add_relations_to_graph(graph, entities, relations)
        return graph

    def link_entity(self, entity_type, entity_name):
        return {
            "name": entity_name,
            "category": entity_type
        }
        # res = self._search_client.search_vector(self.schema.get_label_within_prefix(entity_type), property_key="name",
        #                                         query_vector=self.vectorize_model.vectorize(entity_name), topk=1)
        # if len(res) == 0 or res[0]['score'] < 0.95:
        #     if len(res) and res[0]['score'] > 0.9:
        #         print(f"{res[0]['node']['name']} not same with {entity_name}")
        #     return {
        #         "name": entity_type,
        #         "category": entity_type
        #     }
        # def extra_label(node):
        #     labels = node['__labels__']
        #     for label in labels:
        #         if label != "Entity":
        #             return self.schema.get_label_without_prefix(label)
        #     return None
        #
        # def extra_properties(node):
        #     prop = {}
        #     for k,v in node.items():
        #         if k.startswith("_"):
        #             continue
        #         prop[k]=v
        #     return prop
        # label = extra_label(res[0]['node'])
        # prop = extra_properties(res[0]['node'])
        # if label is None:
        #     return {
        #         "name": entity_type,
        #         "category": entity_type
        #     }
        # return {
        #     "name": res[0]['node']['name'],
        #     "category": label,
        #     "properties": prop
        # }

    def _invoke(self, input: Input, **kwargs) -> List[Output]:
        """
        Invokes the extractor on the given input.

        Args:
            input (Input): The input data.
            **kwargs: Additional keyword arguments.

        Returns:
            List[Output]: The list of output results.
        """
        """
         "law_name": law_name,
                "item_name": item_name,
                "item_content": item_content,
                "index": i+1,
        """
        law_name = input["law_name"]
        entities = [{
            "name": law_name,
            "category": "LegalName"
        }]
        relations = []
        """
        LegalItem-relatedChargeName->ChargeName
        LegalItem-belongToLaw->LegalName
        LegalItem-belongToItem->ItemIndex
        """

        item_name = input['item_name']
        item_content = input['item_content']
        entities.append({
            "name": item_name,
            "category": "LegalItem",
            "properties": {
                "name": item_name,
                "content": item_content
            }
        })
        relations.append([
            item_name, "LegalItem", "belongToLaw", law_name, "LegalName"
        ])
        entities.append({
            "name": item_name.replace(law_name, ''),
            "category": "ItemIndex"
        })
        relations.append([
            item_name, "LegalItem", "belongToItem", item_name.replace(law_name, ''), "ItemIndex"
        ])
        entities.append({
            "name": f"第{str(input['index'])}条",
            "category": "ItemIndex"
        })
        relations.append([
            item_name, "LegalItem", "belongToItem", f"第{str(input['index'])}条", "ItemIndex"
        ])
        if "刑法" in item_name:
            charge_name_set = self.text_similarity.text_sim_result(item_name, list(self.item_2_charge.keys()), topk=1,
                                                                   low_score=0.96, is_cached=False)
            if len(charge_name_set):
                print(f"charge name {item_name} sim {charge_name_set}")
                charge_item = charge_name_set[0][0]
                charges = list(set(self.item_2_charge[charge_item]))
                for c in charges:
                    entities.append({
                        "name": processing_phrases(c),
                        "category": "ChargeName"
                    })
                    relations.append([
                        item_name, "LegalItem", "relatedChargeName", processing_phrases(c), "ChargeName"
                    ])

        subgraph = self.assemble_subgraph(entities, relations)
        return [subgraph]

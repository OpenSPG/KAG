import logging
import knext.common.cache

from typing import List, Dict

from tenacity import stop_after_attempt, retry

from kag.common.conf import KAGConstants, KAGConfigAccessor
from kag.interface import ToolABC, PromptABC, LLMClient
from kag.interface.solver.base_model import SPOEntity
from kag.solver.utils import init_prompt_with_fallback

logger = logging.getLogger()
ner_tool_cache = knext.common.cache.LinkCache(maxsize=100, ttl=300)


@ToolABC.register("ner")
class Ner(ToolABC):
    def __init__(
        self,
        llm_module: LLMClient,
        ner_prompt: PromptABC = None,
        std_prompt: PromptABC = None,
        with_semantic=False,
        **kwargs,
    ):
        super().__init__()
        task_id = kwargs.get(KAGConstants.KAG_QA_TASK_CONFIG_KEY, None)
        kag_config = KAGConfigAccessor.get_config(task_id)
        self.kag_project_config = kag_config.global_config
        self.ner_prompt = ner_prompt or init_prompt_with_fallback(
            "question_ner", self.kag_project_config.biz_scene
        )
        self.std_prompt = std_prompt or init_prompt_with_fallback(
            "std", self.kag_project_config.biz_scene
        )
        self.llm_module = llm_module
        self.with_semantic = with_semantic

    @retry(stop=stop_after_attempt(3), reraise=True)
    def named_entity_recognition(self, query: str):
        """
        Perform named entity recognition.

        This method invokes the pre-configured service client (self.llm) to process the input query,
        using the named entity recognition (NER) prompt (self.ner_prompt).

        Parameters:
        query (str): The text input provided by the user or system for named entity recognition.

        Returns:
        The result returned by the service client, with the type and format depending on the used service.
        """
        return self.llm_module.invoke(
            {"input": query}, self.ner_prompt, with_json_parse=True
        )

    @retry(stop=stop_after_attempt(3), reraise=True)
    def named_entity_standardization(self, query: str, entities: List[Dict]):
        """
        Entity standardization function.

        This function calls a remote service to process the input query and named entities,
        standardizing the entities. This is useful for unifying different representations of the same entity in text,
        improving the performance of natural language processing tasks.

        Parameters:
        - query: A string containing the query with named entities.
        - entities: A list of dictionaries, each containing information about named entities.

        Returns:
        - The result of the remote service call, typically standardized named entity information.
        """
        return self.llm_module.invoke(
            {"input": query, "named_entities": entities},
            self.std_prompt,
            with_json_parse=True,
        )

    @staticmethod
    def append_official_name(
        source_entities: List[Dict], entities_with_official_name: List[Dict]
    ):
        """
        Appends official names to entities.

        Parameters:
        source_entities (List[Dict]): A list of source entities.
        entities_with_official_name (List[Dict]): A list of entities with official names.

        """
        tmp_dict = {}
        for tmp_entity in entities_with_official_name:
            name = tmp_entity["name"]
            category = tmp_entity["category"]
            official_name = tmp_entity["official_name"]
            key = f"{category}{name}"
            tmp_dict[key] = official_name

        for tmp_entity in source_entities:
            name = tmp_entity["name"]
            category = tmp_entity["category"]
            key = f"{category}{name}"
            if key in tmp_dict:
                official_name = tmp_dict[key]
                tmp_entity["official_name"] = official_name

    def _parse_ner_list(self, query):
        ner_list = []
        try:
            ner_list = ner_tool_cache.get(query)
            if ner_list:
                return ner_list
            ner_list = self.named_entity_recognition(query)
            if self.with_semantic:
                std_ner_list = self.named_entity_standardization(query, ner_list)
                self.append_official_name(ner_list, std_ner_list)
            ner_tool_cache.put(query, ner_list)
        except Exception as e:
            if not ner_list:
                ner_list = []
            logger.warning(f"_parse_ner_list {query} failed {e}", exc_info=True)
        return ner_list

    def invoke(self, query, **kwargs) -> List[SPOEntity]:
        res = []
        ner_list = self._parse_ner_list(query)
        for item in ner_list:
            entity = item.get("name", "")
            category = item.get("category", "")
            official_name = item.get("official_name", entity)
            if not entity or not official_name:
                continue
            if category.lower() in ["works", "person", "other"]:
                res.append(SPOEntity(entity_name=entity, un_std_entity_type=category))
            else:
                res.append(
                    SPOEntity(entity_name=official_name, un_std_entity_type=category)
                )
        return res

    def schema(self):
        return {
            "name": "ner",
            "description": "Identify named entities in the input text",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The text to analyze for named entities",
                    }
                },
                "required": ["query"],
            },
        }

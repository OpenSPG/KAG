import itertools
from typing import List, Optional

from kag.solver_new.executor.retriever.local_knowlege_base.kag_retriever.kag_types.logic_node.logic_node import \
    LogicNode, LFNodeData


class TypeInfo:
    def __init__(self, std_entity_type=None, un_std_entity_type=None):
        self.std_entity_type = std_entity_type
        self.un_std_entity_type = un_std_entity_type

    def __repr__(self):
        return f"en:{self.std_entity_type} zh:{self.un_std_entity_type}"


class Condition:
    def __init__(self):
        self.prop_name = None
        self.op = None
        self.condition_value = None

    def __str__(self):
        return f"{self.prop_name} {self.op} {self.condition_value}"

    def __repr__(self):
        return str(self)


class SPOElement:
    def __init__(self):
        self.alias_name: Optional[str] = None
        self.type_set: List[TypeInfo] = []
        self.condition_list: List[Condition] = []

    def __repr__(self):
        return f"{self.alias_name}:{self.get_un_std_entity_first_type_or_std()}"

    def get_value_list_str(self):
        return [str(v) for v in self.condition_list]

    def get_mention_name(self):
        return ""

    def get_type_with_gql_format(self):
        entity_types = self.get_entity_type_set()
        entity_zh_types = self.get_un_std_entity_type_set()
        if len(entity_types) == 0 and len(entity_zh_types) == 0:
            return None
        if None in entity_types and None in entity_zh_types:
            raise RuntimeError(
                f"None type in entity type en {entity_types} zh {entity_zh_types}"
            )
        if len(entity_types) > 0:
            return "|".join(entity_types)
        if len(entity_zh_types) > 0:
            return "|".join(entity_zh_types)

    def get_un_std_entity_first_type_or_std(self):
        std_type = list(self.get_entity_type_set())
        un_std_type = list(self.get_un_std_entity_type_set())
        if len(un_std_type) > 0:
            return un_std_type[0]
        elif len(std_type) > 0:
            return std_type[0]
        else:
            return "Entity"

    def get_entity_first_type_or_un_std(self):
        std_type = list(self.get_entity_type_set())
        unstd_type = list(self.get_un_std_entity_type_set())
        if len(std_type) > 0:
            return std_type[0]
        elif len(unstd_type) > 0:
            return unstd_type[0]
        else:
            return "Entity"

    def get_entity_type_set(self):
        entity_types = []
        for entity_type_info in self.type_set:
            if entity_type_info.std_entity_type is not None:
                entity_types.append(entity_type_info.std_entity_type)
        return set(entity_types)

    def get_un_std_entity_type_set(self):
        entity_types = []
        for entity_type_info in self.type_set:
            if entity_type_info.un_std_entity_type is not None:
                entity_types.append(entity_type_info.un_std_entity_type)
        entity_types = set(entity_types)
        if len(entity_types) == 0:
            return ["Entity"]
        return entity_types


class SPORelation(SPOElement):
    def __init__(self, alias_name=None, rel_type=None, rel_type_zh=None):
        super().__init__()
        if rel_type is not None or rel_type_zh is not None:
            type_info = TypeInfo()
            type_info.std_entity_type = rel_type
            type_info.un_std_entity_type = rel_type_zh
            self.type_set.append(type_info)
        self.alias_name: str = alias_name

        self.s: Optional[SPOElement] = None
        self.o: Optional[SPOEntity] = None

    def __str__(self):
        show = [f"{self.alias_name}:{self.get_un_std_entity_first_type_or_std()}"]
        show = show + self.get_value_list_str()
        return ",".join(show)


class SPOEntity(SPOElement):
    def __init__(
            self,
            entity_id=None,
            std_entity_type=None,
            un_std_entity_type=None,
            entity_name=None,
            alias_name=None,
            is_attribute=False,
    ):
        super().__init__()
        self.is_attribute = is_attribute
        self.id_set = []
        self.entity_name = entity_name
        self.alias_name: str = alias_name
        if entity_id is not None:
            self.id_set.append(entity_id)
        if std_entity_type is not None or un_std_entity_type is not None:
            type_info = TypeInfo()
            type_info.std_entity_type = std_entity_type
            type_info.un_std_entity_type = un_std_entity_type
            self.type_set.append(type_info)

    def __str__(self):
        show = [
            f"{self.alias_name}:{self.get_un_std_entity_first_type_or_std()}{'' if self.entity_name is None else '[' + self.entity_name + ']'} "
        ]
        show = show + self.get_value_list_str()
        return ",".join(show)

    def get_mention_name(self):
        return self.entity_name

    def generate_id_key(self):
        if len(self.id_set) == 0:
            return None
        id_str_set = ['"' + id_str + '"' for id_str in self.id_set]
        return ",".join(id_str_set)

    def generate_start_infos(self, prefix=None):
        if len(self.id_set) == 0:
            return []
        if len(self.type_set) == 0:
            return []

        id_type_info = list(itertools.product(self.id_set, self.type_set))
        return [
            {
                "alias": self.alias_name,
                "id": info[0],
                "type": (
                    info[1].std_entity_type
                    if "." in info[1].std_entity_type
                    else (prefix + "." if prefix is not None else "")
                         + info[1].std_entity_type
                ),
            }
            for info in id_type_info
        ]


class GetSPONodeData(LFNodeData):
    """Container for retrieved data from a single logical node processing step.

    Attributes:
        sub_question (str): Sub-question being processed
        summary (str): Summary generated by LLM
        chunks (List[str]): Retrieved text chunks
        spo (List[RelationData]): SPO relations retrieved from knowledge graph
    """

    def __init__(self):
        super().__init__()
        self.sub_question = ""  # Sub-question text
        self.summary = ""  # Generated summary
        self.chunks = []  # List of retrieved text chunks
        self.spo = []  # List of SPO relation data objects

    def to_str(self):
        return str(self)

    def __repr__(self) -> str:
        """Generate debug-friendly string representation"""
        return f"""sub question: {self.sub_question}
retrieved chunks: 
{self.chunks}

retrieved spo: 
{self.spo}

summary:
{self.summary}
"""


@LogicNode.register("get_spo")
class GetSPONode(LogicNode):
    def __init__(self, operator, args):
        super().__init__(operator, args)
        self.s: SPOElement = args.get("s", None)
        self.p: SPOElement = args.get("p", None)
        self.o: SPOElement = args.get("o", None)
        self.op: str = args.get("op", "=")
        self.sub_query = args.get("sub_query", None)
        self.lf_node_res: GetSPONodeData = GetSPONodeData()

    def get_ele_name(self, alias):
        ele = self.args.get(alias, None)
        if ele is None:
            return ""
        if isinstance(ele, SPOEntity):
            return ele.entity_name if ele.entity_name else ""
        return ""

    def __repr__(self):
        params = [f"{k}={str(v)}" for k, v in self.args.items()]
        params_str = ",".join(params)
        return f"{self.operator}({params_str})"

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.s = args.get("s", self.s)
        self.p = args.get("p", self.p)
        self.o = args.get("o", self.o)
        self.op = args.get("op", "=")
        self.sub_query = args.get("sub_query", self.sub_query)

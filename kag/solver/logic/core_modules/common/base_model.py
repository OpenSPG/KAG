import itertools
import json
import re
from typing import List


class Identifer:
    def __init__(self, alias_name):
        self.alias_name = alias_name

    def __repr__(self):
        return self.alias_name

    def __str__(self):
        return self.alias_name

    def __eq__(self, other):
        if isinstance(other, Identifer):
            return self.alias_name == other.alias_name
        if isinstance(other, str):
            return self.alias_name == other
        return False

    def __hash__(self):
        return hash(self.alias_name)


class TypeInfo:
    def __init__(self, entity_type=None, entity_type_zh=None):
        self.entity_type = entity_type
        self.entity_type_zh = entity_type_zh

    def __repr__(self):
        return f"en:{self.entity_type} zh:{self.entity_type_zh}"


def parse_entity(raw_entity):
    if raw_entity is None:
        return []
    entity_parts = re.findall(r'(?:`(.+?)`|([^|]+))', raw_entity)
    return [part.replace('``', '|') if part else escaping_part for escaping_part, part in entity_parts]


class SPOBase:
    def __init__(self):
        self.alias_name: Identifer = None
        self.type_set: List[TypeInfo] = []
        self.is_attribute = False
        self.value_list = []

    def __repr__(self):
        return f"{self.alias_name}:{self.get_entity_first_type_or_en()}"

    def get_value_list_str(self):
        return [f"{self.alias_name}.{k}={v}" for k,v in self.value_list]

    def get_mention_name(self):
        return ""

    def get_type_with_gql_format(self):
        entity_types = self.get_entity_type_set()
        entity_zh_types = self.get_entity_type_zh_set()
        if len(entity_types) == 0 and len(entity_zh_types) == 0:
            return None
        if None in entity_types and None in entity_zh_types:
            raise RuntimeError(f"None type in entity type en {entity_types} zh {entity_zh_types}")
        if len(entity_types) > 0:
            return "|".join(entity_types)
        if len(entity_zh_types) > 0:
            return "|".join(entity_zh_types)

    def get_entity_first_type(self):
        type_list = list(self.get_entity_type_set())
        if len(type_list) == 0:
            return None
        return type_list[0]

    def get_entity_first_type_or_en(self):
        en = list(self.get_entity_type_set())
        zh = list(self.get_entity_type_zh_set())
        if len(zh) > 0:
            return zh[0]
        elif len(en) > 0:
            return en[0]
        else:
            return None

    def get_entity_type_or_zh_list(self):
        ret = []
        for entity_type_info in self.type_set:
            if entity_type_info.entity_type is not None:
                ret.append(entity_type_info.entity_type)
            elif entity_type_info.entity_type_zh is not None:
                ret.append(entity_type_info.entity_type_zh)
        return ret

    def get_entity_first_type_or_zh(self):
        en = list(self.get_entity_type_set())
        zh = list(self.get_entity_type_zh_set())
        if len(en) > 0:
            return en[0]
        elif len(zh) > 0:
            return zh[0]
        else:
            return None

    def get_entity_type_set(self):
        entity_types = []
        for entity_type_info in self.type_set:
            if entity_type_info.entity_type is not None:
                entity_types.append(entity_type_info.entity_type)
        return set(entity_types)

    def get_entity_type_zh_set(self):
        entity_types = []
        for entity_type_info in self.type_set:
            if entity_type_info.entity_type_zh is not None:
                entity_types.append(entity_type_info.entity_type_zh)
        return set(entity_types)


class SPORelation(SPOBase):
    def __init__(self, alias_name=None, rel_type=None, rel_type_zh=None):
        super().__init__()
        if rel_type is not None or rel_type_zh is not None:
            type_info = TypeInfo()
            type_info.entity_type = rel_type
            type_info.entity_type_zh = rel_type_zh
            self.type_set.append(type_info)
        self.alias_name: Identifer = None
        if alias_name is not None:
            self.alias_name = Identifer(alias_name)

        self.s: SPOBase = None
        self.o: SPOEntity = None

    def __str__(self):
        show = [f"{self.alias_name}:{self.get_entity_first_type_or_en()}"]
        show = show + self.get_value_list_str()
        return ",".join(show)

    @staticmethod
    def parse_logic_form(input_str):
        """
        Parses the logic form from the given input string and constructs a relation object.

        Parameters:
            input_str (str): The input string containing alias and entity types separated by ':'.

        Returns:
            SPORelation: A relation object with alias name and associated type set.
        """

        rel_type_set = []

        # Split the input string into alias and entity_type_set parts
        split_input = input_str.split(':', 1)
        alias = split_input[0]
        # If entity_type_set exists, process it further
        if len(split_input) > 1:
            entity_type_part = split_input[1]

            entity_types = parse_entity(entity_type_part)
            for entity_type in entity_types:
                entity_type_obj = TypeInfo()
                entity_type_obj.entity_type_zh = entity_type
                rel_type_set.append(entity_type_obj)

        rel = SPORelation()
        rel.alias_name = Identifer(alias)
        rel.type_set = rel_type_set
        return rel


class SPOEntity(SPOBase):
    def __init__(self, entity_id=None, entity_type=None, entity_type_zh=None, entity_name=None, alias_name=None,
                 is_attribute=False):
        super().__init__()
        self.is_attribute = is_attribute
        self.id_set = []
        self.entity_name = entity_name
        self.alias_name: Identifer = None
        if alias_name is not None:
            self.alias_name = Identifer(alias_name)
        if entity_id is not None:
            self.id_set.append(entity_id)
        if entity_type is not None or entity_type_zh is not None:
            type_info = TypeInfo()
            type_info.entity_type = entity_type
            type_info.entity_type_zh = entity_type_zh
            self.type_set.append(type_info)

    def __str__(self):
        show = [f"{self.alias_name}:{self.get_entity_first_type_or_en()}{'' if self.entity_name is None else '[' + self.entity_name + ']'} "]
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
        return [{
            "alias": self.alias_name.alias_name,
            "id": info[0],
            "type": info[1].entity_type if '.' in info[1].entity_type else (
                                                                               prefix + '.' if prefix is not None else '') +
                                                                           info[1].entity_type
        } for info in id_type_info]

    @staticmethod
    def parse_logic_form(input_str):
        # # 正则表达式解析输入字符串
        match = re.match(r"([^:]+):?([^\[]+)?(\[[^\[]*\])?(\[[^\[]*\])?", input_str)
        if not match:
            return None

        # 提取和解构匹配的组件
        alias = match.group(1)
        entity_type_raw = match.group(2)
        entity_name_raw = match.group(3)
        entity_id_raw = match.group(4)

        # 处理entity_type_set
        entity_type_set = parse_entity(entity_type_raw)

        # 解析entity_name和entity_id_set
        entity_name = entity_name_raw.strip('][') if entity_name_raw else None
        entity_name = entity_name.strip('`') if entity_name else None
        entity_id_set = parse_entity(entity_id_raw.strip('][')) if entity_id_raw else []

        spo_entity = SPOEntity()
        spo_entity.id_set = entity_id_set
        spo_entity.alias_name = Identifer(alias)
        spo_entity.entity_name = entity_name
        for entity_type in entity_type_set:
            entity_type_obj = TypeInfo()
            entity_type_obj.entity_type_zh = entity_type
            entity_type_obj.entity_type = entity_type
            spo_entity.type_set.append(entity_type_obj)
        return spo_entity


class Entity:
    def __init__(self, entity_id=None, entity_type=None, entity_type_zh=None, entity_name=None, alias_name=None):
        self.id = entity_id
        self.type = entity_type
        self.entity_type_zh = entity_type_zh
        self.entity_name = entity_name
        self.alias_name = alias_name

    def __repr__(self):
        return f"{[self.entity_name, self.alias_name]}:{self.id}({self.type, self.entity_type_zh})"

    def save_args(self, id=None, type=None, entity_type_zh=None, entity_name=None, alias_name=None):
        self.id = id if id else self.id
        self.type = type if type else self.type
        self.entity_type_zh = entity_type_zh if entity_type_zh else self.entity_type_zh
        self.entity_name = entity_name if entity_name else self.entity_name
        self.alias_name = alias_name if alias_name else self.alias_name

    @staticmethod
    def parse_zh(entity_str):
        alias, type_zh, name = '', '', ''
        entity_str = entity_str.replace('：', ':')
        match_alias_type_entity = re.match(r'(.*):(.*)\[(.*)\]', entity_str)
        if match_alias_type_entity:
            alias, type_zh, name = match_alias_type_entity.groups()
        else:
            match_alias_type = re.match(r'(.*):(.*)', entity_str)
            if match_alias_type:
                alias, type_zh = match_alias_type.groups()
            else:
                alias = entity_str
        return Entity(entity_type_zh=type_zh.strip(), entity_name=name.strip(), alias_name=alias.strip())


class LogicNode:
    def __init__(self, operator, args):
        self.operator = operator
        self.args = args
        self.sub_query = args.get('sub_query', '')

    def __repr__(self):
        params = [f"{k}={v}" for k, v in self.args.items()]
        params_str = ','.join(params)
        return f"{self.operator}({params_str})"

    def to_dict(self):
        return json.loads(self.to_json())

    def to_json(self):
        return json.dumps(obj=self,
                          default=lambda x: x.__dict__, sort_keys=False, indent=2)

    def to_dsl(self):
        raise NotImplementedError("Subclasses should implement this method.")

    def to_std(self, args):
        for key, value in args.items():
            self.args[key] = value
        self.sub_query = args.get('sub_query', '')


class LFPlanResult:
    def __init__(self, query: str, lf_nodes: List[LogicNode]):
        self.query: str = query
        self.lf_nodes: List[LogicNode] = lf_nodes
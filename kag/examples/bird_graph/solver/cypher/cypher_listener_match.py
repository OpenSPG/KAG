from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser
from kag.examples.bird_graph.solver.common import load_schema_json


class CypherEntityExtractor:
    def __init__(self):
        # {entity_alias,entity_name}
        self.entities = {}
        self.triples = []
        self.db_name = "california_schools"
        self.graph_schema = load_schema_json(self.db_name)

    def visit_oc_match(self, ctx: CypherParser.OC_MatchContext):
        """
        Extract entities and relations, and correct the directionality of SPO.
        """
        # multi match -> clear triples
        self.triples = []
        pattern = ctx.oC_Pattern()
        if pattern:
            for pattern_part in pattern.oC_PatternPart():
                anonymous_pattern = pattern_part.oC_AnonymousPatternPart()
                self.extract_entities_and_triples(anonymous_pattern)

        return self.rewrite_match()
        # return self.entities, self.triples

    def extract_entities_and_triples(self, anonymous_pattern):
        if anonymous_pattern is None:
            return

        pattern_element = anonymous_pattern.oC_PatternElement()
        if pattern_element:
            start_node = pattern_element.oC_NodePattern()
            start_entity = self.extract_entity(start_node)
            for chain in pattern_element.oC_PatternElementChain():
                relationship = chain.oC_RelationshipPattern()
                end_node = chain.oC_NodePattern()
                end_entity = self.extract_entity(end_node)
                self.extract_triple(start_entity, relationship, end_entity)
                start_entity = end_entity

    def extract_entity(self, node):
        if node is None:
            return None

        alias = node.oC_Variable().getText() if node.oC_Variable() else None
        label = node.oC_NodeLabels().getText() if node.oC_NodeLabels() else None
        if label:
            # replace : -> ''
            label = str.replace(label, ":", "")
            self.entities[alias] = label
        return alias

    def extract_triple(self, start, relationship, end):
        if not start or not relationship or not end:
            return

        rel_var = ""  # relationship.oC_Variable().getText() if relationship.oC_Variable() else None
        rel_label = relationship.oC_RelationshipDetail().oC_RelationshipTypes()
        if rel_label:
            predicate = rel_label.getText()
        else:
            predicate = None
        # replace : -> ''
        predicate = str.replace(predicate, ":", "")
        self.triples.append((start, predicate, end))

    def rewrite_match(self):
        match = ""
        for (start, predicate, end) in self.triples:
            # item
            for item in self.graph_schema:
                if "edge_type" not in item:
                    continue
                if item["edge_type"] == predicate:
                    entity = item["s"]
                    if f"{self.db_name}_{entity}" == self.entities[start]:
                        match += f"MATCH ({start}:{self.entities[start]})-[:{predicate}]->({end}:{self.entities[end]})\n"
                    else:
                        # exchange spo.
                        match += f"MATCH ({end}:{self.entities[end]})-[:{predicate}]->({start}:{self.entities[start]})\n"
                    break
        return match

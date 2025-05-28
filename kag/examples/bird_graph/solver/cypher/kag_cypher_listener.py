from kag.examples.bird_graph.solver.cypher.CypherListener import CypherListener
from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser
from io import StringIO
from kag.examples.bird_graph.solver.cypher.match_extractor import (
    CypherMatchExtractor,
)
from kag.examples.bird_graph.solver.cypher.where_extractor import (
    CypherWhereExtractor,
)


# kag cypher listener
class KagCypherListener(CypherListener):
    def __init__(self, cypher, return_columns):
        self.cypher = cypher
        self.nodeInfo = {
            # {entity_name,entity_alias}
            "nodes": {},
            "properties": [],
        }
        self.relationInfo = {
            "variable_names": [],
            "relationships": [],
            "relation_properties": [],
        }
        self.order = {"fields": []}
        self.where = {"express": []}
        self.match_extractor = CypherMatchExtractor()
        self.where_extractor = CypherWhereExtractor()
        self.rewrite_cypher = StringIO()
        self.alias_mapping = {}
        self.struct = {
            "nodes": self.nodeInfo,
            "relationships": self.relationInfo,
            "order": self.order,
            "where": self.where,
            "rewrite_cypher": self.rewrite_cypher,
        }
        self.return_columns = return_columns

    def var2alias(self, projection_items):
        for item in projection_items:
            alias = item.oC_Variable().getText() if item.oC_Variable() else None
            expression = item.oC_Expression().getText()
            if alias:
                self.alias_mapping[alias] = expression
            else:
                if expression not in self.alias_mapping:
                    self.alias_mapping[expression] = expression

    def convert_entity_2_alias(self):
        alias_entity_columns = {}
        for entity_name in self.return_columns.keys():
            alias_entity_columns[
                self.nodeInfo["nodes"][entity_name]
            ] = self.return_columns[entity_name]
        self.return_columns = alias_entity_columns

    def rewrite_return_column(self, ctx: CypherParser.OC_ReturnContext):
        if not self.return_columns:
            return ctx.getText()
        return_temp_columns = {}
        # old_return_column, new_return_column
        remove_return_columns = {}
        # convert entity 2 alias
        self.convert_entity_2_alias()
        # check return column
        for item in ctx.oC_ProjectionBody().oC_ProjectionItems().oC_ProjectionItem():
            # remove unnecessary fields
            column_with_alias_name = item.oC_Expression().getText()
            remove_return_columns[column_with_alias_name] = ""
            # if entity_alias in self.alias_mapping.keys():
            # column_with_alias_name = self.alias_mapping[column_with_alias_name]
            if "." in column_with_alias_name:
                entity_alias, column_name = column_with_alias_name.split(".", 1)
                if entity_alias not in return_temp_columns.keys():
                    return_temp_columns[entity_alias] = []
                return_temp_columns[entity_alias].append(column_name)
            else:
                return_temp_columns[column_with_alias_name] = column_with_alias_name

        # if len(cypher return column) > len(check_return_column),reduce return column
        if len(return_temp_columns.values()) > len(self.return_columns):
            for entity_alias, columns in return_temp_columns.items():
                if entity_alias in self.return_columns.keys():
                    for column_name in columns:
                        if column_name in self.return_columns[entity_alias]:
                            del remove_return_columns[f"{entity_alias}.{column_name}"]
                else:
                    del remove_return_columns[entity_alias]

        # rewrite return fields
        return_statement = ctx.getText()
        for key, value in remove_return_columns:
            return_statement = return_statement.replace(key, value, 1)
        return return_statement

    def rewrite_match(self, ctx: CypherParser.OC_MatchContext):
        for relation in self.relationInfo["relationships"]:
            pass

    def enterOC_NodePattern(self, ctx: CypherParser.OC_NodePatternContext):
        # node & alias name
        alias = ctx.oC_Variable().getText() if ctx.oC_Variable().getText() else None
        # (abc) case..
        if ctx.oC_NodeLabels():
            node_name = (
                ctx.oC_NodeLabels().getText() if ctx.oC_NodeLabels().getText() else None
            )
            self.nodeInfo["nodes"][str.replace(node_name, ":", "")] = alias
        # node property
        node_property = ctx.oC_Properties().getText() if ctx.oC_Properties() else None
        if node_property:
            self.nodeInfo["properties"].append(node_property)

    def enterOC_RelationshipPattern(
        self, ctx: CypherParser.OC_RelationshipPatternContext
    ):
        variable = (
            ctx.oC_RelationshipDetail().getText()
            if ctx.oC_RelationshipDetail().getText()
            else None
        )
        # types = [rel_type.getText() for rel_type in ctx.relType().getChildren()]
        # direction = "->" if ctx.RIGHT_ARROW() else "<-" if ctx.LEFT_ARROW() else "--"
        self.relationInfo["relationships"].append(variable)

    def enterOC_Order(self, ctx: CypherParser.OC_OrderContext):
        for sort_item in ctx.oC_SortItem():
            field_name = sort_item.oC_Expression().getText()
            self.order["fields"].append(field_name)
        # self.rewrite_cypher.append(ctx.getText())

    def enterOC_Where(self, ctx: CypherParser.OC_WhereContext):
        express = ctx.oC_Expression().getText()
        self.where_extractor.visit_where_condition(ctx)
        text = ctx.getText()
        self.where["express"].append(express)
        self.rewrite_cypher.write("{}\n")

    def enterOC_Match(self, ctx: CypherParser.OC_MatchContext):
        new_match = self.match_extractor.visit_oc_match(ctx)
        if new_match:
            self.rewrite_cypher.write(f"{new_match} \n")
        else:
            self.rewrite_cypher.write(f"MATCH {ctx.oC_Pattern().getText()} \n")

    def enterOC_With(self, ctx: CypherParser.OC_WithContext):
        self.var2alias(ctx.oC_ProjectionBody().oC_ProjectionItems().oC_ProjectionItem())
        # append rewrite cypher
        self.rewrite_cypher.write(f"{ctx.getText()} \n")

    def enterOC_Return(self, ctx: CypherParser.OC_ReturnContext):
        self.var2alias(ctx.oC_ProjectionBody().oC_ProjectionItems().oC_ProjectionItem())
        # return_statement = self.rewrite_return_column(ctx)
        # if not self.where["express"]:
        # self.rewrite_cypher.write("\n")
        self.rewrite_cypher.write(f"{ctx.getText()} \n")

    # replace alias in where expression.
    def replace_where_alias(self, cypher):
        for key, value in self.alias_mapping.items():
            # replace avg(s.abc) -> s.abc
            value = self.where_extractor.function_2_field_expression(value)
            cypher = str.replace(cypher, key, value)
        return cypher

    def rewrite(self):
        new_cypher = self.rewrite_cypher.getvalue()
        """
            If the ORDER BY clause is not empty, 
            then ensure that the fields in the ORDER BY clause are not null in the WHERE condition.
        """
        # maybe exist several where condition
        where_condition = []
        if self.struct["order"]["fields"]:
            new_cypher = self.rewrite_cypher.getvalue()

            if not self.struct["where"]["express"]:
                where_condition.append("WHERE 1=1 \n")
            else:
                for where_text in self.where["express"]:
                    where_text = self.replace_where_alias(where_text)
                    where_condition.append(f"WHERE {where_text} \n")
            for field in self.struct["order"]["fields"]:
                var_name = field
                # replace alias -> real var.
                if field in self.alias_mapping:
                    var_name = self.alias_mapping[field]
                    # replace avg(s.abc) -> s.abc
                    var_name = self.where_extractor.function_2_field_expression(
                        var_name
                    )
                if var_name.lower() == "count(*)" or var_name.lower() == "count(1)":
                    continue

                for i in range(len(where_condition)):
                    where_condition[i] += f"\n AND {var_name} IS NOT NULL"
        else:
            for where_text in self.where["express"]:
                where_condition.append(f"WHERE {where_text} \n")
            # new_cypher = new_cypher.replace("%s", f"{where_condition.getvalue()}\n", 1)
            # new_cypher = new_cypher.replace("%s", "")
            # print("============= rewrite cypher begin ============= ")
            # print(f"cypher:{self.cypher},\n\n new_cypher: {new_cypher}")
            # print("============= rewrite cypher end =============== ")
        try:
            new_cypher = new_cypher.format(*where_condition)
        except KeyError:
            print(f"{new_cypher},{where_condition} key error..")

        return new_cypher

    def enterOC_FunctionInvocation(
        self, ctx: CypherParser.OC_FunctionInvocationContext
    ):
        self.where_extractor.function_name_extractor(ctx)

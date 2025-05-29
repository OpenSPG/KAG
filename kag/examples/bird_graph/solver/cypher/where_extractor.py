from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser


class CypherWhereExtractor:
    def __init__(self):
        # {entity_alias,entity_name}
        self.entities = {}
        self.function_express = {}

    def visit_where_condition(self, ctx: CypherParser.OC_WhereContext):

        for child in ctx.getChildren():
            if isinstance(child, CypherParser.OC_FunctionInvocationContext):
                # 提取聚合函数名称和参数
                func_name = child.getText()
                param = child.oC_Expression().getText()
                # self.aggregates.append((func_name, param))
                print(f"Found aggregate function: {func_name}, Parameter: {param}")

    def function_name_extractor(self, ctx: CypherParser.OC_FunctionInvocationContext):
        """
        处理函数调用，提取聚合函数及其参数。
        """
        func_name = ctx.oC_FunctionName().getText()
        filed = ctx.oC_Expression(0).getText() if ctx.oC_Expression(0) else None
        expression = ctx.getText()
        # pair = (func_name, "value")
        if expression not in self.function_express:
            self.function_express[expression] = filed

    def function_2_field_expression(self, expression):
        new_expression = expression
        if expression in self.function_express:
            new_expression = self.function_express[expression]
        return new_expression

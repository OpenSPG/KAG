from antlr4 import *
from kag.examples.bird_graph.solver.cypher.CypherLexer import CypherLexer
from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser
from kag.examples.bird_graph.solver.cypher.cypher_listener import KagCypherListener


def rewrite_cypher(cypher, return_columns):
    input_stream = InputStream(cypher)
    lexer = CypherLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CypherParser(token_stream)
    tree = parser.oC_Cypher()

    extractor = KagCypherListener(cypher, return_columns)
    walker = ParseTreeWalker()
    walker.walk(extractor, tree)
    return extractor.rewrite()


def rewrite(cypher):
    rewrite_cypher(cypher, [])


if __name__ == "__main__":
    cypher_query = """
        MATCH (f:california_schools_frpm)-[:hasfrpmdata]->(s:california_schools_schools)
        WHERE toFloat(f.`Free Meal Count (Ages 5-17)`) >= 1900.0 AND toFloat(f.`Free Meal Count (Ages 5-17)`) <= 2000.0
        RETURN s.School AS SchoolName, s.Website AS WebsiteAddress
    """

    result = rewrite_cypher(cypher_query)
    # output tree
    # print("nodes:", result["nodes"])
    # print("relationships:", result["relationships"])
    # print("order:", result["order"])
    # print("where:", result["where"])
    print("========================== rewrite cypher ========================== ")
    print(result)

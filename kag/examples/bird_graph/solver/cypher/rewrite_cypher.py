from antlr4 import *
from kag.examples.bird_graph.solver.cypher.CypherLexer import CypherLexer
from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser
from kag.examples.bird_graph.solver.cypher.kag_cypher_listener import KagCypherListener


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
        MATCH (satscores:california_schools_satscores)-[:belongsTo]->(schools:california_schools_schools)<-[:hasfrpmdata]-(frpm:california_schools_frpm)
        WHERE toFloat(satscores.NumGE1500) / toFloat(satscores.NumTstTakr) > 0.3
        RETURN max(toFloat(frpm.`Free Meal Count (Ages 5-17)`) / toFloat(frpm.`Enrollment (Ages 5-17)`)) AS highest_eligible_free_rate
    """

    match = ""
    if match:
        print("xxxx")

    result = rewrite_cypher(cypher_query, [])
    # output tree
    # print("nodes:", result["nodes"])
    # print("relationships:", result["relationships"])
    # print("order:", result["order"])
    # print("where:", result["where"])
    print("========================== rewrite cypher ========================== ")
    print(result)

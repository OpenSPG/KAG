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
    r_cypher = extractor.rewrite()
    # if r_cypher is empty , then return origin cypher
    if r_cypher:
        return r_cypher
    else:
        return cypher


def rewrite(cypher):
    rewrite_cypher(cypher, [])


if __name__ == "__main__":
    cypher_query = """
        MATCH (f:california_schools_frpm)-[:hasfrpmdata]->(s:california_schools_schools)
        MATCH (ss:california_schools_satscores)-[:belongsTo]->(s)
        WHERE f.`County Name` = 'Contra Costa' AND ss.NumTstTakr IS NOT NULL AND ss.NumTstTakr > 0
        RETURN ss.sname AS SchoolName, ss.NumTstTakr AS TestTakers
        ORDER BY TestTakers DESC
        LIMIT 1
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

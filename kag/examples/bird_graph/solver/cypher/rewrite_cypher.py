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
        WHERE f.`Charter Funding Type` = 'Locally funded'
        WITH AVG(f.`Enrollment (K-12)` - f.`Enrollment (Ages 5-17)`) AS avg_diff
        MATCH (f:california_schools_frpm)-[:hasfrpmdata]->(s:california_schools_schools)
        WHERE f.`Charter Funding Type` = 'Locally funded'
        WITH s, f.`Enrollment (K-12)` - f.`Enrollment (Ages 5-17)` AS diff, avg_diff
        WHERE diff > avg_diff
        RETURN s.`School Name` AS SchoolName, s.`DOCType` AS DOCType
    """

    result = rewrite_cypher(cypher_query, [])
    # output tree
    # print("nodes:", result["nodes"])
    # print("relationships:", result["relationships"])
    # print("order:", result["order"])
    # print("where:", result["where"])
    print("========================== rewrite cypher ========================== ")
    print(result)

from antlr4 import *
from kag.examples.bird_graph.solver.cypher.CypherLexer import CypherLexer
from kag.examples.bird_graph.solver.cypher.CypherParser import CypherParser
from kag.examples.bird_graph.solver.cypher.kag_cypher_listener import KagCypherListener


def rewrite_cypher(dataset, db_name, cypher, return_columns):
    input_stream = InputStream(cypher)
    lexer = CypherLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = CypherParser(token_stream)
    tree = parser.oC_Cypher()

    extractor = KagCypherListener(dataset, db_name, cypher, return_columns)
    walker = ParseTreeWalker()
    walker.walk(extractor, tree)
    r_cypher = extractor.rewrite()
    # if r_cypher is empty , then return origin cypher
    if r_cypher:
        return r_cypher
    else:
        return cypher


def rewrite(dataset, db_name, cypher):
    rewrite_cypher(dataset, db_name, cypher, [])


if __name__ == "__main__":
    cypher_query = """
        MATCH (sc:california_schools_schools {City: "Riverside"})
        MATCH (sat:california_schools_satscores)-[:belongsTo]->(sc:california_schools_schools)
        
        where abc = 1
        WITH COLLECT(sat.AvgScrMath) AS mathScores, sc
        WITH SUM(mathScores) / SIZE(mathScores) AS avgMath, sc
        WHERE avgMath > 400
        where abc = 2
        RETURN sc.School AS SchoolName, sc.FundingType AS FundingType

    """

    result = rewrite_cypher(
        "bird_dev_graph_dataset", "california_schools", cypher_query, []
    )
    # output tree
    # print("nodes:", result["nodes"])
    # print("relationships:", result["relationships"])
    # print("order:", result["order"])
    # print("where:", result["where"])
    print("========================== rewrite cypher ========================== ")
    print(result)

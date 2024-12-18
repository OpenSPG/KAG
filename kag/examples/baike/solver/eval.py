from kag.solver.logic.solver_pipeline import SolverPipeline


def qa(query):
    # CA
    resp = SolverPipeline()
    answer, traceLog = resp.run(query)

    print(f"\n\nso the answer for '{query}' is: {answer}\n\n")  #
    print(traceLog)
    return answer, traceLog


if __name__ == "__main__":
    queries = [
        "周星驰的姓名有何含义？",
        "周星驰和万梓良有什么关系",
        "周星驰在首部自编自导自演的电影中，票房达到多少，他在其中扮演什么角色",
        "周杰伦曾经为哪些自己出演的电影创作主题曲？",
        "周杰伦在春晚上演唱过什么歌曲？是在哪一年",
    ]
    for q in queries:
        qa(q)

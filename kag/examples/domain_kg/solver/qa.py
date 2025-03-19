from kag.solver.logic.solver_pipeline import SolverPipeline
from kag.common.conf import KAG_CONFIG


def qa(query):
    resp = SolverPipeline.from_config(KAG_CONFIG.all_config["kag_solver_pipeline"])
    answer, traceLog = resp.run(query)

    print(f"\n\nso the answer for '{query}' is: {answer}\n\n")  #
    print(traceLog)
    return answer, traceLog


if __name__ == "__main__":
    queries = [
        "皮质激素有什么作用",
    ]
    for q in queries:
        qa(q)

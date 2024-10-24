import os
import unittest

from kag.common.env import init_kag_config
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.common.vectorizer.vectorizer import Vectorizer
from kag.solver.implementation.default_kg_retrieval import KGRetrieverByLlm
from kag.solver.implementation.default_lf_planner import DefaultLFPlanner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.common.base_model import SPOEntity
from kag.solver.logic.core_modules.lf_executor import LogicExecutor
from kag.solver.logic.core_modules.lf_generator import LFGenerator
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.solver.logic.core_modules.parser.logic_node_parser import GetNode
from kag.solver.logic.core_modules.retriver.entity_linker import DefaultEntityLinker
from kag.solver.logic.core_modules.retriver.schema_std import SchemaRetrieval

configFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "kag_config.cfg")
init_kag_config(configFilePath)

graph_store = Neo4jClient(
    uri=os.getenv("KAG_GRAPH_STORE_URI"),
    user=os.getenv("KAG_GRAPH_STORE_USER"),
    password=os.getenv("KAG_GRAPH_STORE_PASSWORD"),
    database=os.getenv("KAG_GRAPH_STORE_DATABASE"),
)

graph_store.vectorizer = Vectorizer.from_config(eval(os.getenv("KAG_VECTORIZER")))


lf_solver = LFSolver(chunk_retriever=LFChunkRetriever(), kg_retriever=KGRetrieverByLlm())

std_schema = SchemaRetrieval()
el = DefaultEntityLinker(None, lf_solver.kg_retriever)

generator = LFGenerator()

def convert_node_to_json(s):
    return {
        'id': s.element_id,
        'type': list(s.labels)[0],
        'propertyValues': dict(s)
    }


def convert_edge_to_json(p):
    prop = dict(p)
    start_node = convert_node_to_json(p.start_node)
    end_node = convert_node_to_json(p.end_node)
    prop['original_src_id1__'] = start_node['propertyValues']['id']
    prop['original_dst_id2__'] = end_node['propertyValues']['id']
    return {
        'type': p.type,
        'propertyValues': prop
    }

re = DefaultLFPlanner()

class LogicFormTest(unittest.TestCase):
    def test_neo4j_query(self):
        labels = graph_store.get_all_entity_labels()
        for label in labels:
            if label == "Entity":
                continue
            script = f"""MATCH (n:{label})
SET n:`KQA.{label}`"""
            res = graph_store.run_script(script)
            script = f"""MATCH (n:{label})
            REMOVE n:{label}"""
            res = graph_store.run_script(script)

    def test_neo4j_ppr(self):
        r = graph_store.get_pagerank_scores([{"name":"Anxiety_and_nervousness", "type":"Entity"}], "Entity")
        for i in r:
            print(r)

    def test_search(self):
        ds = graph_store.text_search("Depressive")
        for d in ds:
            print(d)

    def test_vector_search(self):
        ds = graph_store.vector_search("Entity", "name","Depressive")
        for d in ds:
            print(d)


    def test_entity_linker(self):
        get_node = GetNode.parse_node("s")
        get_node.s = SPOEntity(entity_name='david eagleman', entity_type='Person', entity_type_zh='自然人')
        el_data, _ = el.entity_linking("When was David Eagleman born?", [get_node.s])
        print(el_data)
        assert len(el_data) > 0
        assert len(el_data[0]) > 0

    def test_entity_linker2(self):
        get_node = GetNode.parse_node("s")
        get_node.s = SPOEntity(entity_name='Lover Come Back', entity_type='Person', entity_type_zh='自然人')
        el_data, _ = el.entity_linking("Lover Come Back contained the actress who played which part on The Brady Bunch?", [get_node.s])
        print(el_data)
        assert len(el_data) > 0
        assert len(el_data[0]) > 0

    def test_one_hop(self):
        llm_output = """Step1: When was christopher nolan born?
Action1: get_spo(s=s1:Person[christopher nolan], p=p1:born, o=o1:Date)
Action2: get(o1)"""
        lf_nodes = re.lf_planing("When was christopher nolan born?", llm_output)
        executor = LogicExecutor("When was christopher nolan born?", "free qa", None, kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever, std_schema=std_schema,
                               el=el,
                               graph_store=graph_store, generator=generator)
        kg_qa_result, _, history, = executor.execute(lf_nodes, "When was christopher nolan born?")

        print(kg_qa_result)
        print(history)
        assert len(kg_qa_result) > 0
        assert kg_qa_result[0] == '30 july 1970'

    def test_one_hop2(self):
        llm_output = """Step1: When was christopher nolan born?
Action1: get_spo(s=s1:Person[christopher], p=p1:born, o=o1:Date)
Action2: get(o1)"""
        lf_nodes = re.lf_planing("When was christopher nolan born?", llm_output)
        executor = LogicExecutor("When was christopher nolan born?", "free qa", None, kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever, std_schema=std_schema,
                               el=el,
                               graph_store=graph_store, generator=generator)
        kg_qa_result, _, history, = executor.execute(lf_nodes, "When was christopher nolan born?")

        assert len(kg_qa_result) == 0
        assert len(history) > 0
        print(history[-1]['sub_answer'])

    def test_one_hop_deduce_judge_entail(self):
        llm_output = """Step1: When was christopher nolan born?
Action1: get_spo(s=s1:Person[christopher nolan], p=p1:born, o=o1:Date)
Step2: Verify if Christopher Nolan's birthdate is July 30, 1970. And give the real birthday
Action2: deduce(op=judgement,entailment)"""
        lf_nodes = re.lf_planing("When was christopher nolan born? Is Christopher Nolan's date of birth July 30, 1970?", llm_output)
        executor = LogicExecutor("When was christopher nolan born? Is Christopher Nolan's date of birth July 30, 1970?", "free qa", None,
                                 kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever,
                                 std_schema=std_schema,
                                 el=el,
                                 graph_store=graph_store, generator=generator)
        kg_qa_result, _, history, = executor.execute(lf_nodes, "When was christopher nolan born?")

        print(kg_qa_result)
        print(history)
        assert len(kg_qa_result) == 2
        assert kg_qa_result[0] == 'Yes'

    def test_one_hop_deduce_judge_entail2(self):
        llm_output = """Step1: When was christopher nolan born?
Action1: get_spo(s=s1:Person[christopher nolan], p=p1:born, o=o1:Date)
Step2: Verify if Christopher Nolan's birthdate is July 29, 1970. And give the real birthday
Action2: deduce(op=judgement,entailment)"""
        lf_nodes = re.lf_planing(
            "When was christopher nolan born? Is Christopher Nolan's date of birth July 29, 1970?", llm_output)
        executor = LogicExecutor(
            "When was christopher nolan born? Is Christopher Nolan's date of birth July 29, 1970?", "free qa", None,
            kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever,
            std_schema=std_schema,
            el=el,
            graph_store=graph_store, generator=generator)
        kg_qa_result, _, history, = executor.execute(lf_nodes, "When was christopher nolan born?")

        print(kg_qa_result)
        print(history)
        assert len(kg_qa_result) == 2
        assert kg_qa_result[0] == 'No'

    def test_one_hop_deduce_judge(self):
        llm_output = """Step1: When was christopher nolan born?
Action1: get_spo(s=s1:Person[christopher nolan], p=p1:born, o=o1:Date)
Step2: Verify if Christopher Nolan's birthdate is July 30, 1970.
Action2: deduce(op=judgement)"""
        lf_nodes = re.lf_planing("Is Christopher Nolan's date of birth July 30, 1970?", llm_output)
        executor = LogicExecutor("Is Christopher Nolan's date of birth July 30, 1970?", "free qa", None,
                                 kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever,
                                 std_schema=std_schema,
                                 el=el,
                                 graph_store=graph_store, generator=generator)
        kg_qa_result, _, history, = executor.execute(lf_nodes, "When was christopher nolan born?")

        print(kg_qa_result)
        print(history)
        assert len(kg_qa_result) > 0
        assert kg_qa_result[0] == 'Yes'

    def test_galu_query(self):

        llm_output = """Step1: Identify the entity type of Gallu
Action1: get_spo(s=s1:Entity[Gallu], p=p1:EntityType, o=o1:Concept)

Step2: Identify the entity type of Lilu
Action2: get_spo(s=s2:Entity[Lilu], p=p2:EntityType, o=o2:Concept)

Step3: Determine the relationship between Gallu and Lilu
Action3: get_spo(s=s1, p=p3:RelatedTo, o=o2)

Output: output o2
Action4: get(o2)"""
        lf_nodes = re.lf_planing("If Gallu is a demon Lilu is what?", llm_output)
        executor = LogicExecutor("If Gallu is a demon Lilu is what?", "free qa", None, kg_retriever=lf_solver.kg_retriever, chunk_retriever=lf_solver.chunk_retriever, std_schema=std_schema,
                               el=el,
                               graph_store=graph_store, generator=generator)
        kg_qa_result, kg_graph, _, = executor.execute(lf_nodes, "If Gallu is a demon Lilu is what?")
        print(f"call_kb_paths  kg_path={kg_graph.to_answer_path()}")

if __name__ == '__main__':
    unittest.main()

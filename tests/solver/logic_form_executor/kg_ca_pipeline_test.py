import logging
import os
import unittest

import numpy as np

from kag.common.env import init_kag_config
from kag.common.graphstore.neo4j_graph_store import Neo4jClient
from kag.common.vectorizer import Vectorizer
from kag.interface.solver.lf_planner_abc import LFPlannerABC
from kag.solver.implementation.default_reasoner import DefaultReasoner
from kag.solver.implementation.lf_chunk_retriever import LFChunkRetriever
from kag.solver.logic.core_modules.common.text_sim_by_vector import TextSimilarity, cosine_similarity
from kag.solver.logic.core_modules.lf_solver import LFSolver
from kag.solver.logic.solver_pipeline import SolverPipeline

logger = logging.getLogger(__name__)

configFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "kag_config.cfg")
init_kag_config(configFilePath)

class KgCATest(unittest.TestCase):
    def testgraph_vector_test1(self):
        graph_store = Neo4jClient(
            uri=os.getenv("KAG_GRAPH_STORE_URI"),
            user=os.getenv("KAG_GRAPH_STORE_USER"),
            password=os.getenv("KAG_GRAPH_STORE_PASSWORD"),
            database=os.getenv("KAG_GRAPH_STORE_DATABASE"),
        )
        graph_store.vectorizer = Vectorizer.from_config(eval(os.getenv("KAG_VECTORIZER")))
        text_similarity = TextSimilarity()
        out = graph_store.get_node("Creature", "gallu", "name")
        mention_emb = text_similarity.sentence_encode("gallu")

        cosine = cosine_similarity(np.array(mention_emb), np.array(out['_name_vector']))
        print(cosine)
        res = graph_store.vector_search("Creature", property_key="name", query_text_or_vector="gallu", topk=1)
        print(res)

    def run_question(self, q, use_lf_rer = True, use_resp=False)->str:
        init_kag_config(configFilePath)
        if use_lf_rer:
            reasoner = DefaultReasoner()
            resp = SolverPipeline(reasoner=reasoner)
            answer, traceInfo = resp.run(q)
            print("unit test question:" + q + " result:" + (str(answer))+ " trace_info:" + str(traceInfo))
            return answer
        if use_resp:
            lf_solver = LFSolver(chunk_retriever=LFChunkRetriever())
            reasoner = DefaultReasoner(lf_planner=LFPlannerABC(), lf_solver=lf_solver)
            resp = SolverPipeline(reasoner=reasoner, max_run=4)
            answer, traceInfo = resp.run(q)
            print("unit test question:" + q + " result:" + (str(answer)) + " trace_info:" + str(traceInfo))
            return answer
        return ""

    def test_0(self):
        res = self.run_question("When was christopher nolan born?")
        print(res)
    def test_1(self):
        res = self.run_question("If Gallu is a demon Lilu is what?")
        assert "spirit" in res.lower()

    def test_2(self):
        res = self.run_question("Are Christopher Nolan and Sathish Kalathil both film directors?")
        assert "yes" in res.lower()

    def test_3(self):
        res = self.run_question("Are Nantong and Jingdezhen situated in the same province ?")
        assert "no" in res.lower()

    def test_4(self):
        res = self.run_question("Steve Johnson is the current head football coach at a University which also has a second campus in which California city?")
        assert "San Diego" in res

    def test_5(self):
        res = self.run_question("Grace Krilanovich's first novel was published by an independent mom-and-pop publishing house that was founded in 2005, and is based where?")
        assert "Columbus, Ohio" in res

    def test_6(self):
        res = self.run_question("Are both magazines, the Woman's Viewpoint and Pick Me Up, British publications?")
        assert "no" in res.lower()

    def test_7(self):
        res = self.run_question("The runner-up in the 1999 World Drivers' Championship appears on the front cover of a racing video game developed by what company?")
        assert "Studio 33" in res

    def test_8(self):
        res = self.run_question("""At the 2011 census, what was he population of the city where Kerry Saxby-Junna was born?""")
        assert "6,960" in res

    def test_9(self):
        res = self.run_question("Which plant is larger, the Pterocarya or the Cotula?")
        assert "Pterocarya" in res

    def test_10(self):
        res = self.run_question(
            "The manuscript for Flute Sonata in C major, BWV 1033 is in the hand of a German musician whose godfather is whom?")
        assert "Georg Philipp Telemann" in res

    def test_11(self):
        res = self.run_question("""Who directed the film that was shot in or around Leland, North Carolina in 1986""")
        assert "Stephen King" in res

    def test_12(self):
        res = self.run_question(
            "What actresses were involved in the scandal that temporarily separated the Hong Kong duo Twins in 2008?")

    def test_re_failed_1(self):
        res = self.run_question("""Who performed in both Welcome to the Show and the band f(x)?""")
        assert "Choi Jin-ri" in res

    def test_re_failed_2(self):
        res = self.run_question("Scott Andrew Buchholz, is an Australian politician, he previously served as chief of staff to which Queensland Senator Australian politician, who has served as the Deputy Prime Minister of Australia since 18 February 2016?")
        assert "Barnaby Joyce" in res

    def test_re_failed_3(self):
        res = self.run_question("In what year was the man that resigned as the president of Israel before the Israeli presidential election, 2000 born?")
        assert "1924" in res

    def test_re_failed_5(self):
        res = self.run_question("""What genre is the author of the story behind "Act of War; Direct Action" associated with?""")
        assert "aviation techno-thriller novels" in res

    def test_re_failed_6(self):
        res = self.run_question("""Philip Carlo was a biographer for an American contract killer who was associated with members of what crime family?""")
        assert "DeCavalcante crime family" in res

    def test_re_failed_7(self):
        res = self.run_question(
            """Who was Audrey Williams pregnant with during the recording of "Dear Brother"?""")
        assert "Hank Williams, Jr." in res

    def test_re_failed_8(self):
        res = self.run_question("""Are Medici and Senet both board games?""")
        assert "yes" in res.lower()

    def test_re_failed_9(self):
        res = self.run_question("""Charles Andrews graduated from what college preparatory boys' school?""")
        assert "Hebron Academy" in res

    def test_re_failed_10(self):
        res = self.run_question("""Which magazine was published first, Guitar World or Science News?""")
        assert "Science News" in res

    def test_re_failed_11(self):
        res = self.run_question("""When was the Welsh singer born who is known for her distinctive husky voice and who's third album is "Diamond Cut" (1979)?""")
        assert "8 June 1951" in res

    def test_re_failed_12(self):
        res = self.run_question("""Are Frozen and Escape from the Dark both animated features?""")
        assert "no" in res.lower()

    def test_re_failed_13(self):
        res = self.run_question("""Jean Vander Pyl provided the voice of Rosie on the Hanna-Barbera animated sitcom that originally premiered on which date?""")
        assert "September 23, 1962" in res

    def test_re_failed_14(self):
        res = self.run_question("""The film Darkon follows the Darkon Wargaming Club based in Baltimore, Maryland, a group that participates in an activity with this 4-letter acronym name.""")
        assert "LARP" in res

    def test_re_failed_15(self):
        res = self.run_question("""Jon L. Luther was the chairman and CEO of a restaurant holding company headquartered in what city?""")
        assert "Canton, Massachusetts" in res

    def test_re_failed_17(self):
        res = self.run_question("""What position does the footballer who plays for the capital and the largest city of Portugal paly?""")
        assert "central defender" in res

    def test_re_failed_18(self):
        res = self.run_question("Which of the two tornado outbreaks killed the most people?")
        assert "March 2 and 3, 2012" in res

    def test_qwen2_failed_1(self):
        res = self.run_question(
            """Scott Howell is a consultant who has worked with the mayor of what city?""", use_default=True)
        assert "New York City" in res

    def test_qwen2_failed_2(self):
        res = self.run_question(
            """What language were books being translated into during the era of Haymo of Faversham?""", use_default=True)
        assert "Latin" in res


    def test_musique_1(self):
        res = self.run_question("Who was the first president of the association which published Journal of Psychotherapy Integration?")

    def test_musique_2(self):
        res = self.run_question("When did the Admiral Twin open in the city where the Philbrook Museum is located?")

    def test_musique_3(self):
        res = self.run_question("What county shares a border with the county in which Johnnycake, West Virginia is located?")

    def test_re_failed_resp_1(self):
        res = self.run_question("""Steve Johnson is the current head football coach at a University which also has a second campus in which California city?""")
        assert "San Diego" in res

    def test_re_failed_resp_2(self):
        res = self.run_question("""What is the abbreviation to the magazine that called Qvwm  "an unusually impressive imposter"?""")
        assert "LXF" in res

    def test_re_failed_resp_3(self):
        res = self.run_question("""Thumb Wrestling Federation is on a network founded by who?""")
        assert "Betty Cohen" in res

    def test_re_failed_resp_4(self):
        res = self.run_question("""What position did the receiver of the 2007 FIFA U-20 Golden Shoe play?""")
        assert "striker" in res

    def test_re_failed_resp_5(self):
        res = self.run_question("""Drew Fuller stared in a series that originally broadcast on what station?""")
        assert "The WB" in res

    def test_re_failed_resp_6(self):
        res = self.run_question("""Terry McGurrin was the story editor for the show "Scaredy Squirrel" which was written by who?""")
        assert "M&eacute;lanie Watt" in res

    def test_re_failed_resp_7(self):
        res = self.run_question("""Which city was the band which was formed in 1981 in Los Angeles when vocalist/guitarist James Hetfield responded to an advertisement posted by drummer Lars Ulrich in a local newspaper hosted by L'Amour?""")
        assert "New York" in res

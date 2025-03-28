import os
import unittest

from kag.common.env import init_kag_config
from kag.solver.plan.default_lf_planner import DefaultLFPlanner
from kag.common.text_sim_by_vector import TextSimilarity

configFilePath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "kag_config.cfg")
init_kag_config(configFilePath)

lf_planner = DefaultLFPlanner()
class ParseTest(unittest.TestCase):

    def test_plan1(self):
        lf_nodes = lf_planner.lf_planing("When was erik hort born? and where born?")
        print(lf_nodes)

    def test_plan2(self):
        lf_nodes = lf_planner.lf_planing("""Which city was the band which was formed in 1981 in Los Angeles when vocalist/guitarist James Hetfield responded to an advertisement posted by drummer Lars Ulrich in a local newspaper hosted by L'Amour?""")
        print(lf_nodes)

    def test_plan3(self):
        lf_nodes = lf_planner.lf_planing("""Under what name did the founder and lead guitarist of the band Porcupine Tree use when he released his album Indicates Void?""")
        print(lf_nodes)

    def test_plan4(self):
        lf_nodes = lf_planner.lf_planing("""Terry McGurrin was the story editor for the show "Scaredy Squirrel" which was written by who?""")
        print(lf_nodes)

    def test_plan5(self):
        lf_nodes = lf_planner.lf_planing("""What position did the receiver of the 2007 FIFA U-20 Golden Shoe play?""")
        print(lf_nodes)

    def test_plan6(self):
        lf_nodes = lf_planner.lf_planing("""In what film did Roddy Maude-Roxby play a character based on a story by a team including Tom Rowe as a writer?""")
        print(lf_nodes)

    def test_text_sim(self):
        candidates = ['题材', '上映时间', '制片地']
        text_similarity = TextSimilarity()
        mention = '类型'
        out = text_similarity.text_type_sim(mention, candidates)
        print(out)


if __name__ == '__main__':
    unittest.main()

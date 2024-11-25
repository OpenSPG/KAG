#!/usr/bin/python
# encoding: utf-8
"""
Project: openspgapp
Auther: Zhongpu Bo
Email: zhongpubo.bzp@antgroup.com
DateTime: 2024/11/4 15:15
Description:

"""

from kag.common.retriever.kag_retriever import SemanticRetriever

import logging
logger = logging.getLogger(__name__)


class IRCoTPipeline:

    reason_instruction = (
        'You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across '
        'multiple documents. This task is illustrated through demonstrations, each consisting of a document set paired '
        'with a relevant question and its multi-hop reasoning thoughts. Your task is to generate one thought for current '
        'step, DON\'T generate the whole thoughts at once! If you reach what you believe to be the final step, start with '
        '"So the answer is:".'
    )

    few_shot = {
        "2wiki": (
            "Kurram Garhi\n"
            "Kurram Garhi is a small village located near the city of Bannu, which is the part of Khyber Pakhtunkhwa province of Pakistan. Its population is approximately 35000. Barren hills are near this village. This village is on the border of Kurram Agency. Other nearby villages are Peppal, Surwangi and Amandi Kala.\n\n"
            "2001–02 UEFA Champions League second group stage\n"
            "Eight winners and eight runners-up from the first group stage were drawn into four groups of four teams, each containing two group winners and two runners- up. Teams from the same country or from the same first round group could not be drawn together.The top two teams in each group advanced to the quarter- finals.\n\n"
            "Satellite tournament\n"
            "A satellite tournament is either a minor tournament or event on a competitive sporting tour or one of a group of such tournaments that form a series played in the same country or region.\n\n"
            "Trojkrsti\n"
            "Trojkrsti is a village in Municipality of Prilep, Republic of Macedonia.\n\n"
            "Telephone numbers in Ascension Island\n"
            "Country Code:+ 247< br> International Call Prefix: 00 Ascension Island does not share the same country code( +290) with the rest of St Helena.\n\n"
            "Question: Are both Kurram Garhi and Trojkrsti located in the same country?\n"
            "Thought: Kurram Garhi is located in the country of Pakistan. Trojkrsti is located in the country of Republic of Macedonia. Thus, they are not in the same country. So the answer is: no.\n"
        ),
        "hotpotqa": (
            "Milk and Honey (album)\n"
            "Milk and Honey is an album by John Lennon and Yoko Ono released in 1984. Following the compilation \"The John Lennon Collection\", it is Lennon's eighth and final studio album, and the first posthumous release of new Lennon music, having been recorded in the last months of his life during and following the sessions for their 1980 album \"Double Fantasy\". It was assembled by Yoko Ono in association with the Geffen label.\n\n"
            "John Lennon Museum\n"
            "John Lennon Museum (ジョン・レノン・ミュージアム , Jon Renon Myūjiamu ) was a museum located inside the Saitama Super Arena in Chūō-ku, Saitama, Saitama Prefecture, Japan. It was established to preserve knowledge of John Lennon's life and musical career. It displayed Lennon's widow Yoko Ono's collection of his memorabilia as well as other displays. The museum opened on October 9, 2000, the 60th anniversary of Lennon’s birth, and closed on September 30, 2010, when its exhibit contract with Yoko Ono expired. A tour of the museum began with a welcoming message and short film narrated by Yoko Ono (in Japanese with English headphones available), and ended at an avant-garde styled \"reflection room\" full of chairs facing a slide show of moving words and images. After this room there was a gift shop with John Lennon memorabilia available.\n\n"
            "Walls and Bridges\n"
            "Walls and Bridges is the fifth studio album by English musician John Lennon. It was issued by Apple Records on 26 September 1974 in the United States and on 4 October in the United Kingdom. Written, recorded and released during his 18-month separation from Yoko Ono, the album captured Lennon in the midst of his \"Lost Weekend\". \"Walls and Bridges\" was an American \"Billboard\" number-one album and featured two hit singles, \"Whatever Gets You thru the Night\" and \"#9 Dream\". The first of these was Lennon's first number-one hit in the United States as a solo artist, and his only chart-topping single in either the US or Britain during his lifetime.\n\n"
            "Nobody Loves You (When You're Down and Out)\n"
            "\"Nobody Loves You (When You're Down and Out)\" is a song written by John Lennon released on his 1974 album \"Walls and Bridges\". The song is included on the 1986 compilation \"Menlove Ave.\", the 1990 boxset \"Lennon\", the 1998 boxset \"John Lennon Anthology\", the 2005 two-disc compilation \"\", and the 2010 boxset \"Gimme Some Truth\".\n\n"
            "Give Peace a Chance\n"
            "\"Give Peace a Chance\" is an anti-war song written by John Lennon (credited to Lennon–McCartney), and performed with Yoko Ono in Montreal, Quebec, Canada. Released as a single in 1969 by the Plastic Ono Band on Apple Records (catalogue Apple 13 in the United Kingdom, Apple 1809 in the United States), it is the first solo single issued by Lennon, released when he was still a member of the Beatles, and became an anthem of the American anti-war movement during the 1970s. It peaked at number 14 on the \"Billboard\" Hot 100 and number 2 on the British singles chart.\n\n"
            "Question: Nobody Loves You was written by John Lennon and released on what album that was issued by Apple Records, and was written, recorded, and released during his 18 month separation from Yoko Ono?\n"
            "Thought: The album issued by Apple Records, and written, recorded, and released during John Lennon's 18 month separation from Yoko Ono is Walls and Bridges. Nobody Loves You was written by John Lennon on Walls and Bridges album. So the answer is: Walls and Bridges.\n"
        ),
        "musique": (
            "The Last Horse\n"
            "The Last Horse (Spanish:El último caballo) is a 1950 Spanish comedy film directed by Edgar Neville starring Fernando Fernán Gómez.\n\n"
            "Southampton\n"
            "The University of Southampton, which was founded in 1862 and received its Royal Charter as a university in 1952, has over 22,000 students. The university is ranked in the top 100 research universities in the world in the Academic Ranking of World Universities 2010. In 2010, the THES - QS World University Rankings positioned the University of Southampton in the top 80 universities in the world. The university considers itself one of the top 5 research universities in the UK. The university has a global reputation for research into engineering sciences, oceanography, chemistry, cancer sciences, sound and vibration research, computer science and electronics, optoelectronics and textile conservation at the Textile Conservation Centre (which is due to close in October 2009.) It is also home to the National Oceanography Centre, Southampton (NOCS), the focus of Natural Environment Research Council-funded marine research.\n\n"
            "Stanton Township, Champaign County, Illinois\n"
            "Stanton Township is a township in Champaign County, Illinois, USA. As of the 2010 census, its population was 505 and it contained 202 housing units.\n\n"
            "Neville A. Stanton\n"
            "Neville A. Stanton is a British Professor of Human Factors and Ergonomics at the University of Southampton. Prof Stanton is a Chartered Engineer (C.Eng), Chartered Psychologist (C.Psychol) and Chartered Ergonomist (C.ErgHF). He has written and edited over a forty books and over three hundered peer-reviewed journal papers on applications of the subject. Stanton is a Fellow of the British Psychological Society, a Fellow of The Institute of Ergonomics and Human Factors and a member of the Institution of Engineering and Technology. He has been published in academic journals including \"Nature\". He has also helped organisations design new human-machine interfaces, such as the Adaptive Cruise Control system for Jaguar Cars.\n\n"
            "Finding Nemo\n"
            "Finding Nemo Theatrical release poster Directed by Andrew Stanton Produced by Graham Walters Screenplay by Andrew Stanton Bob Peterson David Reynolds Story by Andrew Stanton Starring Albert Brooks Ellen DeGeneres Alexander Gould Willem Dafoe Music by Thomas Newman Cinematography Sharon Calahan Jeremy Lasky Edited by David Ian Salter Production company Walt Disney Pictures Pixar Animation Studios Distributed by Buena Vista Pictures Distribution Release date May 30, 2003 (2003 - 05 - 30) Running time 100 minutes Country United States Language English Budget $94 million Box office $940.3 million\n\n"
            "Question: When was Neville A. Stanton's employer founded?\n"
            "Thought: The employer of Neville A. Stanton is University of Southampton. The University of Southampton was founded in 1862. So the answer is: 1862.\n"
        )
    }

    def __init__(self, top_k=8, max_run=3, dataset_name=None):
        # self.retriever = Neo4JRetriever('BGE', database=os.getenv("KAG_GRAPH_STORE_DATABASE"))  # DefaultRetriever()
        self.retriever = SemanticRetriever()
        self.retriever.with_fix_onto = False
        self.retriever.with_semantic_entity = False
        self.retriever.with_semantic_hyper = False
        self.retriever.semantic_model = None
        self.llm_module = self.retriever.client  # LLMClient.from_config(eval(os.getenv('KAG_DEBUG')))
        self.max_run = max_run
        self.top_k = top_k
        self.d_name = dataset_name
        assert self.d_name in self.few_shot, \
            f"invalid dataset name: {self.d_name}, should be one of {self.few_shot.keys()}"

    def reason(self, query, passages, thoughts):
        prompt_demo = self.few_shot[self.d_name]

        prompt_user = ""
        for passage in passages:
            prompt_user += f'{passage}\n\n'
        prompt_user += f'Question: {query}\nThought: ' + ' '.join(thoughts)

        prompt = self.reason_instruction + '\n\n' + prompt_demo + '\n\n' + prompt_user
        # prompt = {
        #     "system": self.reason_instruction + '\n\n' + prompt_demo,
        #     "user": prompt_user
        # }
        # messages = ChatPromptTemplate.from_messages(
        #     [
        #         SystemMessage(self.reason_instruction + "\n\n" + prompt_demo),
        #         HumanMessage(prompt_user),
        #     ]
        # ).format_prompt()
        # prompt = messages.to_string()

        try:
            response_content = self.llm_module(prompt)
        except Exception as e:
            print(e)
            return ''
        return response_content

    def retrieve(self, query):
        docs = self.retriever.recall_docs(query, top_k=self.top_k)
        doc_info = {}
        for d in docs:
            _parts = [i for i in d.split('#') if i.strip()]
            # node_name = _parts[0].strip()
            score = float(_parts[-1])
            content = '#'.join(_parts[:-1]).strip()
            doc_info[content] = score
        return doc_info

    @staticmethod
    def extract_answer(thought):
        answer_marker = "so the answer is:"
        if answer_marker not in thought.lower():
            logger.warning('invalid answer: {}'.format(thought))
            return thought
        answer_start = thought.lower().index(answer_marker) + len(answer_marker)
        return thought[answer_start:]

    def run(self, question):

        it = 1
        thoughts = []
        trace_log = []
        retrieved_passages_dict = self.retrieve(question)
        while it < self.max_run:  # for each iteration of IRCoT
            retrieved_passages = [
                k for k, v in sorted(retrieved_passages_dict.items(), key=lambda x: x[1], reverse=True)
            ]
            new_thought = self.reason(question, retrieved_passages[:self.top_k], thoughts)
            thoughts.append(new_thought)
            trace_log.append({
                "rerank_docs": retrieved_passages,
                "present_thought": new_thought
            })
            if 'so the answer is' in new_thought.lower():
                break
            it += 1
            new_passages_dict = self.retrieve(new_thought)

            for passage, score in new_passages_dict.items():
                if passage in retrieved_passages_dict:
                    retrieved_passages_dict[passage] = max(retrieved_passages_dict[passage], score)
                else:
                    retrieved_passages_dict[passage] = score

        # end iteration
        response = self.extract_answer(thoughts[-1]).strip()
        return response, trace_log

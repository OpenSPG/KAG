#!/usr/bin/python
# encoding: utf-8
"""
Project: openspgapp
Auther: Zhongpu Bo
Email: zhongpubo.bzp@antgroup.com
DateTime: 2024/11/4 15:15
Description:

"""

from kag.common.retriever.neo4j_retriever import Neo4JRetriever

import logging
logger = logging.getLogger(__name__)


class RAGPipeline:

    reason_instruction = (
        'You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across '
        'multiple documents. This task is illustrated through demonstrations, each consisting of a document set paired '
        'with a relevant question and its multi-hop reasoning thoughts. Your task is to generate one thought for current '
        'step, DON\'T generate the whole thoughts at once! If you reach what you believe to be the final step, start with '
        '"So the answer is:".'
    )

    def __init__(self, top_k=8, max_run=3, dataset_name=None):
        self.retriever = Neo4JRetriever('BGE')  # DefaultRetriever()
        self.llm_module = self.retriever.client  # LLMClient.from_config(eval(os.getenv('KAG_DEBUG')))

    def reason(self, query, passages, thoughts):

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

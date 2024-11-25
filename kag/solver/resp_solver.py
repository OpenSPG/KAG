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


class Reasoner:
    def __init__(self, llm):
        self.llm = llm
        self.update_reason_path = []

    def judge(self, instruction, memory):
        prompt = "Judging based solely on the current known information and without allowing for inference, are you able to completely and accurately respond to the question '{}'? \nKnown information: '{}'. \nIf you can, please reply with 'Yes' directly; if you cannot and need more information, please reply with 'No' directly.".format(
            instruction, memory
        )
        if_finished_info = self.llm(prompt)
        logger.debug('推理器判别:{}'.format(if_finished_info))
        if if_finished_info[:3] == 'Yes':
            if_finished = True
        else:
            if_finished = False
        return if_finished

    def plan(self, instruction, memory):
        prompt = "You serve as an intelligent assistant, adept at facilitating users through complex, multi-hop reasoning across multiple documents. Please understand the information gap between the currently known information and the target problem.Your task is to generate one thought in the form of question for next retrieval step directly. DON\'T generate the whole thoughts at once!\n[Known information]: {}\n[Target question]: {}\n[You Thought]:".format(memory, instruction)
        response = self.llm(prompt)
        logger.debug('推理器规划:{}'.format(response))
        update_reason_path = self.format_reason_path(response)
        return update_reason_path

    def format_reason_path(self, response):
        update_reason_path = []
        split_path = response.split("\n")
        for p in split_path:
            if 'Here are the steps' in p or p == '\n' or p == '':
                continue
            else:
                update_reason_path.append(p)
        logger.debug('当前推理路径:{}'.format(str(update_reason_path)))
        return update_reason_path


class Memory:
    def __init__(self, llm):
        self.llm = llm
        self.state_memory = []
        self.evidence_memory = []

    def verifier(self, docs, sub_instruction):
        prompt = "Judging based solely on the current known information and without allowing for inference, are you able to respond completely and accurately to the question '{}'? \nKnown information: '{}'. If yes, please reply with 'Yes', followed by an accurate response to the question '{}', without restating the question; if no, please reply with 'No' directly.".format(
            sub_instruction, str(docs), sub_instruction
        )
        satisfied_info = self.llm(prompt)
        logger.debug('状态判别:{}'.format(satisfied_info))
        if satisfied_info[:3] == 'Yes':
            satisfied = True
        else:
            satisfied = False
        if satisfied:
            satisfied_info = satisfied_info.replace('Yes', '').strip()
            res = "The answer to the Question'{}' is '{}'".format(sub_instruction, satisfied_info)
            if res not in self.state_memory:
                self.state_memory.append(res)

    def extractor(self, docs, instruction):
        prompt = "Passages: {}\nYour job is to act as a professional writer. You will write a good-quality passage that can support the given prediction about the question only based on the information in the provided supporting passages. Now, let's start. After you write, please write [DONE] to indicate you are done. Do not write a prefix (e.g., 'Response:'') while writing a passage.\nQuestion:{}\nPassage:".format(
            str(docs), instruction
        )
        evidence = self.llm(prompt)
        logger.debug('证据抽取:{}'.format(evidence))
        if evidence not in self.evidence_memory:
            self.evidence_memory.append(evidence)

    def serialize_memory(self):
        serialize_memory = "[State Memory]:{}\n[Evidence Memory]:{}\n".format(
            str(self.state_memory), str(self.evidence_memory)
        )
        return serialize_memory

    def refresh(self):
        self.state_memory = []
        self.evidence_memory = []


class Generator:
    def __init__(self, llm):
        self.llm = llm

    def generate(self, instruction, memory):
        prompt = "Answer the question based on the given reference.\nOnly give me the answer and do not output any other words.\nThe following are given reference:'{}'\nQuestion: '{}'".format(
            memory, instruction
        )
        response = self.llm(prompt)
        return response


class ReSPPipeline:

    def __init__(self, max_run=3):
        self.retriever = SemanticRetriever()
        llm_module = self.retriever.client
        self.reasoner = Reasoner(llm_module)
        self.memory = Memory(llm_module)
        self.generator = Generator(llm_module)
        self.max_run = max_run

    def run(self, question):
        self.memory.refresh()
        instruction = question
        if_finished = False
        present_instruction = instruction
        logger.debug('主指令:{}'.format(instruction))
        present_memory = ""
        run_cnt = 0
        trace_log = []
        while not if_finished and run_cnt < self.max_run:
            logger.debug('当前指令:{}'.format(present_instruction))
            run_cnt += 1
            docs = self.retriever.recall_docs(present_instruction)
            if present_instruction != instruction:
                self.memory.verifier(docs, present_instruction)
            self.memory.extractor(docs, instruction)
            present_memory = self.memory.serialize_memory()
            if_finished = self.reasoner.judge(instruction, present_memory)
            if not if_finished:
                update_reason_path = self.reasoner.plan(instruction, present_memory)
                if len(update_reason_path) == 0:
                    break
                present_instruction = update_reason_path[0]
            trace_log.append({
                "rerank_docs": docs,
                "present_instruction": present_instruction,
                "present_memory": present_memory
            })
        response = self.generator.generate(instruction, present_memory)
        return response, trace_log


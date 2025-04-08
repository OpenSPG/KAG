import json
from string import Template
from typing import List
from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC
from knext.schema.client import SchemaClient


@PromptABC.register("default_decomposition")
class DecompositionGeneratorPrompt(PromptABC):
#     template_en = """
#     {
#     "instruction": "Please extract a series of atomic questions from as many different perspectives as possible based on the given content, ensuring that these questions can be answered directly through the original content. Each sub-question extracted is required to be atomic in nature and cannot be further split. The questions as a whole should be diverse, avoiding the extraction of questions that are repetitive or highly similar. Each question must contain the name of a specific entity, and the use of pronouns such as “it, he, she, they, the company, the person” is prohibited. Strictly follow the format of the output in the example.",
#     "example": [
#         {
#             "input": "After a year at Barcelona's youth academy, La Masia, Messi was finally enrolled in the Royal Spanish Football Federation (RFEF) in February 2002. Now playing in all competitions, he befriended his teammates, among whom were Cesc F\u00e0bregas and Gerard Piqu\u00e9. After completing his growth hormone treatment aged 14, Messi became an integral part of the ``Baby Dream Team '', Barcelona's greatest - ever youth side. During his first full season (2002 -- 03), he was top scorer with 36 goals in 30 games for the Cadetes A, who won an unprecedented treble of the league and both the Spanish and Catalan cups. The Copa Catalunya final, a 4 -- 1 victory over Espanyol, became known in club lore as the partido de la m\u00e1scara, the final of the mask. A week after suffering a broken cheekbone during a league match, Messi was allowed to start the game on the condition that he wear a plastic protector; soon hindered by the mask, he took it off and scored two goals in 10 minutes before his substitution. At the close of the season, he received an offer to join Arsenal, his first from a foreign club, but while F\u00e0bregas and Piqu\u00e9 soon left for England, he chose to remain in Barcelona.",
#             "output": [
#                         {
#                             "question": "How long did Messi stay at Barcelona's youth academy La Masia before joining the Royal Spanish Football Federation (RFEF)?",
#                             "answer": "1 year"
#                         },
#                         {
#                             "question": "Which organization did Messi join in February 2002?",
#                             "answer": "Royal Spanish Football Federation (RFEF)"
#                         },
#                         {
#                             "question": "Which teammates did Messi befriend during his time at La Masia?",
#                             "answer": "Cesc Fàbregas and Gerard Piqué"
#                         },
#                         {
#                             "question": "At what age did Messi complete his growth hormone treatment?",
#                             "answer": "14 years old"
#                         },
#                         {
#                             "question": "In which season did Messi become the top scorer for Cadetes A?",
#                             "answer": "2002-03 season"
#                         },
#                         {
#                             "question": "How many goals did Messi score for Cadetes A in the 2002-03 season?",
#                             "answer": "36 goals"
#                         },
#                         {
#                             "question": "How many games did Messi play for Cadetes A in the 2002-03 season?",
#                             "answer": "30 games"
#                         },
#                         {
#                             "question": "Which titles did Cadetes A win in the 2002-03 season?",
#                             "answer": "League title, Spanish Cup, and Catalan Cup"
#                         },
#                         {
#                             "question": "Which team did Messi face in the Copa Catalunya final?",
#                             "answer": "Espanyol"
#                         },
#                         {
#                             "question": "What was the score of the Copa Catalunya final?",
#                             "answer": "4-1"
#                         },
#                         {
#                             "question": "What protective gear did Messi wear in the Copa Catalunya final?",
#                             "answer": "Plastic protective mask"
#                         },
#                         {
#                             "question": "How many goals did Messi score in the Copa Catalunya final?",
#                             "answer": "2 goals"
#                         },
#                         {
#                             "question": "How long after scoring in the Copa Catalunya final was Messi substituted?",
#                             "answer": "10 minutes"
#                         },
#                         {
#                             "question": "Which foreign club offered Messi a contract at the end of the 2002-03 season?",
#                             "answer": "Arsenal"
#                         },
#                         {
#                             "question": "Which country did Fàbregas and Piqué move to after the 2002-03 season?",
#                             "answer": "England"
#                         },
#                         {
#                             "question": "What decision did Messi make after receiving an offer from Arsenal?",
#                             "answer": "Stay in Barcelona"
#                         }
#                     ]
#         }
#     ],
#     "input": "$input"
# }
#         """
    template_en = """
    # Task
Your task is to analyze the given content and extract from it as many relevant questions as possible, able to cover all the detail information of the content, making sure that these questions can be answered by the original content. A variety of questions is required to avoid extracting duplicates or questions with a high degree of similarity. Each question must contain the name of a specific entity, and the use of pronouns such as “it, he, she, they, the company, the person” is prohibited.

# Output Format
Output your answers line by line, with each question on a new line, without itemized symbols or numbers.

# Content
$input

# Output:
    """
    template_zh = """
# Task
你的任务是分析给定内容，从中尽可能多的从不同角度和提问方式提取一系列相关问题，能够涵盖文档的全部信息，并确保这些问题能够通过原文内容得到解答。要求问题具有多样性，避免提取重复或相似度高的提问。每个问题必须包含具体的实体名称，禁止使用"它、他、她、他们、该公司、此人"等代词。

# Output Format
将每个问题单独成行输出，不使用项目符号或编号标记。

# Content
$input

# Output:
"""

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        questions = response.split("\n")
        questions = [question.strip() for question in questions if len(question.strip()) > 0]

        return questions

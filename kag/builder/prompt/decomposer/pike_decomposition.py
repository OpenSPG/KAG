import json
from string import Template
from typing import List
from kag.common.conf import KAG_PROJECT_CONF
from kag.interface import PromptABC
from knext.schema.client import SchemaClient


@PromptABC.register("default_decomposition")
class DecompositionGeneratorPrompt(PromptABC):
    template_en = """
    {
    "instruction": "Please extract a series of questions that can be directly answered based on the information provided in the reference document, and provide your own answers. The extracted questions should not imply sub-questions and should be atomic in nature. Additionally, the answers should be as concise as possible, providing definitive answers directly.",
    "example": [
        {
            "input": "After a year at Barcelona's youth academy, La Masia, Messi was finally enrolled in the Royal Spanish Football Federation (RFEF) in February 2002. Now playing in all competitions, he befriended his teammates, among whom were Cesc F\u00e0bregas and Gerard Piqu\u00e9. After completing his growth hormone treatment aged 14, Messi became an integral part of the ``Baby Dream Team '', Barcelona's greatest - ever youth side. During his first full season (2002 -- 03), he was top scorer with 36 goals in 30 games for the Cadetes A, who won an unprecedented treble of the league and both the Spanish and Catalan cups. The Copa Catalunya final, a 4 -- 1 victory over Espanyol, became known in club lore as the partido de la m\u00e1scara, the final of the mask. A week after suffering a broken cheekbone during a league match, Messi was allowed to start the game on the condition that he wear a plastic protector; soon hindered by the mask, he took it off and scored two goals in 10 minutes before his substitution. At the close of the season, he received an offer to join Arsenal, his first from a foreign club, but while F\u00e0bregas and Piqu\u00e9 soon left for England, he chose to remain in Barcelona.",
            "output": [
                        {
                            "question": "How long did Messi stay at Barcelona's youth academy La Masia before joining the Royal Spanish Football Federation (RFEF)?",
                            "answer": "1 year"
                        },
                        {
                            "question": "Which organization did Messi join in February 2002?",
                            "answer": "Royal Spanish Football Federation (RFEF)"
                        },
                        {
                            "question": "Which teammates did Messi befriend during his time at La Masia?",
                            "answer": "Cesc Fàbregas and Gerard Piqué"
                        },
                        {
                            "question": "At what age did Messi complete his growth hormone treatment?",
                            "answer": "14 years old"
                        },
                        {
                            "question": "In which season did Messi become the top scorer for Cadetes A?",
                            "answer": "2002-03 season"
                        },
                        {
                            "question": "How many goals did Messi score for Cadetes A in the 2002-03 season?",
                            "answer": "36 goals"
                        },
                        {
                            "question": "How many games did Messi play for Cadetes A in the 2002-03 season?",
                            "answer": "30 games"
                        },
                        {
                            "question": "Which titles did Cadetes A win in the 2002-03 season?",
                            "answer": "League title, Spanish Cup, and Catalan Cup"
                        },
                        {
                            "question": "Which team did Messi face in the Copa Catalunya final?",
                            "answer": "Espanyol"
                        },
                        {
                            "question": "What was the score of the Copa Catalunya final?",
                            "answer": "4-1"
                        },
                        {
                            "question": "What protective gear did Messi wear in the Copa Catalunya final?",
                            "answer": "Plastic protective mask"
                        },
                        {
                            "question": "How many goals did Messi score in the Copa Catalunya final?",
                            "answer": "2 goals"
                        },
                        {
                            "question": "How long after scoring in the Copa Catalunya final was Messi substituted?",
                            "answer": "10 minutes"
                        },
                        {
                            "question": "Which foreign club offered Messi a contract at the end of the 2002-03 season?",
                            "answer": "Arsenal"
                        },
                        {
                            "question": "Which country did Fàbregas and Piqué move to after the 2002-03 season?",
                            "answer": "England"
                        },
                        {
                            "question": "What decision did Messi make after receiving an offer from Arsenal?",
                            "answer": "Stay in Barcelona"
                        }
                    ]
        }
    ],
    "input": "$input"
}    
        """

    template_zh = """
    {
        "instruction": "请根据给出的参考文档，从中提取一系列可以直接从文档给出的信息的得出答案的问题，并自行作答。要求提取的问题不能隐含细分出子问题，具有原子性。并且答案请尽量简洁，直接给出确定的答案。",
        "example": [
            {
                "input": "在巴塞罗那青训学院拉玛西亚待了一年后，梅西于2002年2月正式注册加入西班牙皇家足球联合会（RFEF）。此后，他开始参加所有比赛，并与队友们建立了友谊，其中包括塞斯克·法布雷加斯（Cesc Fàbregas）和杰拉德·皮克（Gerard Piqué）。在14岁完成生长激素治疗后，梅西成为了“宝贝梦之队”（Baby Dream Team）的核心成员，这是巴塞罗那有史以来最出色的青年队。在他的第一个完整赛季（2002-03赛季）中，他以36个进球成为Cadetes A队的最佳射手，该队在30场比赛中赢得了联赛、西班牙杯和加泰罗尼亚杯的三冠王，创造了前所未有的纪录。加泰罗尼亚杯决赛以4-1战胜西班牙人队（Espanyol），这场比赛在俱乐部历史上被称为“面具决赛”（partido de la máscara）。在联赛中颧骨骨折一周后，梅西被允许在佩戴塑料保护面具的条件下首发上场。然而，面具很快影响了他的发挥，他摘下面具并在10分钟内打进两球，随后被替换下场。赛季结束时，他收到了来自阿森纳的邀请，这是他第一次收到外国俱乐部的邀约。尽管法布雷加斯和皮克不久后前往英格兰，梅西选择继续留在巴塞罗那。",
                "output": [
                            {
                                "question": "梅西在巴塞罗那青年学院拉玛西亚待了多久后加入了皇家西班牙足球联合会（RFEF）？",
                                "answer": "1年"
                            },
                            {
                                "question": "梅西在2002年2月加入了哪个组织？",
                                "answer": "皇家西班牙足球联合会（RFEF）"
                            },
                            {
                                "question": "梅西在拉玛西亚期间与哪些队友成为了朋友？",
                                "answer": "塞斯克·法布雷加斯（Cesc Fàbregas）和杰拉德·皮克（Gerard Piqué）"
                            },
                            {
                                "question": "梅西在几岁时完成了生长激素治疗？",
                                "answer": "14岁"
                            },
                            {
                                "question": "梅西在哪个赛季成为Cadetes A队的最佳射手？",
                                "answer": "2002-03赛季"
                            },
                            {
                                "question": "梅西在2002-03赛季为Cadetes A队打进了多少球？",
                                "answer": "36球"
                            },
                            {
                                "question": "梅西在2002-03赛季为Cadetes A队踢了多少场比赛？",
                                "answer": "30场"
                            },
                            {
                                "question": "Cadetes A队在2002-03赛季赢得了哪些冠军？",
                                "answer": "联赛冠军、西班牙杯和加泰罗尼亚杯"
                            },
                            {
                                "question": "梅西在加泰罗尼亚杯决赛中对阵哪支球队？",
                                "answer": "西班牙人（Espanyol）"
                            },
                            {
                                "question": "加泰罗尼亚杯决赛的比分是多少？",
                                "answer": "4-1"
                            },
                            {
                                "question": "梅西在加泰罗尼亚杯决赛中佩戴了什么防护装备？",
                                "answer": "塑料保护面具"
                            },
                            {
                                "question": "梅西在加泰罗尼亚杯决赛中打进多少球？",
                                "answer": "2球"
                            },
                            {
                                "question": "梅西在加泰罗尼亚杯决赛中进球后多久被换下？",
                                "answer": "10分钟"
                            },
                            {
                                "question": "梅西在2002-03赛季结束后收到了哪支外国俱乐部的邀请？",
                                "answer": "阿森纳（Arsenal）"
                            },
                            {
                                "question": "法布雷加斯和皮克在2002-03赛季结束后去了哪个国家？",
                                "answer": "英格兰"
                            },
                            {
                                "question": "梅西在收到阿森纳邀请后做出了什么决定？",
                                "answer": "留在巴塞罗那"
                            }
                        ]
            }
        ],
        "input": "$input"
    }    
        """

    @property
    def template_variables(self) -> List[str]:
        return ["input"]

    def parse_response(self, response: str, **kwargs):
        rsp = response
        if isinstance(rsp, str):
            rsp = json.loads(rsp)
        if isinstance(rsp, dict) and "output" in rsp:
            entities = rsp["output"]
        else:
            entities = rsp

        return entities

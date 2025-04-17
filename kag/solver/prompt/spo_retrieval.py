import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_spo_retrieval")
class SpoRetrieval(PromptABC):
    template_zh = """{
  "指令": "你是一名语言专家。你的任务是根据以下规则从给定的 SPO 候选项中选择正确的 SPO 文本来回答给定的问题。请确保它与 SPO 提及或问题匹配。",
  "要求": [
    "输出必须从 SPO 候选项中选择，并且必须与其内容保持一致，以列表格式呈现。",
    "如果在 SPO 候选项中没有合适的答案，输出一个空列表。确保输出与问题或 SPO 提及高度匹配。",
    "如果在 SPO 候选项中有多个正确答案，以json列表形式输出所有匹配的 SPO。"
  ],
  "示例": [
    {
      "问题": "Woman's Viewpoint 是一本英国出版物吗？",
      "SPO 提及": "出版物[Woman's Viewpoint] 国籍 国家",
      "SPO 候选项": [
        "Woman's Viewpoint 从 1923 年出版到 1927 年",
        "Woman's Viewpoint 由 Florence M. Sterling 出版",
        "Woman's Viewpoint 创立于 1923 年",
        "Woman's Viewpoint 在德克萨斯州创立",
        "Woman's Viewpoint 是一本女性杂志",
        "Rolandos Liatsos 出演 Woman in Mind",
        "Rolandos Liatsos 出演 Woman in Mind"
      ],
      "分析": "根据问题和 SPO 提及，我们需要找到出版物 “Woman's Viewpoint” 的出版国家。SPO 'Woman's Viewpoint 在德克萨斯州创立' 包含了地理位置信息，可从这里推断出所在国籍。",
      "output": [
        "Woman's Viewpoint 在德克萨斯州创立"
      ]
    },
    {
      "问题": "哪位德国音乐家的手稿是《C大调长笛奏鸣曲，BWV 1033》的？",
      "SPO 提及": "实体[Flute Sonata in C major, BWV 1033] InHandOf 实体",
      "SPO 候选项": [
        "C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach",
        "C大调长笛奏鸣曲，BWV 1033 是为长笛或竖笛和低音连续演奏",
        "C大调长笛奏鸣曲，BWV 1033 是一首四乐章的奏鸣曲"
      ],
      "分析": "根据问题和 SPO 提及，我们需要找出谁持有《C大调长笛奏鸣曲，BWV 1033》的手稿。根据提供的 SPO 候选项，SPO \"C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach\" 与问题相关。可以推断出《C大调长笛奏鸣曲，BWV 1033》的手稿应在 Johann Sebastian Bach 的手中。",
      "output": [
        "C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach"
      ]
    }
  ],
  "任务": {
    "问题": "$question",
    "SPO 提及": "$mention",
    "SPO 候选项": "$candis"
  },
  "output": "提供一个JSON列表，其中包含根据SPO提及内容选出的最佳回答问题的SPO候选者。"
}
"""
    template_en = """{
  "instruction": "You are a language expert. Your task is to select the correct SPO (Subject Predicate Object) text from the given SPO candidates according to the following rules to answer the given question. Ensure that the selected SPO matches the SPO mention or appropriately answers the question.",
  "requirements": [
    "The output must be selected from the SPO candidates and remain consistent with their content, presented in a list format.",
    "If there is no suitable answer in the SPO candidates, output an empty list. Ensure that the output is highly relevant to the question or SPO mention.",
    "If there are multiple correct answers in the SPO candidates, output all matching SPOs in a JSON list format."
  ],
  "examples": [
    {
      "question": "Is the Woman's Viewpoint a British publication?",
      "spo_mention": "Publication[Woman's Viewpoint] Nationality Country",
      "spo_candidates": [
        "the woman s viewpoint ranFrom 1923 to 1927",
        "the woman s viewpoint publishedBy florence m sterling",
        "the woman s viewpoint foundedIn 1923",
        "the woman s viewpoint foundedIn texas",
        "the woman s viewpoint was a woman s magazine",
        "rolandos liatsos starredIn woman in mind",
        "rolandos liatsos starredIn woman in mind"
      ],
      "analysis": "The question seeks the nationality of the publication \"Woman's Viewpoint.\" Among the SPO candidates, \"the woman s viewpoint foundedIn texas\" indicates the location of its founding, which relates to its nationality.",
      "output": [
        "the woman s viewpoint foundedIn texas"
      ]
    },
    {
      "question": "Who is the German musician whose hand the manuscript for Flute Sonata in C major, BWV 1033 is in?",
      "spo_mention": "Entity[Flute Sonata in C major, BWV 1033] InHandOf Entity",
      "spo_candidates": [
        "flute sonata in c major bwv 1033 isAttributedTo johann sebastian bach",
        "flute sonata in c major bwv 1033 isFor flute or recorder and basso continuo",
        "flute sonata in c major bwv 1033 is a sonata in 4 movements"
      ],
      "analysis": "The question aims to identify who holds the manuscript of \"Flute Sonata in C major, BWV 1033.\" The SPO candidate \"flute sonata in c major bwv 1033 isAttributedTo johann sebastian bach\" implies ownership, indicating that Johann Sebastian Bach holds the manuscript.",
      "output": [
        "flute sonata in c major bwv 1033 isAttributedTo johann sebastian bach"
      ]
    }
  ],
  "task": {
    "question": "$question",
    "spo_mention": "$mention",
    "spo_candidates": "$candis"
  },
  "output": "Provide a JSON list of the selected SPO candidates that best answer the question based on the spo mention."
}
"""

    @property
    def template_variables(self) -> List[str]:
        return ["question", "mention", "candis"]

    def parse_response(self, response, **kwargs):
        logger.debug(
            f"SpoRetrieval {response} mention:{self.template_variables_value.get('mention', '')} "
            f"candis:{self.template_variables_value.get('candis', '')}"
        )
        if isinstance(response, list):
            return response
        if not isinstance(response, dict):
            return response
        if "output" in response:
            return response["output"]
        if "Output" in response:
            return response["Output"]
        return response

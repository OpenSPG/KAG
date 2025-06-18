import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("default_spo_retrieval")
class SpoRetrieval(PromptABC):
    template_zh = """{
      "指令": "你是一名语言专家。你的任务是根据以下规则从给定的 SPO 候选项编号中选择正确的索引号来回答问题。请直接输出对应的编号数字。",
      "要求": [
        "输出必须为 SPO 候选项中的编号索引（从0开始），以字符串数组格式呈现",
        "候选项列表索引与原始输入顺序严格对应（第1个候选项为0，第2个为1，依此类推）",
        "如果多个候选项都正确，输出所有匹配的索引号",
        "如果没有合适答案，输出空列表"
      ],
      "示例": [
        {
          "问题": "Woman's Viewpoint 是一本英国出版物吗？",
          "SPO 提及": "出版物[Woman's Viewpoint] 国籍 国家",
          "SPO 候选项": [
            "Woman's Viewpoint 从 1923 年出版到 1927 年",
            "Woman's Viewpoint 由 Florence M. Sterling 出版",
            "Woman's Viewpoint 创立于 1923 年",
            "Woman's Viewpoint 在德克萨斯州创立",  // 索引3
            "Woman's Viewpoint 是一本女性杂志",
            "Rolandos Liatsos 出演 Woman in Mind"
          ],
          "output": ["3"]
        },
        {
          "问题": "哪位德国音乐家的手稿是《C大调长笛奏鸣曲，BWV 1033》的？",
          "SPO 提及": "实体[Flute Sonata in C major, BWV 1033] InHandOf 实体",
          "SPO 候选项": [
            "C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach",  // 索引0
            "C大调长笛奏鸣曲，BWV 1033 是为长笛或竖笛和低音连续演奏",
            "C大调长笛奏鸣曲，BWV 1033 是一首四乐章的奏鸣曲"
          ],
          "output": ["0"]
        }
      ],
      "任务": {
        "问题": "$question",
        "SPO 提及": "$mention",
        "SPO 候选项": "$candis"
      },
      "output": "提供一个字符串数组，包含与问题匹配的SPO候选项索引编号"
    }
    """

    template_en = """{
      "instruction": "You are a language expert. Your task is to select the correct SPO candidate indices to answer the question, based on the SPO mention.",
      "requirements": [
        "Output must be string array of SPO candidate indices (0-based numbering)",
        "Indices correspond strictly to the original candidate order (1st=0, 2nd=1, etc.)",
        "Return all matching indices if multiple candidates match",
        "Return empty list if no candidates match"
      ],
      "examples": [
        {
          "question": "Is the Woman's Viewpoint a British publication?",
          "spo_mention": "Publication[Woman's Viewpoint] Nationality Country",
          "spo_candidates": [
            "the woman s viewpoint ranFrom 1923 to 1927",
            "the woman s viewpoint publishedBy florence m sterling",
            "the woman s viewpoint foundedIn 1923",
            "the woman s viewpoint foundedIn texas",  // index 3
            "the woman s viewpoint was a woman s magazine"
          ],
          "output": ["3"]
        },
        {
          "question": "Who is the German musician whose hand the manuscript for Flute Sonata in C major, BWV 1033 is in?",
          "spo_mention": "Entity[Flute Sonata in C major, BWV 1033] InHandOf Entity",
          "spo_candidates": [
            "flute sonata in c major bwv 1033 isAttributedTo johann sebastian bach",  // index 0
            "flute sonata in c major bwv 1033 isFor flute or recorder and basso continuo"
          ],
          "output": ["0"]
        }
      ],
      "task": {
        "question": "$question",
        "spo_mention": "$mention",
        "spo_candidates": "$candis"
      },
      "output": "Return a JSON string array containing matching candidate indices"
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

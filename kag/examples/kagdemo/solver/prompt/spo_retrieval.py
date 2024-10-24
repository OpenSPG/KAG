import logging
from typing import List

from kag.common.base.prompt_op import PromptOp

logger = logging.getLogger(__name__)


class SpoRetrieval(PromptOp):
    template_zh = """示例 1:
问题：Woman's Viewpoint 是一本英国出版物吗？
SPO 提及：出版物[Woman's Viewpoint] 国籍 国家
SPO 候选项：['Woman's Viewpoint 从 1923 年出版到 1927 年', 'Woman's Viewpoint 由 Florence M. Sterling 出版', 'Woman's Viewpoint 创立于 1923 年', 'Woman's Viewpoint 在德克萨斯州创立', 'Woman's Viewpoint 是一本女性杂志', 'Rolandos Liatsos 出演 Woman in Mind', 'Rolandos Liatsos 出演 Woman in Mind']
分析：根据问题和 SPO 提及，我们需要找到出版物 “Woman's Viewpoint” 的出版国家。SPO 'Woman's Viewpoint 在德克萨斯州创立' 包含了地理位置信息，可从这里推断出所在国籍
output：['Woman's Viewpoint 在德克萨斯州创立']

示例 2:
问题：哪位德国音乐家的手稿是《C大调长笛奏鸣曲，BWV 1033》的？
SPO 提及：实体[Flute Sonata in C major, BWV 1033] InHandOf 实体
SPO 候选项：['C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach', 'C大调长笛奏鸣曲，BWV 1033 是为长笛或竖笛和低音连续演奏', 'C大调长笛奏鸣曲，BWV 1033 是一首四乐章的奏鸣曲']
分析：根据问题和 SPO 提及，我们需要找出谁持有《C大调长笛奏鸣曲，BWV 1033》的手稿。根据提供的 SPO 候选项，SPO "C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach" 与问题相关。可以推断出《C大调长笛奏鸣曲，BWV 1033》的手稿应在 Johann Sebastian Bach 的手中。
output：['C大调长笛奏鸣曲，BWV 1033 归因于 Johann Sebastian Bach']

要求：
你是一名语言专家。你的任务是根据以下规则从给定的 SPO 候选项中选择正确的 SPO 文本来回答给定的问题。请确保它与 SPO 提及或问题匹配。

输出必须从 SPO 候选项中选择，并且必须与其内容保持一致，以列表格式呈现。
如果在 SPO 候选项中没有合适的答案，输出一个空列表。确保输出与问题或 SPO 提及高度匹配。
如果在 SPO 候选项中有多个正确答案，输出所有匹配的 SPO。

问题：$question
SPO 提及: $mention
SPO 候选项: $candis
output:
"""
    template_en = """Examples 1:
Question: Is the Woman's Viewpoint a British publication?
spo mention: Publication[Woman's Viewpoint] Nationality Country
spo candications: ['the woman s viewpoint ranFrom 1923 to 1927', 'the woman s viewpoint publishedBy florence m  sterling', 'the woman s viewpoint foundedIn 1923', 'the woman s viewpoint foundedIn texas', 'the woman s viewpoint was a woman s magazine', 'rolandos liatsos starredIn woman in mind', 'rolandos liatsos starredIn woman in mind']
Analysis: Based on the Question and the SPO mention, we need to find the country of publication for the publication "Woman's Perspective". According to the information provided in the SPO candidates, the SPO  'the woman s viewpoint foundedIn texas' is related to the spo mention.
output: ['the woman s viewpoint foundedIn texas']

Examples 2:
Question: Who is the German musician whose hand the manuscript for Flute Sonata in C major, BWV 1033 is in?
spo mention: Entity[Flute Sonata in C major, BWV 1033] InHandOf Entity
spo candications: ['flute sonata in c major  bwv 1033 isAttributedTo johann sebastian bach', 'flute sonata in c major  bwv 1033 isFor flute or recorder and basso continuo', 'flute sonata in c major  bwv 1033 is a sonata in 4 movements']
Analysis: Based on the Question and the SPO mention, we need to find out who holds the manuscript of "Flute Sonata in C major, BWV 1033". According to the information provided in the SPO candidates, the SPO "flute sonata in c major bwv 1033 isAttributedTo johann sebastian bach" is related to the spo mention. It can be inferred that the manuscript of "Flute Sonata in C major, BWV 1033" should be in the hands of Johann Sebastian Bach.
output: ['flute sonata in c major  bwv 1033 isAttributedTo johann sebastian bach']

Requirements:
You are a language expert. Your task is to select the correct SPO (subject predicate object) text from the given SPO candidates according to the following rules to answer the given question. Please ensure that it matches the SPO mention or answer question.
1. The output must be selected from the SPO candidates and must remain consistent with their content, presented in a list format.
2. If there is no suitable answer in the SPO candidates, output an empty list. Ensure that the output is highly matched with the question or SPO mention.
3. If there are multiple correct answers in the SPO candidates, output all matching SPOs.

Question：$question
spo mention: $mention
spo candications: $candis
output: """

    def __init__(self, language: str):
        super().__init__(language)

    @property
    def template_variables(self) -> List[str]:
        return ["question", "mention", "candis"]

    def parse_response_en(self, satisfied_info: str):
        if satisfied_info[:3] == 'Yes':
            if_finished = True
        else:
            if_finished = False
        return if_finished

    def parse_response_zh(self, satisfied_info: str):
        if satisfied_info.startswith("是"):
            if_finished = True
        else:
            if_finished = False
        return if_finished

    def parse_response(self, response: str, **kwargs):
        logger.debug(
            f"SpoRetrieval {response} mention:{self.template_variables_value.get('mention', '')} "
            f"candis:{self.template_variables_value.get('candis', '')}")
        llm_output = response.replace('Expected Output:', '')
        llm_output = llm_output.replace('"', '')
        return llm_output.strip()

from typing import List
import logging

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("summary_resp_generator")
class RespGenerator(PromptABC):
    #
    # This prompt template is adapted from LightRAG:
    #
    #   https://github.com/HKUDS/LightRAG/blob/45cea6e/lightrag/prompt.py#L156
    #
    # which can produce answers with better comprehensiveness, diversity
    # and empowerment to general questions.
    #
    # NOTE: This prompt template may not be the best for all the tasks.
    #       For example, it won't produce answers with high EM and F1
    #       scores for the hotpotqa, 2wiki and musique datasets.
    #
    _prompt_template = """---Role---

You are a helpful assistant responding to questions about the provided data.

---Goal---

Generate a response of the target length and format that responds to the user's question, summarizing all information in the provided data appropriate for the response length and format, and incorporating any relevant general knowledge.
If you don't know the answer, just say so. Do not make anything up.
Do not include information where the supporting evidence for it is not provided.
Give the response in {language}.

---Target response length and format---

Multiple Paragraphs

---Provided data---

$memory

Add sections and commentary to the response as appropriate for the length and format. Style the response in markdown.

$instruction
"""

    template_zh = _prompt_template.format(language="Chinese")
    template_en = _prompt_template.format(language="English")

    @property
    def template_variables(self) -> List[str]:
        return ["memory", "instruction"]

    def parse_response(self, response: str, **kwargs):
        logger.debug("推理器判别:{}".format(response))
        return response

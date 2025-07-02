import logging
import re
import time

from kag.common.conf import KAG_PROJECT_CONF
from kag.common.parser.logic_node_parser import extract_steps_and_actions

from kag.interface.solver.reporter_abc import ReporterABC
from kag.common.utils import extract_tag_content, remove_boxed
from kag.solver.reporter.open_spg_reporter import OpenSPGReporter

logger = logging.getLogger()


class SafeDict(dict):
    def __missing__(self, key):
        return ""


def remove_xml_tags(text):
    # 正则表达式匹配所有 XML 标签，例如：<tag> 或 </tag> 或 <tag attr="value">
    pattern = r"<[^>]+>"
    # 用空字符串替换所有匹配项
    clean_text = re.sub(pattern, "", text)
    return clean_text


def process_planning(think_str):
    result = []
    lines = think_str.split("\n")
    for l in lines:
        strip_line = l.strip()
        if strip_line == "```":
            continue
        if strip_line.lower().startswith("action"):
            result.append("```logical-form-chain")
            result.append(strip_line)
            result.append("```")
            continue

        (
            step_content,
            step_head,
            action_content,
            action_head,
        ) = extract_steps_and_actions(strip_line)
        if not step_content:
            result.append(strip_line)
            continue
        result.append(f"- {step_head}: {step_content}")
        if action_content:
            result.append(
                f"""```logical-form-chain
{action_head}: {action_content}
```"""
            )
    return "\n".join(result)


def process_tag_template(text):
    if isinstance(text, str):
        text = remove_boxed(text)
        all_tags = extract_tag_content(text)
        if len(all_tags) == 0:
            return text
        xml_tag_template = {
            "search": {
                "zh": "执行搜索:\n{content}\n",
                "en": "Execute search:\n{content}\n",
            },
            "think": {"zh": "{content}\n", "en": "{content}\n"},
            "answer": {"zh": "{content}", "en": "{content}"},
        }
        clean_text = ""
        for tag_info in all_tags:
            content = tag_info[1]
            if tag_info[0] in xml_tag_template:
                if "search" == tag_info[0]:
                    content = process_planning(content)
                clean_text += xml_tag_template[tag_info[0]][
                    KAG_PROJECT_CONF.language
                ].format_map(SafeDict({"content": content}))
            else:
                clean_text += content
        text = remove_xml_tags(clean_text)
    return text


@ReporterABC.register("kag_open_spg_reporter")
class KAGOpenSPGReporter(OpenSPGReporter):
    def __init__(self, task_id, host_addr=None, project_id=None, **kwargs):
        super().__init__(
            task_id=task_id, host_addr=host_addr, project_id=project_id, **kwargs
        )
        self.tag_mapping["begin_sub_kag_think"] = {
            "en": """

Start the {num_turns}th round of thinking

{content}""",
            "zh": """

开始第{num_turns}次思考

{content}""",
        }

    def add_report_line(self, segment, tag_name, content, status, **kwargs):
        content = process_tag_template(content)
        super().add_report_line(
            segment=segment, tag_name=tag_name, content=content, status=status, **kwargs
        )

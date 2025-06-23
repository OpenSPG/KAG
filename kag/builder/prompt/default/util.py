import json
import re
import logging

logger = logging.getLogger(__name__)


def load_knowIE_data(respond, lang="en"):
    try:
        extract_ret = json.loads(respond)
    except:
        extract_ret_str = modify_knowledge_unit(respond)
        try:
            left_pos = respond.find("{") if respond.find("{") >= 0 else 0
            right_pos = respond.rfind("}") + 1
            extract_ret_str = extract_ret_str[left_pos:right_pos].strip()
            extract_ret_str = extract_ret_str.replace("\\'", "'")
            extract_ret = json.loads(extract_ret_str)
        except:
            try:
                extract_ret_str = "{" + "{".join(respond.split("{")[1:])
                extract_ret_str = extract_ret_str.split("}\n}")[0] + "}\n}"
                pattern = r'(?<="Content": ")(.*?)(?=",\n    "Knowledge Type")'
                extract_ret_str = re.sub(
                    pattern,
                    lambda match: match.group(1).replace('"', r"\""),
                    extract_ret_str,
                )
                extract_ret = json.loads(extract_ret_str)
            except:
                try:
                    if "```json" in extract_ret_str:
                        extract_ret_str = extract_ret_str.split("```json")[1]
                    if "output:\n" in extract_ret_str:
                        extract_ret_str = extract_ret_str.split("output:\n")[1]
                    if "```" in extract_ret_str:
                        extract_ret = extract_ret_str.split("```")[0]
                    else:
                        extract_ret = extract_ret_str.replace("\\'", "'").replace(
                            '\\"', '"'
                        )  # .replace('\"Sleazy\"' ,'\\\"Sleazy\\\"').replace('\\\"Planet of the Apes\\\"' ,'Planet of the Apes') #.replace("\\", '\\\\').replace("\'", "\\\'")
                    extract_ret = json.loads(extract_ret)
                except Exception as e:
                    logger.warning(
                        f"load_knowIE_data retry2 has exception {e} {respond}",
                        exc_info=True,
                    )
                    try:
                        extract_ret = json.loads(extract_ret_str + "}")
                    except:
                        raise ValueError(
                            "the output KnowUnit str is invalid: " + respond
                        )
    return extract_ret


def load_NER_data(respond):
    try:
        extract_ret_str = respond.replace(
            'Before" trilogy,', 'Before trilogy",'
        ).replace('I"s', "I's")
        if "```json" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("```json")[1]
        if "output:" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("output:")[1]
        if "```" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("```")[0]
        extract_ret_str = extract_ret_str.replace("\\'", "'")
        extract_ret = json.loads(extract_ret_str)
    except:
        try:
            extract_ret_str = "[" + "[".join(extract_ret_str.split("[")[1:])
            extract_ret_str = "]".join(extract_ret_str.split("]")[:-1]) + "]"
            extract_ret = json.loads(extract_ret_str)
        except:
            try:
                extract_ret_str = extract_ret_str.strip() + "}]"
                extract_ret = json.loads(extract_ret_str)
            except:
                raise ValueError("the output NER str is invalid: " + respond)
    return extract_ret


def load_SPO_data(respond):
    extract_ret_str = respond
    try:
        if "output:\n" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("output:\n")[1]
        if "```json\n" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("```json\n")[1]
        if "\n```" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("\n```")[0]
        if "input:\n" in extract_ret_str:
            extract_ret_str = extract_ret_str.split("input:\n")[0]
        extract_ret_str = extract_ret_str.replace("\\'", "'")
        rst = check_data(extract_ret_str, "spo", "zh")
        if rst and len(rst) > 0:
            return rst
        else:
            return []
            # raise ValueError("the output SPO str is invalid: " + respond)

    except:
        matches = re.findall(r"\[([^[\[\]].*)\]", extract_ret_str)
        unique2quadruple = {}

        for ele in matches:
            ele = (
                ele.strip()
                .strip("[")
                .strip("]")
                .replace(" ", "")
                .strip('"')
                .strip('",')
                .strip('"')
            )
            quadruple = [
                sub.strip('"').strip(",").strip("'") for sub in ele.split('","')
            ]
            if len(quadruple) == 4:
                unique2quadruple["-".join(quadruple)] = quadruple
            elif len(quadruple) == 3:
                unique2quadruple["-".join(quadruple)] = quadruple + [""]

            rst = list(unique2quadruple.values())
            if len(rst) > 0:
                return rst
            else:
                for quanple in extract_ret_str.split("]"):
                    try:
                        content = quanple.split("[")[1]
                        quadruple = [
                            ele.strip().strip('"').strip("'")
                            for ele in content.replace("\", '", '", "')
                            .replace("', \"", '", "')
                            .replace("', '", '", "')
                            .split('", "')
                        ]
                        if len(quadruple) == 4:
                            unique2quadruple["-".join(quadruple)] = quadruple
                        elif len(quadruple) == 3:
                            unique2quadruple["-".join(quadruple)] = quadruple + [""]
                        elif len(quadruple) == 5:
                            unique2quadruple["-".join(quadruple)] = [
                                quadruple[0],
                                quadruple[1],
                                quadruple[2] + " " + quadruple[3],
                                quadruple[4],
                            ]
                    except:
                        continue
                rst = list(unique2quadruple.values())
                if len(rst) > 0:
                    return rst
                else:
                    return []
                    # raise ValueError("the output SPO str is invalid: " + respond)


def modify_knowledge_unit(text, lang="zh"):
    # 定义正则表达式模式
    if lang == "zh":
        pattern = r'"知识点\d+名称"\s*:\s*"([^"]+)"\s*,'
    else:
        pattern = r'"knowledge unit \d+ Name"\s*:\s*"([^"]+)",'
    modified_text = re.sub(pattern, r'"\1":', text)
    return modified_text


def check_data(line, data_type="knowIE", language="zh"):
    try:
        info = json.loads(line)
    except Exception as e:
        logger.warning(f"check_data retry0 has exception {e} {line}", exc_info=True)
        try:
            info = json.loads(line.replace("```json", "").replace("\n``", ""))
        except Exception as e:
            logger.warning(f"check_data retry1 has exception {e} {line}", exc_info=True)
            try:
                info = json.loads(
                    line.replace("```json", "")
                    .replace("\n``", "")
                    .replace("\\", "\\\\")
                )
            except Exception as e:
                logger.warning(
                    f"check_data retry2 has exception {e} {line}", exc_info=True
                )
                return None
    if data_type == "knowIE":
        if not isinstance(info, dict):
            return None
        check_data = {}
        for name in info:

            if (
                language == "zh"
                and "知识点" not in name
                and len(
                    set(info[name].keys())
                    & set(
                        [
                            "内容",
                            "知识类型",
                            "结构化内容",
                            "领域本体",
                            "核心实体",
                            "关联问",
                            "扩展知识点",
                        ]
                    )
                )
                >= 6
            ):
                check_data[name] = info[name]
            # elif language == "en" and "knowledge unit" not in name and lsn(set(info[name].keys()) & set([ "Name","Type", "Domain Ontology", "Description","Standard Name", "Synonyms"])) >=6:
            elif language == "en" and isinstance(info[name], dict):
                if (
                    "knowledge unit" not in name
                    and len(
                        set(info[name].keys())
                        & set(
                            [
                                "Content",
                                "Knowledge Type",
                                "Structured Content",
                                "Domain Ontology",
                                "Core Entities",
                                "Related Query",
                                "Extended Knowledge Points",
                            ]
                        )
                    )
                    >= 6
                ):
                    check_data[name] = info[name]
        if len(check_data) > 0:
            return check_data

    elif data_type == "ner":
        check_data = []
        if not isinstance(info, list):
            return None

        for ner in info:
            if language == "en" and isinstance(ner, dict):
                if (
                    len(
                        set(ner.keys())
                        & set(
                            [
                                "Name",
                                "Type",
                                "Domain Ontology",
                                "Description",
                                "Standard Name",
                                "Synonyms",
                            ]
                        )
                    )
                    == 6
                ):
                    check_data.append(ner)
            if language == "zh" and isinstance(ner, dict):
                if (
                    len(set(ner.keys()) & set(["名称", "类型", "领域本体", "解释", "标准名", "同义词"]))
                    == 6
                ):
                    check_data.append(ner)
        if len(check_data) > 0:
            return check_data

    elif data_type == "spo":
        if not isinstance(info, list):
            return None
        check_data = []
        # print(info)
        valid = {}
        for spo in info:
            try:
                if isinstance(spo, list) and (len(spo) < 3 or len(spo[1].strip()) == 0):
                    continue
                elif isinstance(spo, list) and len(spo) == 4:
                    if spo[0] == spo[3]:
                        spo[3] = ""
                    valid["_".join(spo)] = spo
                elif isinstance(spo, list) and len(spo) == 3:
                    spo = spo + [""]
                    valid["_".join(spo)] = spo
            except Exception as e:
                logger.warning(
                    f"check_data spo parsed. has exception {e} {spo}", exc_info=True
                )
                continue
        check_data = list(valid.values())
        if len(check_data) > 0:
            return check_data
    return None

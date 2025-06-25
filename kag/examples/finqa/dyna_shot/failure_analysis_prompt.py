import logging
from typing import List

from kag.interface import PromptABC

logger = logging.getLogger(__name__)


@PromptABC.register("finqa_falure_analysis")
class FinQAFalureAnalysisPrompt(PromptABC):
    template_zh = """
# 任务
你是财经领域的专家，你的任务是根据正确答案，分析错题原因，并总结改进方法。

# 要求
1. 不要质疑正确答案。
2. 将错误原因进行分类，在这些类型中选择一个：['无召回数据', '数值提取错误', '计算公式错误']
3. 归纳出泛化能力强的方法，使得类似问题不再出错。

## 输出内容和格式
先输出你的分析和思考，最后按如下格式输出：
```
<type>错误分类</type>
<keywords>此类错误的关键字</keywords>
<ImprovementMethods>改进方法</ImprovementMethods>
```

## 归纳思路
1. 如果无召回，可能是问题中相关信息给错了，根据召回数据，改写题目中的关键信息。
2. 如果召回正确，但是提取了错误的数值，根据金融知识分析为什么会提取错误的数值。
3. 如果计算公式错误，总结出正确的公式。

# 参考例子
## 题目
what is the range of height of monopole towers , in feet?
## 参考信息
monopoles typically have heights ranging from 50 to 200 feet .
## 正确答案
计算公式：subtract(200, 50)，结果：150
## 错误答案
50至200
## 案例输出结果
<type>计算公式错误</type>
<keywords>the range of, what is</keywords>
<ImprovementMethods>问题中出现的the range of不是要求回答范围的最大最小值，而是回答范围的差值。 </ImprovementMethods>

# 题目
$question

# 正确答案
## 召回信息
$gold_inds
## 计算过程
$program_re
## 结果
$gold

# 错题
## 子问题以及召回信息
```
$memory
```
## math算子使用的python代码
```python
$code
```
## 错题结果
$prediction

使用中文输出你的分析和结果：
""".strip()

    template_en = template_zh

    @property
    def template_variables(self) -> List[str]:
        return [
            "question",
            "gold_inds",
            "program_re",
            "memory",
            "code",
            "gold",
            "prediction",
        ]

    def parse_response(self, response: str, **kwargs):
        return response

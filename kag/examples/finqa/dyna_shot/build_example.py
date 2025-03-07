# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import os
import json
import hashlib
import shutil
import random

import pandas as pd
from neo4j import GraphDatabase

from kag.builder.runner import BuilderChainRunner
from kag.common.conf import KAG_CONFIG


def load_finqa_train_data(shuffle: bool = False) -> list:
    """
    load data
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = os.path.join(current_dir, "..", "builder", "data", "train.json")
    with open(file_name, "r", encoding="utf-8") as f:
        data_list = json.load(f)
    print("finqa data list len " + str(len(data_list)))
    for _idx, data in enumerate(data_list):
        data["index"] = _idx
    return data_list

prompt = """
问题分类：
yes or no问题。

数值问题。
1. percentage increase from A to B
    percentage of 
    percentage decrease
2. ratio of X to Y


3. 时间序列分析（Time Series Analysis） 这类问题涉及对一段时间内的数据进行分析，包括趋势、平均值或累计值。

4. 预测与推断（Forecasting and Extrapolation） 这类问题基于现有数据预测未来趋势或结果。

5. 最大最小
- 最小损失，因为数值是负数，用max

6. 差异
difference between
In comparison to A,  how much percentage

7. What was the change，有何变化，减法，同6


易错题：
1. the computation of diluted earnings per common share excluded 8.0 million , 13.4 million , and 14.7 million stock options for the years ended december 31 , 2012 , 2011 , and 2010 
for the years ended december 31，表示的是最后一天。
问题问题2012，对应的值应该是 ended december 31, 2011

2. from to时，有lower hightest干扰，导致计算方向错误。

3. 
"""

if __name__ == "__main__":
    _data_list = load_finqa_train_data()
    q_list = []
    for i, _item in enumerate(_data_list):
        _question = _item["qa"]["question"]
        q_list.append(_question)
    random.shuffle(q_list)
    q_list = q_list[:100]
    print("\n".join(q_list))

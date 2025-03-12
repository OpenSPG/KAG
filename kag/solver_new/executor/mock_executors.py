# -*- coding: utf-8 -*-
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
from kag.interface import ExecutorABC


@ExecutorABC.register("mock_retriever_executor")
class MockRetrieverExecutor(ExecutorABC):
    def invoke(self, query, task, context, **kwargs):
        result = [
            "截至2025年3月12日，余额宝的七日年化收益率为1.39%‌‌。这一收益率在过去几年中经历了显著下降。例如，2024年初时余额宝的7日年化收益率可能在2%左右，但随后逐步下降，到2025年1月12日首次跌破1.2%，创下成立以来的最低值‌。",
            "余额宝的收益率波动主要受市场利率环境的影响。货币基金的收益率通常与市场利率紧密相关，而市场利率的变化受多种经济因素影响，包括货币政策、市场流动性和经济周期等‌。因此，投资者在选择理财产品时，需要关注这些因素的变化，以判断收益率的未来趋势",
        ]
        task.result = result
        return result

    async def ainvoke(self, query, task, context, **kwargs):
        return self.invoke(query, task, context, **kwargs)

    def schema(self):
        return {
            "name": "Retriever",
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "User-provided query for retrieval.",
                    },
                },
            },
        }


@ExecutorABC.register("mock_math_executor")
class MockMathExecutor(ExecutorABC):
    def invoke(self, query, task, context, **kwargs):
        math_expr = task.arguments["query"]
        result = eval(math_expr.replace("%", "/100"))
        task.result = result
        return result

    async def ainvoke(self, query, task, context, **kwargs):
        return self.invoke(query, task, context, **kwargs)

    def schema(self):
        return {
            "name": "Math",
            "description": "Given a mathematical expression that conforms to Python syntax, perform the mathematical calculation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The user's input expression needs to conform to Python syntax.",
                    },
                },
            },
        }

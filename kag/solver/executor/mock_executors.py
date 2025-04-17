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

from kag.interface import ExecutorABC, Task, Context, LLMClient


@ExecutorABC.register("mock_retriever_executor")
class MockRetrieverExecutor(ExecutorABC):
    @property
    def category(self):
        return "Retriever"

    def invoke(self, query: str, task: Task, context: Context, **kwargs):
        """Retrieval of user query from a knowledge base.

        Args:
            query: User query triggering the retrieval
            task: Task instance containing execution parameters
            context: Pipeline execution context with dependency tracking
            **kwargs: Additional execution parameters

        Returns:
            List of strings containing mock financial data entries
        """
        result = [
            "截至2025年3月12日，余额宝的七日年化收益率为1.39%‌‌。这一收益率在过去几年中经历了显著下降。例如，2024年初时余额宝的7日年化收益率可能在2%左右，但随后逐步下降，到2025年1月12日首次跌破1.2%，创下成立以来的最低值‌。",
            "余额宝的收益率波动主要受市场利率环境的影响。货币基金的收益率通常与市场利率紧密相关，而市场利率的变化受多种经济因素影响，包括货币政策、市场流动性和经济周期等‌。因此，投资者在选择理财产品时，需要关注这些因素的变化，以判断收益率的未来趋势",
        ]
        task.result = result
        return result

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        """Asynchronous retrieval of user query from a knowledge base.

        Args:
            query: User query triggering the retrieval
            task: Task instance containing execution parameters
            context: Pipeline execution context with dependency tracking
            **kwargs: Additional execution parameters

        Returns:
            List of strings containing mock financial data entries
        """

        return self.invoke(query, task, context, **kwargs)

    def schema(self):
        return {
            "name": "Retriever",
            "description": "Retrieve relevant knowledge from the local knowledge base.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "User-provided query for retrieval.",
                    "optional": False,
                },
            },
        }


@ExecutorABC.register("mock_math_executor")
class MockMathExecutor(ExecutorABC):
    """Given a mathematical expression that conforms to Python syntax, perform the mathematical calculation."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.prompt = """
根据问题生成可执行Python代码(需要import所有的依赖包)，最后一行用`print`输出结果。代码需简洁无注释，仅返回代码，不要其他内容。


**示例说明:**  
用户问题：计算1到100的和。  
模型返回：  
```python
s = sum(range(1, 101))
print(s)
```  

用户问题：

        """

    @property
    def category(self):
        return "Math"

    async def gen_py_code(self, query: str):
        prompt = f"{self.prompt}\n{query}"
        out = await self.llm.acall(prompt)
        return out.lstrip("```python").rstrip("```")

    def run_py_code(self, code):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            exec(code)
        output = f.getvalue().strip()
        return output

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        """Asynchronous wrapper for synchronous invocation (runs in default threadpool).

        Args:
            query: Original mathematical query
            task: Task containing the mathematical expression
            context: Execution context
            **kwargs: Additional execution parameters

        Returns:
            Result from synchronous invocation
        """
        try:
            math_expr = task.arguments["query"]
            result = eval(math_expr.replace("%", "/100"))
            task.result = result
            return result
        except:
            py_code = await self.gen_py_code(task.arguments["query"])
            print(f"py_code = {py_code}")
            result = self.run_py_code(py_code)
            task.result = result

    def schema(self):
        return {
            "name": "Math",
            "description": "Perform mathematical calculations based on user input and return the result. The user input can be a valid mathematical expression or a problem described in natural language.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The user inputs a string, which will be executed directly if it is a valid Python expression; otherwise, it will be translated into Python code before execution.",
                    "optional": False,
                }
            },
        }


@ExecutorABC.register("mock_code_executor")
class MockCodeExecutor(ExecutorABC):
    """Given a mathematical expression that conforms to Python syntax, perform the mathematical calculation."""

    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.prompt = """
根据问题生成可执行Python代码(需要import所有的依赖包)，最后一行用`print`输出结果。代码需简洁无注释，仅返回代码，不要其他内容。


**示例说明:**  
用户问题：计算1到100的和。  
模型返回：  
```python
s = sum(range(1, 101))
print(s)
```  

用户问题：

        """

    @property
    def category(self):
        return "Code"

    async def gen_py_code(self, query: str):
        prompt = f"{self.prompt}\n{query}"
        out = await self.llm.acall(prompt)
        return out.lstrip("```python").rstrip("```")

    def run_py_code(self, code):
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            exec(code)
        output = f.getvalue().strip()
        return output

    async def ainvoke(self, query: str, task: Task, context: Context, **kwargs):
        """Asynchronous wrapper for synchronous invocation (runs in default threadpool).

        Args:
            query: Original mathematical query
            task: Task containing the mathematical expression
            context: Execution context
            **kwargs: Additional execution parameters

        Returns:
            Result from synchronous invocation
        """
        try:
            math_expr = task.arguments["query"]
            result = eval(math_expr.replace("%", "/100"))
            task.result = result
            return result
        except:
            py_code = await self.gen_py_code(task.arguments["query"])
            print(f"py_code = {py_code}")
            result = self.run_py_code(py_code)
            task.result = result

    def schema(self):
        return {
            "name": "Code",
            "description": "Perform mathematical calculations based on user input and return the result. The user input can be a valid mathematical expression or a problem described in natural language.",
            "parameters": {
                "query": {
                    "type": "string",
                    "description": "The user inputs a string, which will be executed directly if it is a valid Python expression; otherwise, it will be translated into Python code before execution.",
                    "optional": False,
                }
            },
        }

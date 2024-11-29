import sympy as sp
from sympy import FiniteSet, Symbol

from kag.solver.logic.core_modules.op_executor.op_math.sympy_math.custom_function import evaluate_expression

if __name__ == "__main__":

    expression = "Abs(-100) + count(A) + 100"
    t = [1, 2, 3, 4, 5]
    data_dict = {
        'A': FiniteSet(*t)
    }

    try:
        result = evaluate_expression(expression, data_dict)

        print(f"Expression: {expression}")
        print(f"Data: {data_dict}")
        print(f"Result: {result}")
    except NotImplementedError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred: {e}")

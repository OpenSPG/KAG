import sympy as sp
from kag.solver.logic.core_modules.op_executor.op_math.sympy_math.unary.unary_set_op import CountSet, SumSet, \
    AverageSet, MaxSet, MinSet, AbsSet

# Dictionary of custom functions for sympy
from sympy import Basic

custom_functions = {
    'count': CountSet(),
    'sum': SumSet(),
    'average': AverageSet(),
    'max': MaxSet(),
    'min': MinSet(),
    'abs': AbsSet()
}

custom_functions_call = {
    'count': CountSet().process,
    'sum': SumSet().process,
    'average': AverageSet().process,
    'max': MaxSet().process,
    'min': MinSet().process,
    'abs': AbsSet().process
}

def evaluate_expression_eval(expression, data_dict):
    """
    Evaluates a mathematical expression using SymPy and custom functions.

    :param expression: A string representing the mathematical expression to be evaluated.
    :param data_dict: A dictionary containing variable names and their corresponding values.
    :return: The result of the evaluated expression.
    """
    data_dict.update(custom_functions_call)
    result = eval(expression, data_dict)

    return result

def evaluate_expression_sympy(expression, data_dict):
    """
    Evaluates a mathematical expression using SymPy and custom functions.

    :param expression: A string representing the mathematical expression to be evaluated.
    :param data_dict: A dictionary containing variable names and their corresponding values.
    :return: The result of the evaluated expression.
    """
    # Parse the expression using SymPy
    expr = sp.sympify(expression)

    # Extract variables from the data dictionary
    variables = {sp.Symbol(key): value for key, value in data_dict.items()}

    # Substitute the variables into the expression
    result = expr.subs(variables)

    # Process custom functions in the result
    for func_name, func in custom_functions.items():
        if func_name in str(result):
            result = result.replace(sp.Function(func_name), lambda *args: func.process(*args))
    if isinstance(result, Basic):
        # Check if all functions in the result are implemented
        for func in result.atoms(sp.Function):
            if func.func.__name__ not in custom_functions:
                raise NotImplementedError(f"Function '{func.func.__name__}' is not implemented.")

    return result

def evaluate_expression(expression, data_dict):
    return evaluate_expression_eval(expression, data_dict)
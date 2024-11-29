from sympy import Symbol


class UnarySetOp:
    """
    Base class for unary set operations.
    """

    def __init__(self):
        """
        Initializes the base unary set operation.
        """
        self.op_name = 'base'

    def pre_check(self, A):
        """
        Pre-checks the input to ensure it is valid.

        :param A: The input set or symbol.
        :raises ValueError: If the input is a symbolic variable.
        """
        if isinstance(A, Symbol):
            raise ValueError(f"Undefined variables: {A}")

    def do_process(self, A):
        """
        Abstract method to perform the specific operation on the input set.

        :param A: The input set.
        :raises NotImplementedError: If the operation is not implemented.
        """
        raise NotImplementedError(f"{self.op_name} is not implemented")

    def process(self, A):
        """
        Processes the input set by performing the pre-check and then the specific operation.

        :param A: The input set.
        :return: The result of the operation.
        """
        self.pre_check(A)
        return self.do_process(A)


class CountSet(UnarySetOp):
    """
    Class for counting the number of elements in a set.
    """

    def __init__(self):
        """
        Initializes the count set operation.
        """
        super(CountSet, self).__init__()
        self.op_name = "count"

    def do_process(self, A):
        """
        Counts the number of elements in the input set.

        :param A: The input set.
        :return: The number of elements in the set.
        """
        return len(A)


class SumSet(UnarySetOp):
    """
    Class for summing the elements in a set.
    """

    def __init__(self):
        """
        Initializes the sum set operation.
        """
        super(SumSet, self).__init__()
        self.op_name = "sum"

    def do_process(self, A):
        """
        Sums the elements in the input set.

        :param A: The input set.
        :return: The sum of the elements in the set.
        """
        return sum(A)


class AverageSet(UnarySetOp):
    """
    Class for computing the average of elements in a set.
    """

    def __init__(self):
        """
        Initializes the average set operation.
        """
        super(AverageSet, self).__init__()
        self.op_name = "average"

    def do_process(self, A):
        """
        Computes the average of the elements in the input set.

        :param A: The input set.
        :return: The average of the elements in the set.
        :raises ValueError: If the input set is empty.
        """
        if len(A) == 0:
            raise ValueError("Cannot compute average of an empty set")
        return sum(A) / len(A)


class MaxSet(UnarySetOp):
    """
    Class for finding the maximum element in a set.
    """

    def __init__(self):
        """
        Initializes the max set operation.
        """
        super(MaxSet, self).__init__()
        self.op_name = "max"

    def do_process(self, A):
        """
        Finds the maximum element in the input set.

        :param A: The input set.
        :return: The maximum element in the set.
        :raises ValueError: If the input set is empty.
        """
        if len(A) == 0:
            raise ValueError("Cannot compute max of an empty set")
        return max(A)


class MinSet(UnarySetOp):
    """
    Class for finding the minimum element in a set.
    """

    def __init__(self):
        """
        Initializes the min set operation.
        """
        super(MinSet, self).__init__()
        self.op_name = "min"

    def do_process(self, A):
        """
        Finds the minimum element in the input set.

        :param A: The input set.
        :return: The minimum element in the set.
        :raises ValueError: If the input set is empty.
        """
        if len(A) == 0:
            raise ValueError("Cannot compute min of an empty set")
        return min(A)


class AbsSet(UnarySetOp):
    """
    Class for computing the absolute values of elements in a set.
    """

    def __init__(self):
        """
        Initializes the abs set operation.
        """
        super(AbsSet, self).__init__()
        self.op_name = "abs"

    def do_process(self, A):
        """
        Computes the absolute values of the elements in the input set.

        :param A: The input set.
        :return: A set of absolute values of the elements in the input set.
        """
        return {abs(x) for x in A}

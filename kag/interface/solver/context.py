import networkx as nx
from collections import OrderedDict
from kag.interface.solver.planner_abc import Task
from kag.interface.solver.model.one_hop_graph import KgGraph


class Context:
    """Pipeline execution context that tracks tasks and their dependencies."""

    def __init__(self):
        """Initializes an ordered dictionary to store tasks in insertion order."""

        self._tasks = OrderedDict()
        self.variables_graph = KgGraph()
        self.kwargs = {}

    def add_task(self, task: Task):
        """Adds a task to the context.

        Args:
            task: Task instance to be added to the execution context.
        """
        self._tasks[task.id] = task

    def last_task(self):
        """Retrieves the most recently added task.

        Returns:
            The last task in the execution order, or None if no tasks exist.
        """
        if len(self._tasks) == 0:
            return None
        last_id = list(self._tasks.keys())[-1]
        return self._tasks[last_id]

    def append_task(self, task: Task):
        """Appends a new task and automatically sets its parent to the last task.

        Used for iterative planning where new tasks depend on the latest execution state.
        Automatically adds parent dependency only if the task has no existing parents.

        Args:
            task: Task to append to the execution sequence.
        """
        if len(task.parents) == 0 and len(self._tasks) > 0:
            task.parents = [self.last_task()]
        self.add_task(task)

    def get_task(self, task_id: str):
        """Retrieves a task by its unique identifier.

        Args:
            task_id: Unique identifier of the task to retrieve.

        Returns:
            The requested task if found, otherwise None.
        """
        return self._tasks.get(task_id)

    def topological_sort(self, dag: nx.DiGraph):
        """Performs topological sort on a directed acyclic graph (DAG).

        Args:
            dag: NetworkX graph representing task dependencies.

        Returns:
            Generator yielding node IDs in topological order.
        """
        return nx.topological_sort(dag)

    def topological_generations(self, dag: nx.DiGraph):
        """Generates topological generations (parallelizable task groups).

        Args:
            dag: NetworkX graph representing task dependencies.

        Returns:
            Generator yielding lists of node IDs that can be executed in parallel.
        """
        return nx.topological_generations(dag)

    def get_dag(self):
        """Constructs a directed acyclic graph (DAG) of task dependencies.

        Verifies all referenced tasks exist in the context. Raises ValueError if any
        dependency references a non-existent task.

        Returns:
            A NetworkX DiGraph representing the task dependency structure.

        Raises:
            ValueError: If a task referenced in dependencies does not exist.
        """
        dag = nx.DiGraph()
        nodes = set()
        for task_id, task in self._tasks.items():
            nodes.add(task_id)
            for dep in task.parents:
                nodes.add(dep.id)
        for node in nodes:
            if node not in self._tasks:
                raise ValueError(f"task {node} not found.")
        dag.add_nodes_from(nodes)
        for task_id, task in self._tasks.items():
            for dep in task.parents:
                dag.add_edge(dep.id, task_id)
        self.topological_sort(dag)
        return dag

    def gen_task(self, group: bool = False):
        """Generates tasks in execution order, optionally grouped by parallelizable stages.

        Args:
            group: If True, yields lists of tasks that can be executed in parallel.
                   If False (default), yields individual tasks sequentially.

        Returns:
            Generator yielding either individual Task objects or lists of Tasks,
            depending on the 'group' parameter.

        Raises:
            NetworkXUnfeasible: If the task dependency graph contains cycles.
        """
        dag = self.get_dag()
        if not group:
            nodes = self.topological_sort(dag)
            for node in nodes:
                yield self._tasks[node]
        else:
            node_groups = self.topological_generations(dag)
            for node_group in node_groups:
                yield [self._tasks[node] for node in node_group]

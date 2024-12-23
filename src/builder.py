from collections.abc import Callable, Iterable, MutableMapping, Sequence
from operator import add, mul
from graphkit import compose, operation
from graphkit.base import Operation
from graphkit.network import DataPlaceholderNode
from io import BytesIO
from .node import Node


import math
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import os
import sys
import pydot


class InvalidNodeArgument(Exception):
    """
    Used for attempts to add operations on invalid nodes.

    Currently used to represent attempts to add operations on nodes that aren't
    defined in the current graph.
    """
    def __init__(self, message):
        super().__init__(message)


class UnsupportedPlotFileExtension(Exception):
    """
    Used for attempts to create a plot file with an unsupported file extension.
    """
    def __init__(self, message):
        super().__init__(message)


# Computational graph builder that supports basic operations like addition and
# multiplication. Also allows for assertions on equality between nodes and setting
# "hints" in the graph, which allow clients to run arbitrary functions in the graph.
# Currently supports ints and floats, but not complex numerical types.
class Builder:
    """
    A wrapper around graphkit for computational graphs.
     
    This class abstracts away tracking nodes and handling operations with relationships
    defined between nodes in a computational graph. Provides convenience functions for
    basic operations like addition and multiplcation. Also allows for assertions on equality
    between nodes and setting "hints" in the graph, which allow clients to run arbitrary
    functions in the graph.

    Each function that adds a node or operation in the graph allows setting a human-readable
    name on the node and/or operation. The names are used as labels in a graph that can rendered
    by calling the plot() function.

    ...

    Attributes
    ----------
    current_id : int
        ID of the node that is guaranteed to be unique within a Builder graph - increments on
        addition of any new node
    current_operation_id : int
        ID of the operation that is guaranteed to be unique within a Builder graph - increaments
        on addition of any new operation
    operations : list[Operation]
        the list of operations that will be computed within the graph
    assertion_node_id_to_nodes : MutableMapping[str, list[Node | int | float]]
        mapping of the Node ID of an assertion node to its list of nodes operands - used for outputting
        human-readable node labels of its operand nodes
    inputs : MutableMapping[str, int | float | None]
        mapping of Node ID to input values
    nodes : set[Node]
        set of all Nodes in the graph - used to guarantee uniqueness of nodes to the graph
    node_id_to_label : MutableMapping[str, str]
        label of node ID to its human-readable label - used for populating labels in the
        human-viewable output graph

    Methods
    -------
    init(self, name: str | None = None) -> Node
        Creates a node in the graph that should be defined by the client before computation
    constant(self, value: int | float, name: str | None = None) -> Node
        Defines a node with a constant value in the graph
    add(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None) -> Node
        Creates an add operation in the graph between two nodes (will automatically convert a constant arg to a node)
    mul(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None) -> Node
        Creates a mul operation in the graph between two nodes (will automatically convert a constant arg to a node)
    assert_equal(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None) -> Node
        Defines an equality operation in the graph between two nodes (will automatically convert a constant arg to a node)
    hint(self, fn: Callable, nodes: Sequence[int | float | Node], name: str | None = None, op_name: str | None = None) -> Node
        Allows the user to call a custom function on the computational graph as an operation
    fill_nodes(self, inputs: MutableMapping[Node, int | float]) -> None
        Sets a mapping of the nodes to their input values
    check_constraints(self) -> bool
        Runs the graph and checks any assertions and the validity of the graph
    get_graph_results(self) -> dict[str, int | float | bool] | None
        Runs the graph and outputs the results of each node. Also internally validates the graph.
    plot(self, filename: str | None = None) -> pydot.Dot
        Runs the graph and renders the graph to the filename, if given

    """
    current_id: int
    current_operation_id: int
    operations: list[Operation]
    assertion_node_id_to_nodes: MutableMapping[str, list[Node | int | float]]
    inputs: MutableMapping[str, int | float | None]
    nodes: set[Node]
    node_id_to_label: MutableMapping[str, str]

    def __init__(self):
        self.current_id = 0
        self.current_operation_id = 0
        self.operations = []
        self.assertion_node_id_to_nodes = {}
        self.inputs = {}
        self.nodes = set()
        self.node_id_to_label = {}

    def __equal__(self, a: int | float, b: int | float) -> bool:
        # Checks equality of two numbers. The default tolerance is 1e-09 - https://docs.python.org/3/library/math.html#math.isclose.
        return math.isclose(a, b)

    def __check_operation__(self, nodes: Sequence[int | float | Node], op_name: str) -> None:
        # Validates that the given nodes for an operation are in the graph.
        for node in nodes:
            if type(node) is Node and node not in self.nodes:
                raise InvalidNodeArgument(f"Node {node.get_name()} isn't in graph. Unable to add the {op_name} operation.")

    def __add_node__(self, name: str | None = None) -> Node:
        # Adds a node to the current graph.
        node = Node(str(self.current_id), name=name)
        self.current_id += 1
        self.node_id_to_label[node.id] = node.get_name()
        self.nodes.add(node)
        return node

    def __maybe_add_constant_nodes__(self, nodes: Sequence[int | float | Node]) -> Sequence[Node]:
        # Converts any int or constant values in the list of nodes to Constant nodes.
        nodes_with_constants = []

        for maybe_constant in nodes:
            if type(maybe_constant) in (int, float):
                constant_node = self.constant(maybe_constant, name=str(maybe_constant))  # type: ignore[arg-type]
                nodes_with_constants.append(constant_node)
            else:
                nodes_with_constants.append(maybe_constant)  # type: ignore[arg-type]

        return nodes_with_constants

    def __add_operation__(self, operands: Sequence[int | float | Node], result_node: Node, fn: Callable, op_id: str, op_name: str | None = None) -> None:
        # Adds an operation to the current graph.
        op_name = op_name if op_name else op_id
        nodes = self.__maybe_add_constant_nodes__(operands)
        node_ids = [node.id for node in nodes]

        self.operations.append(operation(
            name=op_id,
            needs=node_ids,
            provides=[result_node.id])(fn)
        )
        self.current_operation_id += 1

        # Operations are also nodes in the graph.
        self.node_id_to_label[op_id] = op_name

    def __get_graph__(self) -> compose | None:
        # Validates the graph. If valid, returns the graph composition. Otherwise, returns None.
        if len(self.operations) == 0:
            print(f"No operations in graph. Cannot run graph without any operations defined.", file=sys.stderr)
            return None

        for node_id, val in self.inputs.items():
            if val == None:
                print(f"Node {self.node_id_to_label[node_id]} is undefined. Must define node in order to check constraints.", file=sys.stderr)
                return None

        return compose(name="graph")(*self.operations)

    def __run_graph__(self, graph_composer: compose | None = None) -> dict[str, int | float | bool] | None:
        # Runs the graph and returns the output. May return None if the graph isn't valid.
        graph = graph_composer

        if graph == None:
            graph = self.__get_graph__()
        
        return None if graph == None else graph(self.inputs)

    def __check_constraints__(self, graph_composer: compose | None = None) -> bool:
        # Validates the graph, runs it, and then checks all assertions and expected values.
        computation_result = self.__run_graph__(graph_composer)

        if computation_result == None:
            return False

        satisfied_constraints = True
        
        for node_id, val in self.inputs.items():
            if val != computation_result[node_id]:
                print(f"Node {self.node_id_to_label[node_id]} has an expected value of {val}, but this does not match the calculated value of {computation_result[node_id]}")
                satisfied_constraints = False

        for node_id, operands in self.assertion_node_id_to_nodes.items():
            if not computation_result[node_id]:
                a_label = operands[0].get_name() if type(operands[0]) is Node else str(operands[0])
                b_label = operands[1].get_name() if type(operands[1]) is Node else str(operands[1])
                print(f"Node {self.node_id_to_label[node_id]} has failed assertion that node {a_label} and node {b_label} are equal.")
                satisfied_constraints = False

        return satisfied_constraints

    def init(self, name: str | None = None) -> Node:
        """Returns a new node in the graph

        The node must be defined before the graph is run.

        Parameters
        ----------
        name : str, optional
            The human-readable label of the node

        Returns
        -------
            A new node in the graph.
        """
        init_node = self.__add_node__(name=name)
        self.inputs[init_node.id] = None
        return init_node

    def constant(self, value: int | float, name: str | None = None) -> Node:
        """Returns a new node in the graph with the given constant value

        A new node is added to the graph with the given int or float value

        Parameters
        ----------
        name : str, optional
            The human-readable label of the node

        Returns
        -------
            A new node in the graph with the given constant value.
        """
        constant = self.__add_node__(name=name if name else str(value))
        self.inputs[constant.id] = value
        return constant

    def add(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None) -> Node:
        """Returns a new node in the graph for the addition operation

        Defines an addition operation on the given two nodes or constants. If the given
        a and b operands are constants, they will be converted to nodes with constant values and added
        to the graph.

        Parameters
        ----------
        a : int | float | Node
            The first operand for the add operation - constants are converted to nodes
        b : int | float | Node
            The second operand for the add operation - constants are converted to nodes
        name : str, optional
            The human-readable label of the node representing the result of the addition
        op_name : str, optional
            The human-readable label of the node representing the addition operation

        Raises
        ------
        InvalidNodeArgument
            If any of the given nodes are not in the current graph.
        Returns
        -------
            A new node in the graph representing the result of the addition operation.
        """
        operands = [a, b]
        self.__check_operation__(operands, op_name if op_name else "add")

        result_node = self.__add_node__(name=name)
        op_id = "add" + str(self.current_operation_id)
        self.__add_operation__(operands, result_node, add, op_id, op_name)
        return result_node

    def mul(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None) -> Node:
        """Returns a new node in the graph for the multiplication operation

        Defines a multiplication operation on the given two nodes or constants. If the given
        a and b operands are constants, they will be converted to nodes with constant values and added
        to the graph.

        Parameters
        ----------
        a : int | float | Node
            The first operand for the add operation - constants are converted to nodes
        b : int | float | Node
            The second operand for the add operation - constants are converted to nodes
        name : str, optional
            The human-readable label of the node representing the result of the multiplication
        op_name : str, optional
            The human-readable label of the node representing the multiplication operation

        Raises
        ------
        InvalidNodeArgument
            If any of the given nodes are not in the current graph.
        Returns
        -------
            A new node in the graph representing the result of the multiplication operation.
        """
        operands = [a, b]
        self.__check_operation__(operands, op_name if op_name else "mul")

        result_node = self.__add_node__(name=name)
        op_id = "mul" + str(self.current_operation_id)
        self.__add_operation__(operands, result_node, mul, op_id, op_name)
        return result_node

    def assert_equal(self, a: int | float | Node, b: int | float | Node, name: str | None = None, op_name: str | None = None):
        """Returns a new node in the graph for asserting equality

        Defines an equality operation on the given two nodes or constants. If the given
        a and b operands are constants, they will be converted to nodes with constant values and added
        to the graph.

        Parameters
        ----------
        a : int | float | Node
            The first operand for the add operation - constants are converted to nodes
        b : int | float | Node
            The second operand for the add operation - constants are converted to nodes
        name : str, optional
            The human-readable label of the node representing the result of the equality operation
        op_name : str, optional
            The human-readable label of the node representing the equality operation

        Raises
        ------
        InvalidNodeArgument
            If any of the given nodes are not in the current graph.
        Returns
        -------
            A new node in the graph representing the result of the equality operation.
        """
        operands = [a, b]
        self.__check_operation__(operands, op_name if op_name else "equal")

        result_node = self.__add_node__(name=name)
        self.assertion_node_id_to_nodes[result_node.id] = operands
        op_id = "equal" + str(self.current_operation_id)
        self.__add_operation__(operands, result_node, self.__equal__, op_id, op_name)

    def hint(self, fn: Callable, nodes: Sequence[int | float | Node], name: str | None = None, op_name: str | None = None) -> Node:
        """Returns a new node in the graph for the result of running the given function

        Defines an operation representing calling the given function on the given list of
        nodes. Any node in the list of nodes that is a constant will be converted to a node
        with a constant value in the graph.

        Parameters
        ----------
        fn : Callable
            The client-supplied custom function to be called on the given list of nodes
        nodes : Sequence[int | float | Node]
            The list of nodes that the fn will be called on - constants are converted to nodes
        name : str, optional
            The human-readable label of the node representing the result of the hint operation
        op_name : str, optional
            The human-readable label of the node representing the hint operation

        Raises
        ------
        InvalidNodeArgument
            If any of the given nodes are not in the current graph.
        Returns
        -------
            A new node in the graph representing the result of the hint operation.
        """
        self.__check_operation__(nodes, op_name if op_name else "hint")

        result_node = self.__add_node__(name=name)
        op_id = "hint" + str(self.current_operation_id)
        self.__add_operation__(nodes, result_node, fn, op_id, op_name)
        return result_node

    def fill_nodes(self, inputs: MutableMapping[Node, int | float]) -> None:
        """Set the values of any input nodes in the graph

        Sets the value mapping of any input nodes in the graph. Also serves as
        a convenience function for setting equality assertions, i.e. you can set
        a value mapping on any node in the graph, and it will be checked in
        check_constraints().

        Outputs any nodes not found in the graph to stderr.

        Parameters
        ----------
        inputs : MutableMapping[Node, int | float]
            The map of nodes to values
        """
        for node, val in inputs.items():
            if node not in self.nodes:
                print(f"Node {node.get_name()} isn't in graph. Cannot set its value.", file=sys.stderr)
            self.inputs[node.id] = val
            self.node_id_to_label[node.id] = self.node_id_to_label[node.id] + " = " + str(val)

    def check_constraints(self) -> bool:
        """Checks all assertions and any value expectations in the input map

        Explicitly checks all assertions defined on the graph with assert_equal(). Also checks
        any value expectations in the input map if defined in fill_nodes(). Prints out any nodes
        that don't match the expected value or any failed assertions to stdout.

        Returns
        -------
            A boolean representing whether or not all constraints were met.
        """
        return self.__check_constraints__()

    def get_graph_results(self) -> dict[str, int | float | bool] | None:
        """Outputs the results of running the graph

        Convenience function that returns the values of all nodes in the graph, including any
        computed intermediate node values. The output is a map of Node ID to value. Using
        the node ID is necessary to guarantee uniqueness of nodes within the graph.

        Returns
        -------
            A dict of node ID to their value in the graph.
        """
        return self.__run_graph__()

    def plot(self, filename: str | None = None) -> pydot.Dot:
        """Plot the graph and write it out to the given file name.

        Copied from https://github.com/yahoo/graphkit/blob/master/graphkit/network.py
        and updated for Python 3.10+

        Parameters
        ----------
        filename:
            Write the output to a png, pdf, or graphviz dot file. The extension
            controls the output format.

        Returns
        -------
            An instance of the pydot graph.

        Raises
        ------
        UnsupportedPlotFileExtension
            If the specified file extension isn't supported.

        """
        g = pydot.Dot(graph_type="digraph")

        graph_composer = self.__get_graph__()
        if not self.__check_constraints__(graph_composer):
            return g
        graph = graph_composer.net.graph

        def get_node_name(a):
            if isinstance(a, DataPlaceholderNode):
                return a
            return a.name

        # Draw nodes
        for nx_node in graph.nodes():
            name = get_node_name(nx_node)
            label = name

            if self.node_id_to_label and name in self.node_id_to_label:
                label = self.node_id_to_label[name]
            if isinstance(nx_node, DataPlaceholderNode):
                node = pydot.Node(name=nx_node, label=label, shape="rect")
            else:
                node = pydot.Node(name=name, label=label, shape="circle")
            g.add_node(node)

        # Draw edges
        for src, dst in graph.edges():
            src_name = get_node_name(src)
            dst_name = get_node_name(dst)
            edge = pydot.Edge(src=src_name, dst=dst_name)
            g.add_edge(edge)

        # Save plot
        if filename:
            basename, ext = os.path.splitext(filename)

            ext_to_img_create_fn = {
                ".png": g.create_png,
                ".jpg": g.create_jpeg,
                ".jpeg": g.create_jpeg,
                ".svg": g.create_svg,
                ".pdf": g.create_pdf,
                ".dot": g.to_string,
            }

            ext_lowered = ext.lower()
            if ext_lowered not in ext_to_img_create_fn:
                raise UnsupportedPlotFileExtension(f"Unknown file format for saving graph: {ext}")

            with open(filename, "wb") as f:
                f.write(ext_to_img_create_fn[ext_lowered]())

        return g

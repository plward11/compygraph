class Node:
    """
    A node used to represent a value or operation within a Builder graph. The node ID
    is guaranteed by the Builder to be unique within the Builder's graph. The name can be
    provided by the user and does not need to be unique. The name is used as a label
    in the generated graph.

    TODO: Consider extending the node to be aware of its operands, if any, and
    an enum for typing to support more complex use cases.

    ...

    Attributes
    ----------
    id : str
        the ID of the node that is guaranteed to be unique with a Builder graph
    name : str
        the human-readable and customizable name of the node - used to label the node
        in a generated graph

    Methods
    -------
    get_name()
        Gets the human-readable name of the node if possible, otherwise returns the
        ID of the node.
    """
    def __init__(self, id: str, name: str | None = None) -> None:
        self.id = id
        self.name = name

    def get_name(self) -> str:
        return self.name if self.name else self.id

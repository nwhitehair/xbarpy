from __future__ import annotations

from typing import Optional, Tuple


class BranchingNode:
    """
    Base class representing a node within a tree.
    Each node has slots for up to two child nodes, and each slot is specified by an index
    (`0` or `1`).
    Empty slots are occupied by `None`.
    """
    _node_subclasses_by_name = {} # noqa: RUF012

    def __init__(self, parent: Optional[BranchingNode] = None,
                 child0: Optional[BranchingNode] = None, child1: Optional[BranchingNode] = None):
        self._children = [None, None]
        self._set_parent(parent=parent)
        self.set_child(child0, 0)
        self.set_child(child1, 1)

    def _set_parent(self, parent: BranchingNode):
        self._parent = parent

    def set_child(self, child_node: Optional[BranchingNode], index: int):
        if index not in (0, 1):
            raise ValueError(f"Child node index must be either 0 or 1 (got {index}).")
        self._children[index] = child_node
        if isinstance(child_node, BranchingNode):
            child_node._set_parent(self)

    def get_child(self, index: int) -> Optional[BranchingNode]:
        if index not in (0, 1):
            raise ValueError(f"Child node index must be either 0 or 1 (got {index}).")
        self._children[index]

    @property
    def parent(self) -> Optional[BranchingNode]:
        return self._parent

    @property
    def is_root(self) -> bool:
        return self._parent is not None

    @property
    def is_terminal(self) -> bool:
        return len(self.children) == 0

    @property
    def children(self) -> Tuple[BranchingNode, BranchingNode]:
        children = tuple(self._children)
        return children

    def __init_subclass__(cls):
        BranchingNode._node_subclasses_by_name[cls.__name__] = cls

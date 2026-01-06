import dataclasses
from typing import Callable, Generic, Iterable, Iterator, TypeVar

V = TypeVar("V")  # type for graph vertices


@dataclasses.dataclass(frozen=True)
class RootedTreeNode(Generic[V]):
    node: V
    children: list["RootedTreeNode[V]"]

    def get_leaves(self) -> Iterator[V]:
        if self.children:
            for child in self.children:
                yield from child.get_leaves()
        else:
            yield self.node

    @classmethod
    def build(
        cls, node: V, children_getter: Callable[[V], Iterable[V]], max_depth: int
    ) -> "RootedTreeNode[V]":
        if max_depth == 0:
            return cls(node=node, children=[])
        else:
            children = children_getter(node)
            return cls(
                node=node,
                children=[cls.build(child, children_getter, max_depth - 1) for child in children],
            )

    def is_leaf(self) -> bool:
        return not self.children

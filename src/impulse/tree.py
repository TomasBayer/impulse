from __future__ import annotations

import dataclasses
import functools
import itertools
from typing import Callable, Iterable, Iterator

from impulse import dotfile


@dataclasses.dataclass(frozen=True)
class ModuleTreeNode:
    """
    Node in a module tree.

    Stores a module path and its child module trees.
    """

    module_path: str
    children: frozenset[ModuleTreeNode]

    @property
    def module_name(self) -> str:
        return f".{self.module_path.split('.')[-1]}"

    def is_leaf(self) -> bool:
        return not self.children

    def get_leaves(self) -> Iterator[str]:
        if self.is_leaf():
            yield self.module_path
        else:
            for child in self.children:
                yield from child.get_leaves()

    @functools.cached_property
    def leaves(self) -> frozenset[str]:
        return frozenset(self.get_leaves())

    @classmethod
    def build_children(
        cls,
        children: Iterable[str],
        children_getter: Callable[[str], Iterable[str]],
        max_depth: int,
    ) -> ModuleTreeNode:
        return cls(
            "ROOT", frozenset(cls.build(child, children_getter, max_depth) for child in children)
        )

    @classmethod
    def build(
        cls, root_module_path: str, children_getter: Callable[[str], Iterable[str]], max_depth: int
    ) -> ModuleTreeNode:
        """
        Recursively build a module tree up to a specified maximum depth.

        Modules that are not packages become leaves. Packages below the maximum depth include their submodules as
        children. Packages at the maximum depth have their children ignored and becomes leaves, too.
        """
        if max_depth <= 0:
            return cls(module_path=root_module_path, children=frozenset())
        else:
            children = children_getter(root_module_path)
            return cls(
                module_path=root_module_path,
                children=frozenset(
                    cls.build(child, children_getter, max_depth - 1) for child in children
                ),
            )

    def build_dot_graph(
        self,
        has_edge: Callable[[str, str], bool],
        build_edge: Callable[[str, str], dotfile.Edge],
        build_dotgraph: Callable[[str], dotfile.DotGraph],
    ) -> dotfile.DotGraph:
        """
        Build a DotGraph representing the entire module tree.

        Leaves of the tree become nodes in the graph, and edges are added between leaf nodes according to the
        `has_edge` predicate.
        """
        return self._build_dot_graph(
            available_edges={
                (upstream, downstream)
                for upstream, downstream in itertools.permutations(self.leaves, r=2)
                if has_edge(upstream, downstream)
            },
            build_edge=build_edge,
            build_dotgraph=build_dotgraph,
            depth=0,
        )

    def _build_dot_graph(
        self,
        available_edges: set[tuple[str, str]],
        build_edge: Callable[[str, str], dotfile.Edge],
        build_dotgraph: Callable[[str], dotfile.DotGraph],
        depth: int,
    ) -> dotfile.DotGraph:
        """
        Recursively build a DotGraph for this subtree. Helper to be used by `build_dotgraph`.

        When called from `build_dotgraph`, `available_edges` contains all valid leaf-to-leaf edges in the entire
        module tree. The set is shared and mutated across recursive calls to this function. At lower levels,
        it may contain edges whose endpoints lie partially or entirely outside this subtree.

        Algorithm (edge ownership model):
        - Each subtree is responsible for adding edges whose both endpoints are contained within that
        subtree.
        - Child subtrees run first and remove the edges they fully own.
        - By the time control returns to this node, only edges that cross between its child subtrees or have
        endpoints that lie outside of this tree remain.
        - This node then adds those remaining edges and removes them from the shared set.

        As a result, every edge is added exactly once, at the lowest common ancestor of its two endpoints.
        """
        dot_graph = build_dotgraph(self.module_path if depth == 1 else self.module_name)

        for child in self.children:
            if not child.is_leaf():
                dot_graph.add_subgraph(
                    child._build_dot_graph(
                        available_edges,
                        build_edge,
                        build_dotgraph,
                        depth + 1,
                    )
                )
            else:
                dot_graph.add_node(child.module_path)

        edges_in_this_tree = {
            (upstream, downstream)
            for upstream, downstream in available_edges
            if upstream in self.leaves and downstream in self.leaves
        }

        for upstream, downstream in edges_in_this_tree:
            available_edges.remove((upstream, downstream))
            dot_edge = build_edge(upstream, downstream)
            dot_graph.add_edge(dot_edge)

        return dot_graph

from __future__ import annotations

import itertools
import dataclasses
from textwrap import dedent
from typing import Iterator


CLUSTER_INDEX_GENERATOR: Iterator[int] = itertools.count()  # noqa: F821


@dataclasses.dataclass(frozen=True, order=True)
class Edge:
    source: str
    destination: str
    label: str = ""
    emphasized: bool = False

    def __str__(self) -> str:
        return f'"{self.source}" ->  "{self.destination}"{self._render_attrs()}\n'

    def _render_attrs(self) -> str:
        attrs: dict[str, str] = {}
        if self.label:
            attrs["label"] = self.label
        if self.emphasized:
            attrs["style"] = "dashed"
        if attrs:
            joined_attrs = ", ".join([f'{key}="{value}"' for key, value in attrs.items()])
            return f" [{joined_attrs}]"
        else:
            return ""


class DotGraph:
    """
    A directed graph that can be rendered in DOT format.

    https://en.wikipedia.org/wiki/DOT_(graph_description_language)

    Either a top-level graph or a cluster that can be embedded in another dot graph

    See: https://graphviz.org/Gallery/directed/cluster.html
    """

    def __init__(self, title: str, concentrate: bool = True) -> None:
        self.title = title
        self.subgraphs: set[DotGraph] = set()
        self.nodes: set[str] = set()
        # Edges between two nodes in self.nodes, a node in self.nodes and a node in a subgraph, or two nodes from
        # different subgraphs. Edges between two nodes in the same subgraph are instead defined in that subgraph to
        # ensure they're rendered in its rectangle
        self.edges: set[Edge] = set()
        self.concentrate = concentrate

    def add_subgraph(self, subgraph: "DotGraph") -> None:
        self.subgraphs.add(subgraph)

    def add_node(self, name: str) -> None:
        self.nodes.add(name)

    def add_edge(self, edge: Edge) -> None:
        self.edges.add(edge)

    def render(self, as_subgraph: bool = False) -> str:
        graph_type = (
            f"subgraph cluster_{next(CLUSTER_INDEX_GENERATOR)}" if as_subgraph else "digraph"
        )
        # concentrate=true means that we merge the lines together.
        return dedent(f"""{graph_type} {{
            node [fontname=helvetica]
            {"concentrate=true" if self.concentrate else ""}
            {f'label="{DotGraph.render_module(self.title)}"' if as_subgraph else ""}
            {self._render_nodes()}
            {self._render_edges()}
            {self._render_subgraphs()}
        }}""")

    def _render_subgraphs(self) -> str:
        return "\n".join(subgraph.render(as_subgraph=True) for subgraph in self.subgraphs)

    def _render_nodes(self) -> str:
        return "\n".join(
            f'"{node}" [label="{DotGraph.render_module(node)}"]\n' for node in sorted(self.nodes)
        )

    def _render_edges(self) -> str:
        return "\n".join(str(edge) for edge in sorted(self.edges))

    @staticmethod
    def render_module(module: str) -> str:
        # Render as relative module.
        return f".{module.split('.')[-1]}"

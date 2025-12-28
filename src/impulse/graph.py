import dataclasses
from typing import Callable, Generic, Iterator, Mapping, TypeVar

V = TypeVar("V")  # type for graph vertices


@dataclasses.dataclass(frozen=True)
class DirectedGraphWithoutLoops(Generic[V]):
    vertices: frozenset[V]
    _adjacency_map: Mapping[V, set[V]]

    @classmethod
    def from_adjacency_condition(cls, vertices: set[V], is_adjacent: Callable[[V, V], bool]):
        adjacency_map = {
            from_vertex: {
                to_vertex
                for to_vertex in vertices
                if from_vertex != to_vertex and is_adjacent(from_vertex, to_vertex)
            }
            for from_vertex in vertices
        }
        return cls(vertices=frozenset(vertices), _adjacency_map=adjacency_map)

    def iter_edges(self) -> Iterator[tuple[V, V]]:
        for from_vertex in self._adjacency_map:
            for to_vertex in self._adjacency_map[from_vertex]:
                yield from_vertex, to_vertex

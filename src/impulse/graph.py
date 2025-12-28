import dataclasses
import itertools
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

    def remove_vertices(self, vertices_to_remove: set[V]) -> "DirectedGraphWithoutLoops[V]":
        new_vertices = frozenset(self.vertices - vertices_to_remove)
        return self.__class__(
            vertices=new_vertices,
            _adjacency_map={
                from_vertex: self._adjacency_map[from_vertex] - vertices_to_remove
                for from_vertex in new_vertices
            },
        )

    def find_acyclic_vertices(self) -> set[V]:
        """
        Find all vertices that are not part of any cycle.

        This function uses Tarjan's strongly connected components algorithm. The
        algorithm performs a single depth first search of the graph and groups
        vertices into strongly connected components (SCCs), where each vertex in
        an SCC is reachable from every other vertex in the same SCC.

        Under the assumption that the graph contains no self loops, a vertex is
        not part of a cycle if and only if the SCC it is part of contains no
        other vertices.

        Returns:
            A set of vertices that are not part of any cycle.
        """
        # Vertices are assigned indices in the order they are encountered
        index_generator: Iterator[int] = itertools.count()
        index_map: dict[V, int] = {}
        lowest_reachable_index: dict[V, int] = {}

        active_stack: list[V] = []
        # Mirror of active_stack for O(1) membership checks
        active_stack_set: set[V] = set()

        acyclic_vertices: set[V] = set()

        def visit(v: V) -> None:
            index = next(index_generator)

            index_map[v] = index
            lowest_reachable_index[v] = index

            active_stack.append(v)
            active_stack_set.add(v)

            for w in self._adjacency_map.get(v, {}):
                if w not in index_map:
                    visit(w)
                    lowest_reachable_index[v] = min(
                        lowest_reachable_index[v], lowest_reachable_index[w]
                    )
                elif w in active_stack_set:
                    lowest_reachable_index[v] = min(lowest_reachable_index[v], index_map[w])

            if lowest_reachable_index[v] == index_map[v]:
                scc: list[V] = []
                while True:
                    w = active_stack.pop()
                    active_stack_set.remove(w)
                    scc.append(w)
                    if w == v:
                        break

                if len(scc) == 1:
                    acyclic_vertices.update(scc)

        for vertex in self.vertices:
            if vertex not in index_map:
                visit(vertex)

        return acyclic_vertices

    def remove_acyclic_vertices(self) -> "DirectedGraphWithoutLoops[V]":
        return self.remove_vertices(self.find_acyclic_vertices())

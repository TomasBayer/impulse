import pytest
from impulse import graph


class TestDirectedGraphWithoutLoops:
    def test_from_adjacency(self):
        vertices = {"A", "B", "C"}

        def is_adjacent(from_vertex, to_vertex):
            return from_vertex < to_vertex

        test_graph = graph.DirectedGraphWithoutLoops.from_adjacency_condition(
            vertices, is_adjacent
        )

        # Self-loops should be excluded
        assert test_graph._adjacency_map == {"A": {"B", "C"}, "B": {"C"}, "C": set()}

    def test_from_adjacency_for_complete_graph(self):
        vertices = {"A", "B", "C"}

        def is_adjacent(from_vertex, to_vertex):
            return True

        test_graph = graph.DirectedGraphWithoutLoops.from_adjacency_condition(
            vertices, is_adjacent
        )

        assert test_graph._adjacency_map == {
            "A": {"B", "C"},
            "B": {"A", "C"},
            "C": {"A", "B"},
        }

    def test_from_adjacency_for_empty_graph(self):
        vertices = {"A", "B", "C"}

        def is_adjacent(from_vertex, to_vertex):
            return False

        test_graph = graph.DirectedGraphWithoutLoops.from_adjacency_condition(
            vertices, is_adjacent
        )

        assert test_graph._adjacency_map == {"A": set(), "B": set(), "C": set()}

    def test_from_adjacency_empty_vertices(self):
        vertices = set()

        def is_adjacent(from_vertex, to_vertex):
            return True

        test_graph = graph.DirectedGraphWithoutLoops.from_adjacency_condition(
            vertices, is_adjacent
        )

        assert test_graph.vertices == set()
        assert test_graph._adjacency_map == {}

    def test_iter_edges(self):
        vertices = {"A", "B", "C"}
        edges = {
            "A": {"B", "C"},
            "B": {"C"},
            "C": set(),
        }
        g = graph.DirectedGraphWithoutLoops(vertices, edges)

        result = set(g.iter_edges())
        expected = {("A", "B"), ("A", "C"), ("B", "C")}
        assert result == expected

    @pytest.mark.parametrize(
        ("vertices_to_remove", "expected_vertices", "expected_adjacency_map"),
        [
            (set(), {"A", "B", "C"}, {"A": {"B"}, "B": {"C"}, "C": set()}),
            ({"C"}, {"A", "B"}, {"A": {"B"}, "B": set()}),
            ({"B"}, {"A", "C"}, {"A": set(), "C": set()}),
            ({"A", "B", "C"}, set(), {}),
        ],
    )
    def test_remove_vertices(
        self,
        vertices_to_remove: set[str],
        expected_vertices: set[str],
        expected_adjacency_map: dict[str, set[str]],
    ):
        vertices = {"A", "B", "C"}
        adjacency_map = {"A": {"B"}, "B": {"C"}, "C": set()}
        test_graph = graph.DirectedGraphWithoutLoops(frozenset(vertices), adjacency_map)

        result_graph = test_graph.remove_vertices(vertices_to_remove)

        assert result_graph.vertices == expected_vertices
        assert result_graph._adjacency_map == expected_adjacency_map

    def test_find_acyclic_vertices_empty_graph(self):
        g = graph.DirectedGraphWithoutLoops(set(), {})
        assert g.find_acyclic_vertices() == set()

    def test_find_acyclic_vertices_simple_acyclic(self):
        vertices = {"A", "B", "C"}
        adjacency_map = {"A": {"B", "C"}, "B": {"C"}, "C": set()}
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == {"A", "B", "C"}

    def test_find_acyclic_vertices_simple_cycle(self):
        vertices = {"A", "B", "C"}
        adjacency_map = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == set()

    def test_find_acyclic_vertices_with_branches(self):
        vertices = {"A", "B", "C", "D", "E", "F"}
        adjacency_map = {
            "A": {"B", "C"},  # A branches to B and C
            "B": {"D"},  # B -> D -> E -> B (cycle)
            "C": {"F"},  # C -> F (acyclic branch)
            "D": {"E"},
            "E": {"B"},
            "F": set(),
        }
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == {"A", "C", "F"}

    def test_find_acyclic_vertices_isolated_vertices(self):
        """Isolated vertices (no edges) are acyclic."""
        vertices = {"A", "B", "C"}
        adjacency_map = {"A": set(), "B": set(), "C": set()}
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == {"A", "B", "C"}

    def test_find_acyclic_vertices_multiple_cycles(self):
        """Multiple disconnected cycles."""
        vertices = {"A", "B", "C", "D", "E", "F"}
        adjacency_map = {
            "A": {"B"},  # A -> B -> A (cycle 1)
            "B": {"A"},
            "C": set(),  # C is isolated (acyclic)
            "D": {"E"},  # D -> E -> F -> D (cycle 2)
            "E": {"F"},
            "F": {"D"},
        }
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == {"C"}

    def test_find_acyclic_vertices_mixed_graph(self):
        """Graph with cycles, acyclic chains, and isolated vertices."""
        vertices = {"A", "B", "C", "D", "E", "F", "G"}
        adjacency_map = {
            "A": {"B"},  # A -> B -> C (acyclic chain)
            "B": {"C"},
            "C": set(),
            "D": {"E"},  # D -> E -> D (cycle)
            "E": {"D"},
            "F": set(),  # F isolated
            "G": {"A"},  # G -> A (connects to acyclic chain)
        }
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        assert g.find_acyclic_vertices() == {"A", "B", "C", "F", "G"}

    def test_remove_acyclic_vertices_returns_only_cycles(self):
        """remove_acyclic_vertices should return a graph with only cyclic vertices."""
        vertices = {"A", "B", "C", "D", "E"}
        adjacency_map = {
            "A": {"B"},  # A -> B (acyclic)
            "B": set(),
            "C": {"D"},  # C -> D -> E -> C (cycle)
            "D": {"E"},
            "E": {"C"},
        }
        g = graph.DirectedGraphWithoutLoops(vertices, adjacency_map)
        result = g.remove_acyclic_vertices()

        assert result.vertices == {"C", "D", "E"}
        assert result._adjacency_map == {
            "C": {"D"},
            "D": {"E"},
            "E": {"C"},
        }

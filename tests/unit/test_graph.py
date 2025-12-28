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

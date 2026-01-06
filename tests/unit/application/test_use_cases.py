from impulse.application import use_cases
from copy import copy
from impulse import dotfile
from impulse.dotfile import Edge
import grimp
from impulse import ports

SOME_ROOT_PACKAGE = "mypackage"
SOME_MODULE = f"{SOME_ROOT_PACKAGE}.foo"


def fake_get_top_level_package_non_namespace(module_name: str) -> str:
    return module_name.split(".")[0]


def build_fake_graph(package_name: str) -> grimp.ImportGraph:
    graph = grimp.ImportGraph()
    graph.add_module(package_name)

    graph.add_module(SOME_MODULE)

    for child in ("blue", "green", "yellow", "red"):
        graph.add_module(f"{SOME_MODULE}.{child}")

    graph.add_import(
        importer=f"{SOME_MODULE}.blue.alpha",
        imported=f"{SOME_MODULE}.green",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.green",
        imported=f"{SOME_MODULE}.yellow.beta",
    )
    # Add 4 imports between blue and red in different permutations of root and descendants.
    graph.add_import(
        importer=f"{SOME_MODULE}.blue",
        imported=f"{SOME_MODULE}.red",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.blue",
        imported=f"{SOME_MODULE}.red.gamma",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.blue.alpha",
        imported=f"{SOME_MODULE}.red",
    )
    graph.add_import(
        importer=f"{SOME_MODULE}.blue.delta",
        imported=f"{SOME_MODULE}.red.epsilon",
    )
    # Add a cycle.
    graph.add_import(
        importer=f"{SOME_MODULE}.red.epsilon",
        imported=f"{SOME_MODULE}.blue.alpha",
    )

    return graph


class SpyGraphViewer(ports.GraphViewer):
    def __init__(self) -> None:
        self.called_with_dot: dotfile.DotGraph | None = None

    def view(self, dot: dotfile.DotGraph) -> None:
        self.called_with_dot = dot


class TestDrawGraph:
    def test_draw_graph(self):
        original_sys_path = ["/some/path", "/another/path"]
        sys_path = copy(original_sys_path)
        current_directory = "/cwd"
        viewer = SpyGraphViewer()

        use_cases.draw_graph(
            SOME_MODULE,
            show_import_totals=False,
            show_cycle_breakers=False,
            depth=1,
            sys_path=sys_path,
            current_directory=current_directory,
            get_top_level_package=fake_get_top_level_package_non_namespace,
            build_graph=build_fake_graph,
            viewer=viewer,
        )

        # The current directory was added to system path.
        assert sys_path == [current_directory, *original_sys_path]
        # The image generation function was called.
        assert viewer.called_with_dot, "Viewer not called."
        assert viewer.called_with_dot.title == SOME_MODULE
        assert viewer.called_with_dot.concentrate is True
        assert viewer.called_with_dot.nodes == {
            "mypackage.foo.green",
            "mypackage.foo.blue",
            "mypackage.foo.yellow",
            "mypackage.foo.red",
        }
        assert viewer.called_with_dot.edges == {
            Edge("mypackage.foo.blue", "mypackage.foo.green"),
            Edge("mypackage.foo.green", "mypackage.foo.yellow"),
            Edge("mypackage.foo.blue", "mypackage.foo.red"),
            Edge("mypackage.foo.red", "mypackage.foo.blue"),
        }

    def test_draw_graph_calls_top_level_package(self):
        def get_top_level_package(module: str) -> str:
            return "some.namespace"

        def asserting_build_graph(top_level_package: str) -> grimp.ImportGraph:
            assert top_level_package == "some.namespace"
            graph = grimp.ImportGraph()
            graph.add_module("some.namespace")
            graph.add_module("some.namespace.foo")
            graph.add_module("some.namespace.foo.blue")
            graph.add_module("some.namespace.foo.blue.alpha")
            graph.add_module("some.namespace.foo.blue.beta")
            return graph

        viewer = SpyGraphViewer()
        use_cases.draw_graph(
            "some.namespace.foo.blue",
            show_import_totals=False,
            show_cycle_breakers=False,
            depth=1,
            sys_path=[],
            current_directory="/cwd",
            get_top_level_package=get_top_level_package,
            build_graph=asserting_build_graph,
            viewer=viewer,
        )

    def test_draw_graph_show_import_totals(self):
        viewer = SpyGraphViewer()

        use_cases.draw_graph(
            SOME_MODULE,
            show_import_totals=True,
            show_cycle_breakers=False,
            depth=1,
            sys_path=[],
            current_directory="/cwd",
            get_top_level_package=fake_get_top_level_package_non_namespace,
            build_graph=build_fake_graph,
            viewer=viewer,
        )

        assert viewer.called_with_dot.concentrate is False
        assert viewer.called_with_dot.edges == {
            Edge("mypackage.foo.blue", "mypackage.foo.green", label="1"),
            Edge("mypackage.foo.green", "mypackage.foo.yellow", label="1"),
            Edge("mypackage.foo.blue", "mypackage.foo.red", label="4"),
            Edge("mypackage.foo.red", "mypackage.foo.blue", label="1"),
        }

    def test_draw_graph_show_cycle_breakers(self):
        viewer = SpyGraphViewer()

        use_cases.draw_graph(
            SOME_MODULE,
            show_import_totals=False,
            show_cycle_breakers=True,
            depth=1,
            sys_path=[],
            current_directory="/cwd",
            get_top_level_package=fake_get_top_level_package_non_namespace,
            build_graph=build_fake_graph,
            viewer=viewer,
        )

        assert viewer.called_with_dot.concentrate is False
        assert viewer.called_with_dot.edges == {
            Edge(
                "mypackage.foo.blue",
                "mypackage.foo.green",
            ),
            Edge(
                "mypackage.foo.green",
                "mypackage.foo.yellow",
            ),
            Edge(
                "mypackage.foo.blue",
                "mypackage.foo.red",
            ),
            Edge("mypackage.foo.red", "mypackage.foo.blue", emphasized=True),
        }

    def test_draw_graph_with_depth_2(self):
        """Test that depth=2 creates nested subgraph structure."""

        def build_depth_graph(
            package_name: str, *additional_package_names: str
        ) -> grimp.ImportGraph:
            """Build graph with 2 levels of nesting."""
            graph = grimp.ImportGraph()

            # Root module
            graph.add_module("mypackage")
            graph.add_module("mypackage.foo")

            # Level 1: immediate children of foo
            graph.add_module("mypackage.foo.blue")
            graph.add_module("mypackage.foo.red")

            # Level 2: grandchildren of foo
            graph.add_module("mypackage.foo.blue.alpha")
            graph.add_module("mypackage.foo.blue.beta")
            graph.add_module("mypackage.foo.red.gamma")

            # Add some imports
            graph.add_import(
                importer="mypackage.foo.blue.alpha",
                imported="mypackage.foo.red.gamma",
            )
            graph.add_import(
                importer="mypackage.foo.blue.alpha",
                imported="mypackage.foo.blue.beta",
            )

            return graph

        viewer = SpyGraphViewer()

        use_cases.draw_graph(
            "mypackage.foo",
            show_import_totals=False,
            show_cycle_breakers=False,
            depth=2,
            sys_path=[],
            current_directory="/cwd",
            get_top_level_package=fake_get_top_level_package_non_namespace,
            build_graph=build_depth_graph,
            viewer=viewer,
        )

        assert viewer.called_with_dot.title == "mypackage.foo"
        assert len(viewer.called_with_dot.subgraphs) == 2

        # Find the blue and red subgraphs
        blue_subgraph = next(sg for sg in viewer.called_with_dot.subgraphs if sg.title == ".blue")
        red_subgraph = next(sg for sg in viewer.called_with_dot.subgraphs if sg.title == ".red")

        # Verify nodes in nested subgraphs
        assert blue_subgraph.nodes == {
            "mypackage.foo.blue.alpha",
            "mypackage.foo.blue.beta",
        }
        assert red_subgraph.nodes == {
            "mypackage.foo.red.gamma",
        }

        # Verify edges are in the appropriate subgraphs
        assert blue_subgraph.edges == {
            Edge("mypackage.foo.blue.alpha", "mypackage.foo.blue.beta"),
        }

        assert viewer.called_with_dot.edges == {
            Edge("mypackage.foo.blue.alpha", "mypackage.foo.red.gamma"),
        }

from collections.abc import Set
from collections.abc import Callable
import grimp

from impulse import ports, dotfile, tree


def draw_graph(
    module_names: tuple[str, ...],
    show_import_totals: bool,
    show_cycle_breakers: bool,
    depth: int,
    sys_path: list[str],
    current_directory: str,
    get_top_level_package: Callable[[str], str],
    build_graph: Callable[[str], grimp.ImportGraph],
    viewer: ports.GraphViewer,
) -> None:
    """
    Create a file showing a graph of the supplied package(s).
    Args:
        module_names: one or more package or subpackage names of importable Python packages.
        show_import_totals: whether to label the arrows with the total number of imports they represent.
        show_cycle_breakers: marks a set of dependencies that, if removed, would make the graph acyclic.
        depth: depth of module hierarchy to visualize
        sys_path: the sys.path list (or a test double).
        current_directory: the current working directory.
        get_top_level_package: the function to retrieve the top level package name. This will usually be the first part
            of the dotted module name (before the first dot), but for namespace packages it should be the 'portion' name.
        build_graph: the function which builds the graph of the supplied package
            (pass grimp.build_graph or a test double).
        viewer: GraphViewer for generating the graph image and opening it.
    """
    # Add current directory to the path, as this doesn't happen automatically.
    sys_path.insert(0, current_directory)

    # Get all unique top-level packages
    top_level_packages = {get_top_level_package(module_name) for module_name in module_names}

    grimp_graph = build_graph(*top_level_packages)

    dot = _build_dot(grimp_graph, module_names, show_import_totals, show_cycle_breakers, depth)

    viewer.view(dot)


class _DotGraphBuildStrategy:
    def build(
        self,
        module_names: tuple[str, ...],
        grimp_graph: grimp.ImportGraph,
        depth: int = 1,
    ) -> dotfile.DotGraph:
        module_tree = tree.ModuleTreeNode.build_children(
            module_names, grimp_graph.find_children, depth
        )

        self.prepare_graph(grimp_graph, module_tree.leaves)

        return module_tree.build_dot_graph(
            has_edge=lambda upstream, downstream: self.has_dependency(
                grimp_graph, upstream, downstream
            ),
            build_edge=lambda upstream, downstream: self.build_edge(
                grimp_graph, upstream, downstream
            ),
            build_dotgraph=lambda module_name: dotfile.DotGraph(
                title=module_name, concentrate=self.should_concentrate()
            ),
        )

    def should_concentrate(self) -> bool:
        return True

    def prepare_graph(self, grimp_graph: grimp.ImportGraph, nodes: Set[str]) -> None:
        pass

    def has_dependency(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> bool:
        raise NotImplementedError

    def build_edge(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> dotfile.Edge:
        raise NotImplementedError


class _ModuleSquashingBuildStrategy(_DotGraphBuildStrategy):
    """Fast builder for when we don't need additional data about the imports."""

    def prepare_graph(self, grimp_graph: grimp.ImportGraph, nodes: Set[str]) -> None:
        for node in nodes:
            grimp_graph.squash_module(node)

    def has_dependency(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> bool:
        return grimp_graph.direct_import_exists(importer=downstream, imported=upstream)

    def build_edge(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> dotfile.Edge:
        return dotfile.Edge(source=downstream, destination=upstream)


class _ImportExpressionBuildStrategy(_DotGraphBuildStrategy):
    """Slower builder for when we want to work on the whole graph,
    without squashing children.
    """

    def __init__(
        self, *, module_names: tuple[str, ...], show_import_totals: bool, show_cycle_breakers: bool
    ) -> None:
        self.module_names = module_names
        self.show_import_totals = show_import_totals
        self.show_cycle_breakers = show_cycle_breakers
        self.cycle_breakers: set[tuple[str, str]] | None = None

    def should_concentrate(self) -> bool:
        # We need to see edge direction emphasized separately.
        return not (self.show_import_totals or self.show_cycle_breakers)

    def prepare_graph(self, grimp_graph: grimp.ImportGraph, nodes: Set[str]) -> None:
        super().prepare_graph(grimp_graph, nodes)

        if self.show_cycle_breakers:
            self.cycle_breakers = self._get_coarse_grained_cycle_breakers(grimp_graph, nodes)

    def _get_coarse_grained_cycle_breakers(
        self, grimp_graph: grimp.ImportGraph, nodes: Set[str]
    ) -> set[tuple[str, str]]:
        # In the form (importer, imported).
        coarse_grained_cycle_breakers: set[tuple[str, str]] = set()

        for module_name in self.module_names:
            for fine_grained_cycle_breaker in grimp_graph.nominate_cycle_breakers(module_name):
                importer, imported = fine_grained_cycle_breaker
                importer_ancestor = self._get_self_or_ancestor(candidate=importer, ancestors=nodes)
                imported_ancestor = self._get_self_or_ancestor(candidate=imported, ancestors=nodes)

                if importer_ancestor and imported_ancestor:
                    coarse_grained_cycle_breakers.add((importer_ancestor, imported_ancestor))

        return coarse_grained_cycle_breakers

    @staticmethod
    def _get_self_or_ancestor(candidate: str, ancestors: Set[str]) -> str | None:
        for ancestor in ancestors:
            if candidate == ancestor or candidate.startswith(f"{ancestor}."):
                return ancestor
        return None

    def has_dependency(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> bool:
        return grimp_graph.direct_import_exists(
            importer=downstream, imported=upstream, as_packages=True
        )

    def build_edge(
        self, grimp_graph: grimp.ImportGraph, upstream: str, downstream: str
    ) -> dotfile.Edge:
        if self.show_import_totals:
            number_of_imports = self._count_imports_between_packages(
                grimp_graph, importer=downstream, imported=upstream
            )
            label = str(number_of_imports)
        else:
            label = ""

        if self.show_cycle_breakers:
            assert self.cycle_breakers is not None
            is_cycle_breaker = (downstream, upstream) in self.cycle_breakers
            emphasized = is_cycle_breaker
        else:
            emphasized = False

        return dotfile.Edge(
            source=downstream, destination=upstream, label=label, emphasized=emphasized
        )

    @staticmethod
    def _count_imports_between_packages(
        graph: grimp.ImportGraph, *, importer: str, imported: str
    ) -> int:
        return (
            len(graph.find_matching_direct_imports(import_expression=f"{importer} -> {imported}"))
            + len(
                graph.find_matching_direct_imports(
                    import_expression=f"{importer} -> {imported}.**"
                )
            )
            + len(
                graph.find_matching_direct_imports(
                    import_expression=f"{importer}.** -> {imported}"
                )
            )
            + len(
                graph.find_matching_direct_imports(
                    import_expression=f"{importer}.** -> {imported}.**"
                )
            )
        )


def _build_dot(
    grimp_graph: grimp.ImportGraph,
    module_names: tuple[str, ...],
    show_import_totals: bool,
    show_cycle_breakers: bool,
    depth: int,
) -> dotfile.DotGraph:
    strategy: _DotGraphBuildStrategy
    if show_import_totals or show_cycle_breakers:
        strategy = _ImportExpressionBuildStrategy(
            module_names=module_names,
            show_import_totals=show_import_totals,
            show_cycle_breakers=show_cycle_breakers,
        )
    else:
        strategy = _ModuleSquashingBuildStrategy()

    return strategy.build(module_names, grimp_graph, depth)

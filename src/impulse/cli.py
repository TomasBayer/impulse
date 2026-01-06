import os

import click
import sys

from impulse.application import use_cases
from impulse import adapters
import grimp


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--show-import-totals",
    is_flag=True,
    help="Label arrows with the number of imports they represent.",
)
@click.option(
    "--show-cycle-breakers",
    is_flag=True,
    help=(
        "Identify a set of dependencies that, if removed, would make the graph acyclic, "
        "and display them as dashed lines."
    ),
)
@click.option(
    "--depth",
    type=click.IntRange(min=0),
    default=1,
    help="Depth of module hierarchy to visualize.",
)
@click.argument("module_names", type=str, nargs=-1, required=True)
def drawgraph(
    module_names: tuple[str, ...], show_import_totals: bool, show_cycle_breakers: bool, depth: int
) -> None:
    use_cases.draw_graph(
        module_names=module_names,
        show_import_totals=show_import_totals,
        show_cycle_breakers=show_cycle_breakers,
        depth=depth,
        sys_path=sys.path,
        current_directory=os.getcwd(),
        get_top_level_package=adapters.get_top_level_package,
        build_graph=grimp.build_graph,
        viewer=adapters.BrowserGraphViewer(),
    )

"""hyperglass Command Line Interface."""

# Standard Library
import re
import sys
import typing as t

# Third Party
import typer

# Local
from .echo import echo


def _version(value: bool) -> None:
    # Project
    from hyperglass import __version__

    if value:
        echo.info(__version__)
        raise typer.Exit()


cli = typer.Typer(name="hyperglass", help="hyperglass Command Line Interface", no_args_is_help=True)


def run():
    """Run the hyperglass CLI."""
    return typer.run(cli())


@cli.callback()
def version(
    version: t.Optional[bool] = typer.Option(
        None, "--version", help="hyperglass version", callback=_version
    )
) -> None:
    """hyperglass"""
    pass


@cli.command()
def start(build: bool = False, workers: t.Optional[int] = None) -> None:
    """Start hyperglass"""
    # Project
    from hyperglass.main import run

    # Local
    from .util import build_ui

    kwargs = {}
    if workers != 0:
        kwargs["workers"] = workers

    try:
        if build:
            build_complete = build_ui(timeout=180)
            if build_complete:
                run(workers)
        else:
            run(workers)

    except (KeyboardInterrupt, SystemExit) as err:
        error_message = str(err)
        if (len(error_message)) > 1:
            echo.warning(str(err))
        echo.error("Stopping hyperglass due to keyboard interrupt.")
        raise typer.Exit(0)


@cli.command()
def build_ui(timeout: int = typer.Option(180, help="Timeout in seconds")) -> None:
    """Create a new UI build."""
    # Local
    from .util import build_ui as _build_ui

    with echo._console.status(
        f"Starting new UI build with a {timeout} second timeout...", spinner="aesthetic"
    ):

        _build_ui()


@cli.command()
def system_info():
    """Get system information for a bug report"""
    # Third Party
    from rich.table import Table

    # Project
    from hyperglass.util.system_info import get_system_info

    # Local
    from .static import MD_BOX

    data = get_system_info()

    rows = tuple(
        (f"**{title}**", f"`{value!s}`" if mod == "code" else str(value))
        for title, (value, mod) in data.items()
    )

    table = Table("Metric", "Value", box=MD_BOX)
    for title, metric in rows:
        table.add_row(title, metric)

    echo.info("Please copy & paste this table in your bug report:\n")
    echo.plain(table)


@cli.command()
def clear_cache():
    """Clear the Redis cache"""
    # Project
    from hyperglass.state import use_state

    state = use_state()

    try:
        state.clear()
        echo.success("Cleared Redis Cache")

    except Exception as err:
        if not sys.stdout.isatty():
            echo._console.print_exception(show_locals=True)
            raise typer.Exit(1)

        echo.error("Error clearing cache: {!s}", err)
        raise typer.Exit(1)


@cli.command()
def devices(
    search: t.Optional[str] = typer.Argument(None, help="Device ID or Name Search Pattern")
):
    """Show all configured devices"""
    # Third Party
    from rich.columns import Columns
    from rich._inspect import Inspect

    # Project
    from hyperglass.state import use_state

    devices = use_state("devices")
    if search is not None:
        pattern = re.compile(search, re.IGNORECASE)
        for device in devices:
            if pattern.match(device.id) or pattern.match(device.name):
                echo._console.print(
                    Inspect(
                        device,
                        title=device.name,
                        docs=False,
                        methods=False,
                        dunder=False,
                        sort=True,
                        all=False,
                        value=True,
                        help=False,
                    )
                )
                raise typer.Exit(0)

    panels = [
        Inspect(
            device,
            title=device.name,
            docs=False,
            methods=False,
            dunder=False,
            sort=True,
            all=False,
            value=True,
            help=False,
        )
        for device in devices
    ]
    echo._console.print(Columns(panels))


@cli.command(name="params")
def _params(
    path: t.Optional[str] = typer.Argument(
        None, help="Parameter Object Path, for example 'messages.no_input'"
    )
):
    """Show configuration parameters"""
    # Standard Library
    from operator import attrgetter

    # Third Party
    from rich._inspect import Inspect

    # Project
    from hyperglass.state import use_state

    params = use_state("params")
    if path is not None:
        try:
            value = attrgetter(path)(params)

            echo._console.print(
                Inspect(
                    value,
                    title=f"params.{path}",
                    docs=False,
                    methods=False,
                    dunder=False,
                    sort=True,
                    all=False,
                    value=True,
                    help=False,
                )
            )
            raise typer.Exit(0)
        except AttributeError:
            echo.error(f"{'params.'+path!r} does not exist")
            raise typer.Exit(1)

    panel = Inspect(
        params,
        title="hyperglass Configuration Parameters",
        docs=False,
        methods=False,
        dunder=False,
        sort=True,
        all=False,
        value=True,
        help=False,
    )
    echo._console.print(panel)


@cli.command()
def setup():
    """Initialize hyperglass setup."""
    # Local
    from .installer import Installer

    with Installer() as start:
        start()


@cli.command()
def settings():
    """Show hyperglass system settings (environment variables)"""

    # Project
    from hyperglass.settings import Settings

    echo.plain(Settings)

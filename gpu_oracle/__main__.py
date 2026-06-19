"""CLI entry point for GPU Oracle."""

import sys
from pathlib import Path

import click
from rich.console import Console

from gpu_oracle.config import Config, get_default_config_path
from gpu_oracle.gather import Gatherer
from gpu_oracle.plot import Plotter

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="gpu-oracle")
def cli():
    """GPU Oracle - Track GPU statistics over time and generate interactive dashboards."""
    pass


@cli.command()
@click.option("--poll-seconds", default=5, help="Polling interval in seconds", show_default=True)
@click.option("--run", help="Run name (auto-generated if not specified)")
@click.option("--config", default=None, help="Path to config file", type=click.Path(exists=True))
@click.option("--skip-plot", is_flag=True, help="Skip plotting after gathering")
def gather(poll_seconds: int, run: str | None, config: str | None, skip_plot: bool):
    """Gather GPU metrics over time.

    Press Ctrl+C to stop gathering and save results.
    """
    # Load config
    config_path = config if config else get_default_config_path()

    try:
        cfg = Config.from_file(config_path)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error loading config:[/red] {e}")
        sys.exit(1)

    # Validate poll interval
    if poll_seconds < 1:
        console.print("[red]Error:[/red] poll-seconds must be at least 1")
        sys.exit(1)

    # Run gatherer
    gatherer = Gatherer(poll_seconds=poll_seconds, config=cfg, run_name=run)
    try:
        gatherer.run()
        if not skip_plot:
            _plot(run=gatherer.run_name, output=None, runs_dir=None)
    except Exception as e:
        console.print(f"\n[red]Error during gathering:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option("--run", required=True, help="Run name to plot")
@click.option("--output", help="Output HTML file path")
@click.option("--runs-dir", help="Directory containing run JSON files", type=click.Path(exists=True))
def plot(run: str, output: str | None, runs_dir: str | None):
    """Generate an interactive HTML dashboard from a run.

    Example:
        gpu-oracle plot --run run_20250610_143026_a7b3c
    """
    _plot(run=run, output=output, runs_dir=runs_dir)

def _plot(run: str, output: str | None, runs_dir: str | None):
    """Generate an interactive HTML dashboard from a run.
    """
    runs_dir_path = Path(runs_dir) if runs_dir else None
    output_path = Path(output) if output else None

    try:
        plotter = Plotter(run_name=run, runs_dir=runs_dir_path)
        result_path = plotter.generate(output_path=output_path)

        if result_path:
            console.print(f"\n[dim]Open the dashboard in your browser:[/dim]")
            console.print(f"[cyan]file://{result_path.absolute()}[/cyan]")

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error generating plot:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()

"""Plot generation logic for GPU Oracle dashboards."""

import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console

console = Console()


# Metric display configuration
METRIC_CONFIG = {
    "utilization": {"title": "GPU Utilization", "unit": "%", "color": "blue"},
    "memory_used": {"title": "Memory Used", "unit": "MB", "color": "green"},
    "memory_free": {"title": "Memory Free", "unit": "MB", "color": "lightgreen"},
    "memory_total": {"title": "Memory Total", "unit": "MB", "color": "darkgreen"},
    "temperature": {"title": "Temperature", "unit": "°C", "color": "red"},
    "power_draw": {"title": "Power Draw", "unit": "W", "color": "orange"},
    "clock_graphics": {"title": "Graphics Clock", "unit": "MHz", "color": "purple"},
    "clock_sm": {"title": "SM Clock", "unit": "MHz", "color": "magenta"},
    "clock_memory": {"title": "Memory Clock", "unit": "MHz", "color": "pink"},
    "fan_speed": {"title": "Fan Speed", "unit": "%", "color": "cyan"},
    "pci_tx": {"title": "PCI TX Throughput", "unit": "MB/s", "color": "indigo"},
    "pci_rx": {"title": "PCI RX Throughput", "unit": "MB/s", "color": "teal"},
}


class Plotter:
    """Handles generation of interactive HTML dashboards."""

    def __init__(self, run_name: str, runs_dir: Path | None = None):
        self.run_name = run_name
        self.runs_dir = runs_dir or Path(__file__).parent.parent / "runs"
        self.data: dict | None = None
        self.metrics_data: list[dict] | None = None

    def _load_data(self):
        """Load JSON data file for the run."""
        input_path = self.runs_dir / f"{self.run_name}.json"

        if not input_path.exists():
            raise FileNotFoundError(f"Run data not found: {input_path}")

        with open(input_path) as f:
            self.data = json.load(f)
            self.metrics_data = self.data.get("metrics", [])

        console.print(f"[green]✓[/green] Loaded data from: [cyan]{input_path}[/cyan]")

    def _organize_data(self):
        """Organize metrics data by GPU and metric type."""
        if not self.metrics_data:
            return {}, set()

        # Get all metrics present in the data (excluding timestamp and gpu_id)
        sample = self.metrics_data[0]
        metric_names = set(sample.keys()) - {"timestamp", "gpu_id"}

        # Organize by metric: {metric: {gpu_id: [(timestamp, value), ...]}}
        organized: dict[str, dict[int, list[tuple]]] = {}
        for metric in metric_names:
            organized[metric] = {}

        for entry in self.metrics_data:
            gpu_id = entry["gpu_id"]
            timestamp = entry["timestamp"]

            for metric in metric_names:
                if metric in entry and entry[metric] is not None:
                    if gpu_id not in organized[metric]:
                        organized[metric][gpu_id] = []
                    organized[metric][gpu_id].append((timestamp, entry[metric]))

        return organized, metric_names

    def _create_metric_plot(self, metric: str, data: dict[int, list[tuple]]) -> go.Figure:
        """Create a plot for a single metric with all GPUs."""
        config = METRIC_CONFIG.get(metric, {"title": metric, "unit": "", "color": "blue"})

        fig = go.Figure()

        # Color palette for different GPUs
        colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

        # Add a line for each GPU
        for gpu_id in sorted(data.keys()):
            timestamps, values = zip(*data[gpu_id])

            color = colors[gpu_id % len(colors)]
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=values,
                mode="lines+markers",
                name=f"GPU {gpu_id}",
                line=dict(color=color, width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>GPU {gpu_id}</b><br>" +
                              "Time: %{x}<br>" +
                              f"{config['title']}: %{{y}} {config['unit']}<br>" +
                              "<extra></extra>"
            ))

        fig.update_layout(
            title=f"<b>{config['title']} Over Time</b>",
            xaxis_title="Time",
            yaxis_title=f"{config['title']} ({config['unit']})",
            hovermode="x unified",
            template="plotly_white",
            font=dict(family="Arial, sans-serif"),
            height=400,
            margin=dict(l=60, r=30, t=60, b=60),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )

        return fig

    def generate(self, output_path: Path | None = None) -> Path:
        """Generate the HTML dashboard."""
        self._load_data()
        organized, metric_names = self._organize_data()

        if not metric_names:
            console.print("[yellow]Warning:[/yellow] No metrics found in data")
            return Path()

        # Create subplots (2 columns)
        num_metrics = len(metric_names)
        num_rows = (num_metrics + 1) // 2

        subplot_titles = [METRIC_CONFIG.get(m, {}).get("title", m) for m in sorted(metric_names)]
        fig = make_subplots(
            rows=num_rows,
            cols=2,
            subplot_titles=subplot_titles,
            vertical_spacing=0.12,
            horizontal_spacing=0.08
        )

        # Color palette for GPUs
        colors = [
            "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
            "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
        ]

        # Add traces for each metric
        for idx, metric in enumerate(sorted(metric_names)):
            row = (idx // 2) + 1
            col = (idx % 2) + 1
            config = METRIC_CONFIG.get(metric, {"unit": ""})

            metric_data = organized.get(metric, {})

            for gpu_id in sorted(metric_data.keys()):
                timestamps, values = zip(*metric_data[gpu_id])
                color = colors[gpu_id % len(colors)]

                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=values,
                        mode="lines+markers",
                        name=f"GPU {gpu_id}",
                        line=dict(color=color, width=1.5),
                        marker=dict(size=3),
                        legendgroup=f"gpu{gpu_id}",
                        hovertemplate=f"<b>GPU {gpu_id}</b><br>" +
                                      "Time: %{x}<br>" +
                                      f"{metric}: %{{y}} {config['unit']}<br>" +
                                      "<extra></extra>"
                    ),
                    row=row, col=col
                )

        # Update layout
        fig.update_layout(
            title_text=f"<b>GPU Oracle Dashboard - {self.run_name}</b>",
            template="plotly_white",
            font=dict(family="Arial, sans-serif"),
            height=300 * num_rows + 100,
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.05,
                xanchor="center",
                x=0.5
            )
        )

        # Set default output path
        if output_path is None:
            plots_dir = Path(__file__).parent.parent / "plots"
            plots_dir.mkdir(exist_ok=True)
            output_path = plots_dir / f"{self.run_name}.html"

        # Write HTML
        fig.write_html(output_path, include_plotlyjs="cdn", full_html=True)

        console.print(f"[green]✓[/green] Dashboard saved to: [cyan]{output_path}[/cyan]")
        return output_path

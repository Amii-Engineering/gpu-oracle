"""Plot generation logic for GPU Oracle dashboards."""

import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from rich.console import Console

console = Console()


# Metric display configuration with Grafana-style colors and unit conversion
# conversion_factor: factor to multiply raw value by for display (e.g., MB to GB = 1/1024)
METRIC_CONFIG = {
    "utilization": {"title": "GPU Utilization", "unit": "%", "color": "#5794F2", "conversion": 1.0},
    "memory_used": {"title": "Memory Used", "unit": "GB", "color": "#73BF69", "conversion": 1.0 / 1024},
    "memory_free": {"title": "Memory Free", "unit": "GB", "color": "#96D98D", "conversion": 1.0 / 1024},
    "memory_total": {"title": "Memory Total", "unit": "GB", "color": "#5FA646", "conversion": 1.0 / 1024},
    "temperature": {"title": "Temperature", "unit": "°C", "color": "#F2CC0C", "conversion": 1.0},
    "power_draw": {"title": "Power Draw", "unit": "W", "color": "#F2495C", "conversion": 1.0},
    "clock_graphics": {"title": "Graphics Clock", "unit": "MHz", "color": "#9B8BFE", "conversion": 1.0},
    "clock_sm": {"title": "SM Clock", "unit": "MHz", "color": "#B684FD", "conversion": 1.0},
    "clock_memory": {"title": "Memory Clock", "unit": "MHz", "color": "#C278FD", "conversion": 1.0},
    "fan_speed": {"title": "Fan Speed", "unit": "%", "color": "#73D9D7", "conversion": 1.0},
    "pci_tx": {"title": "PCI TX Throughput", "unit": "MB/s", "color": "#FFA68D", "conversion": 1.0},
    "pci_rx": {"title": "PCI RX Throughput", "unit": "MB/s", "color": "#FFB3BA", "conversion": 1.0},
}

# GPU color palette (Grafana-inspired: distinct but not too bright)
GPU_COLORS = [
    "#3B82F6",  # Blue
    "#EF4444",  # Red
    "#10B981",  # Green
    "#F59E0B",  # Orange
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#84CC16",  # Lime
]


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

    def generate(self, output_path: Path | None = None) -> Path:
        """Generate the HTML dashboard with Grafana-style dark theme."""
        self._load_data()
        organized, metric_names = self._organize_data()

        if not metric_names:
            console.print("[yellow]Warning:[/yellow] No metrics found in data")
            return Path()

        # Get all unique GPU IDs
        all_gpus = set()
        for metric_data in organized.values():
            all_gpus.update(metric_data.keys())
        gpu_ids = sorted(all_gpus)

        # Create subplots (2 columns)
        num_metrics = len(metric_names)
        num_rows = (num_metrics + 1) // 2

        subplot_titles = [METRIC_CONFIG.get(m, {}).get("title", m) for m in sorted(metric_names)]
        fig = make_subplots(
            rows=num_rows,
            cols=2,
            subplot_titles=subplot_titles,
            vertical_spacing=0.18,
            horizontal_spacing=0.12
        )

        # Track which GPUs we've already added to the legend
        gpus_in_legend = set()

        # Add traces for each metric
        for idx, metric in enumerate(sorted(metric_names)):
            row = (idx // 2) + 1
            col = (idx % 2) + 1
            config = METRIC_CONFIG.get(metric, {"unit": ""})

            metric_data = organized.get(metric, {})

            for gpu_id in sorted(metric_data.keys()):
                timestamps, values = zip(*metric_data[gpu_id])
                color = GPU_COLORS[gpu_id % len(GPU_COLORS)]

                # Apply unit conversion
                conversion = config.get("conversion", 1.0)
                converted_values = [v * conversion for v in values]

                # Only show legend entry for first occurrence of each GPU
                show_in_legend = gpu_id not in gpus_in_legend
                if show_in_legend:
                    gpus_in_legend.add(gpu_id)

                fig.add_trace(
                    go.Scatter(
                        x=timestamps,
                        y=converted_values,
                        mode="lines",
                        name=f"GPU {gpu_id}",
                        line=dict(color=color, width=2),
                        legendgroup=f"gpu{gpu_id}",
                        showlegend=show_in_legend,
                        connectgaps=True,
                        hovertemplate=f"<b>GPU {gpu_id}</b><br>" +
                                      "Time: %{x}<br>" +
                                      f"{metric}: %{{y:.2f}} {config['unit']}<br>" +
                                      "<extra></extra>"
                    ),
                    row=row, col=col
                )

        # Grafana-style dark theme - pure greyscale
        fig.update_layout(
            paper_bgcolor="#0d1117",  # GitHub dark dim background (pure grey)
            plot_bgcolor="#161b22",  # Slightly lighter plot area (pure grey)
            title_text=f"<b style='color: #c9d1d9; font-size: 18px;'>GPU Oracle Dashboard</b> <span style='color: #8b949e; font-size: 14px;'>| {self.run_name}</span>",
            font=dict(color="#c9d1d9", family="'Inter', -apple-system, BlinkMacSystemFont, sans-serif", size=11),
            height=400 * num_rows + 140,  # Increased height for less compression
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.005,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(13, 17, 23, 0)",
                borderwidth=0,
                font=dict(color="#8b949e", size=11)
            ),
            margin=dict(t=100, b=60, l=70, r=40)
        )

        # Update axes with Grafana-style greyscale theme
        fig.update_xaxes(
            showgrid=True,
            gridcolor="#30363d",  # Subtle grey grid
            gridwidth=1,
            linecolor="#30363d",
            linewidth=1,
            tickcolor="#8b949e",
            tickfont=dict(color="#8b949e", size=10),
            title_font=dict(color="#8b949e", size=11)
        )
        fig.update_yaxes(
            showgrid=True,
            gridcolor="#30363d",  # Subtle grey grid
            gridwidth=1,
            linecolor="#30363d",
            linewidth=1,
            tickcolor="#8b949e",
            tickfont=dict(color="#8b949e", size=10),
            title_font=dict(color="#8b949e", size=11)
        )

        # Update subplot titles with Grafana-style styling
        for annotation in fig['layout']['annotations']:
            annotation['font'] = dict(color='#8b949e', size=12, family="'Inter', sans-serif", weight='normal')

        # Set default output path
        if output_path is None:
            plots_dir = Path(__file__).parent.parent / "plots"
            plots_dir.mkdir(exist_ok=True)
            output_path = plots_dir / f"{self.run_name}.html"

        # Write HTML with custom styling
        html_string = fig.to_html(
            include_plotlyjs="cdn",
            full_html=True,
            config={
                'displayModeBar': True,
                'displaylogo': False,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'responsive': True
            }
        )

        # Add custom CSS for Grafana-like styling
        custom_css = """
        <style>
            * {
                box-sizing: border-box;
            }
            body {
                margin: 0;
                padding: 20px;
                background-color: #0d1117;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                color: #c9d1d9;
            }
            .plotly-graph-div {
                background-color: #0d1117;
            }
            .plotly .modebar {
                background: rgba(22, 27, 34, 0.9) !important;
                border: 1px solid #30363d !important;
            }
        </style>
        """

        # Inject custom CSS
        html_string = html_string.replace('</head>', custom_css + '</head>')

        with open(output_path, 'w') as f:
            f.write(html_string)

        console.print(f"[green]✓[/green] Dashboard saved to: [cyan]{output_path}[/cyan]")
        return output_path

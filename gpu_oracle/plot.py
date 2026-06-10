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

# Dark theme template (Grafana-style)
DARK_THEME = {
    "layout": {
        "paper_bgcolor": "#111827",  # Dark gray background
        "plot_bgcolor": "#1F2937",  # Slightly lighter plot area
        "font": {"color": "#E5E7EB"},  # Light gray text
        "hoverlabel": {
            "bgcolor": "#374151",
            "bordercolor": "#4B5563",
            "font": {"color": "#E5E7EB"}
        },
        "xaxis": {
            "gridcolor": "#374151",
            "linecolor": "#4B5563",
            "tickcolor": "#6B7280",
            "zerolinecolor": "#374151"
        },
        "yaxis": {
            "gridcolor": "#374151",
            "linecolor": "#4B5563",
            "tickcolor": "#6B7280",
            "zerolinecolor": "#374151"
        },
        "legend": {
            "bgcolor": "rgba(31, 41, 55, 0.8)",
            "bordercolor": "#4B5563",
            "font": {"color": "#E5E7EB"}
        }
    }
}

# GPU color palette (distinct, modern colors)
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
        """Generate the HTML dashboard with dark theme."""
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
            vertical_spacing=0.15,
            horizontal_spacing=0.10
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
                        line=dict(color=color, width=1.5),
                        legendgroup=f"gpu{gpu_id}",
                        showlegend=show_in_legend,
                        hovertemplate=f"<b>GPU {gpu_id}</b><br>" +
                                      "Time: %{x}<br>" +
                                      f"{metric}: %{{y:.2f}} {config['unit']}<br>" +
                                      "<extra></extra>"
                    ),
                    row=row, col=col
                )

        # Apply dark theme
        fig.update_layout(
            **{k: v for k, v in DARK_THEME["layout"].items() if k != "font"},
            title_text=f"<b style='color: #E5E7EB'>GPU Oracle Dashboard</b> <span style='color: #6B7280'>| {self.run_name}</span>",
            title_font_size=20,
            font=dict(color="#E5E7EB", family="'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", size=12),
            height=320 * num_rows + 120,
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(17, 24, 39, 0)",
                borderwidth=0
            ),
            margin=dict(t=80, b=50, l=60, r=30)
        )

        # Update subplot axes with dark theme
        fig.update_xaxes(
            gridcolor="#374151",
            linecolor="#4B5563",
            tickcolor="#6B7280",
            showgrid=True,
            gridwidth=1
        )
        fig.update_yaxes(
            gridcolor="#374151",
            linecolor="#4B5563",
            tickcolor="#6B7280",
            showgrid=True,
            gridwidth=1
        )

        # Update subplot titles color
        for annotation in fig['layout']['annotations']:
            annotation['font'] = dict(color='#9CA3AF', size=13, family="'Inter', sans-serif")

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
                'modeBarButtonsToRemove': ['lasso2d', 'select2d']
            }
        )

        # Add custom CSS for better styling
        custom_css = """
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: #111827;
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            }
            .plotly-graph-div {
                background-color: #111827;
            }
        </style>
        """

        # Inject custom CSS
        html_string = html_string.replace('</head>', custom_css + '</head>')

        with open(output_path, 'w') as f:
            f.write(html_string)

        console.print(f"[green]✓[/green] Dashboard saved to: [cyan]{output_path}[/cyan]")
        return output_path

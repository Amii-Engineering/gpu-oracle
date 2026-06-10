# GPU Oracle

Track GPU statistics over time and generate interactive HTML dashboards.

## Features

- Multi-GPU support with parallel tracking
- Configurable metrics via YAML
- Interactive Plotly dashboards for analysis
- Easy sharing of HTML reports
- Graceful shutdown with Ctrl+C

## Requirements

- NVIDIA GPU with NVIDIA drivers
- Python 3.10+
- UV package manager

## Installation

1. Clone the repository:
```bash
cd gpu-stat-tracker
```

2. Install dependencies with UV:
```bash
uv sync
```

## Configuration

Edit `config.yaml` to enable or disable metrics:

```yaml
metrics:
  utilization: true      # GPU utilization (%)
  memory_used: true     # Memory used (MB)
  memory_free: true     # Memory free (MB)
  temperature: true      # Temperature (C)
  power_draw: true      # Power draw (W)
  clock_graphics: true  # Core clock (MHz)
  fan_speed: true       # Fan speed (%)
```

## Usage

### Gathering Metrics

Start gathering GPU metrics:

```bash
uv run gpu-oracle gather --poll-seconds 5
```

Options:
- `--poll-seconds`: Polling interval in seconds (default: 5)
- `--run`: Specify a custom run name (auto-generated if omitted)
- `--config`: Path to custom config file

Press **Ctrl+C** to stop gathering. The tool will:
- Save results to `runs/<run_name>.json`
- Display run statistics
- Show the next command to generate plots

Example output:
```
✓ Run completed
  Duration: 120.5s
  GPUs tracked: 4
  Samples per GPU: 24
  Total samples: 96

Next: uv run gpu-oracle plot --run run_20250610_143026_a7b3c
```

### Generating Dashboards

Create an interactive HTML dashboard:

```bash
uv run gpu-oracle plot --run run_20250610_143026_a7b3c
```

Options:
- `--run`: Run name to plot (required)
- `--output`: Custom output path for HTML file
- `--runs-dir`: Custom directory for run JSON files

The dashboard will be saved to `plots/<run_name>.html`.

### Sharing Results

The generated HTML files are self-contained and can be:
- Opened directly in any web browser
- Shared via email or cloud storage
- Embedded in reports or presentations

## Output Files

### JSON Data Format (`runs/*.json`)

```json
{
  "run_name": "run_20250610_143026_a7b3c",
  "start_time": "2025-06-10T14:30:26-07:00",
  "end_time": "2025-06-10T14:35:10-07:00",
  "poll_seconds": 5,
  "config": {"metrics": {...}},
  "metrics": [
    {"timestamp": "...", "gpu_id": 0, "utilization": 85, "temperature": 72},
    ...
  ]
}
```

### HTML Dashboard (`plots/*.html`)

- Interactive plots with zoom, pan, and hover
- Color-coded lines for each GPU
- Grid layout for multiple metrics
- Responsive design

## Troubleshooting

**NVML Error**: Ensure NVIDIA drivers are installed and accessible:
```bash
nvidia-smi
```

**No GPUs detected**: Check GPU visibility and NVML setup.

**Config file not found**: Ensure `config.yaml` exists in the project root or use `--config`.

## License

See LICENSE file.

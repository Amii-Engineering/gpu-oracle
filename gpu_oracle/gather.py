"""GPU polling and data gathering logic for GPU Oracle."""

import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from gpu_oracle.config import Config
from gpu_oracle.metrics import MetricError, filter_metrics, get_all_metrics, get_gpu_count, get_gpu_name, init_nvml, shutdown_nvml

console = Console()


class Gatherer:
    """Handles GPU metrics gathering with graceful shutdown."""

    def __init__(self, poll_seconds: int, config: Config, run_name: str | None = None):
        self.poll_seconds = poll_seconds
        self.config = config
        self.run_name = run_name or self._generate_run_name()
        self.data: list[dict] = []
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.running = True

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)

    def _generate_run_name(self) -> str:
        """Generate a unique run name based on current time."""
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        # Simple random suffix
        import random
        import string
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"run_{timestamp}_{suffix}"

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        self.running = False

    def _print_startup_info(self):
        """Print startup information."""
        enabled = self.config.get_enabled_metrics()
        console.print(Panel.fit(
            f"[bold cyan]GPU Oracle Gather Mode[/bold cyan]\n"
            f"Run: [bold yellow]{self.run_name}[/bold yellow]\n"
            f"Poll interval: [bold]{self.poll_seconds}s[/bold]\n"
            f"Enabled metrics: [bold]{len(enabled)}[/bold]\n"
            f"[dim]Press Ctrl+C to stop and save results[/dim]",
            title="🚀 Starting",
            border_style="cyan"
        ))

    def _print_summary(self):
        """Print run summary after gathering."""
        duration = (self.end_time - self.start_time).total_seconds()
        num_gpus = get_gpu_count() if self.data else 0
        samples_per_gpu = len(self.data) // num_gpus if num_gpus > 0 else 0

        console.print(Panel.fit(
            f"[bold green]Run completed[/bold green]\n"
            f"Duration: [bold]{duration:.1f}s[/bold]\n"
            f"GPUs tracked: [bold]{num_gpus}[/bold]\n"
            f"Samples per GPU: [bold]{samples_per_gpu}[/bold]\n"
            f"Total samples: [bold]{len(self.data)}[/bold]\n\n"
            f"[bold cyan]Next:[/bold cyan] "
            f"[dim]uv run gpu-oracle plot --run {self.run_name}[/dim]",
            title="✓ Summary",
            border_style="green"
        ))

    def _save_results(self):
        """Save gathered data to JSON file."""
        runs_dir = Path(__file__).parent.parent / "runs"
        runs_dir.mkdir(exist_ok=True)

        output_path = runs_dir / f"{self.run_name}.json"

        result = {
            "run_name": self.run_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "poll_seconds": self.poll_seconds,
            "config": {"metrics": self.config.metrics},
            "metrics": self.data,
        }

        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)

        console.print(f"\n[green]✓[/green] Results saved to: [cyan]{output_path}[/cyan]")
        return output_path

    def run(self):
        """Main gathering loop."""
        try:
            init_nvml()
        except MetricError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

        try:
            num_gpus = get_gpu_count()
            gpu_names = [get_gpu_name(i) for i in range(num_gpus)]

            enabled_metrics = self.config.get_enabled_metrics()

            console.print(f"\nDetected [bold]{num_gpus}[/bold] GPU(s):")
            for i, name in enumerate(gpu_names):
                console.print(f"  GPU {i}: [dim]{name.decode('utf-8') if isinstance(name, bytes) else name}[/dim]")

            self._print_startup_info()
            console.print("\n[dim]Gathering metrics...[/dim]\n")

            self.start_time = datetime.now()

            while self.running:
                # Poll all GPUs
                for gpu_id in range(num_gpus):
                    try:
                        all_metrics = get_all_metrics(gpu_id)
                        filtered = filter_metrics(all_metrics, enabled_metrics)
                        self.data.append(filtered)
                    except MetricError as e:
                        console.print(f"[red]Error polling GPU {gpu_id}:[/red] {e}")

                # Show progress
                elapsed = (datetime.now() - self.start_time).total_seconds()
                console.print(f"[dim]Elapsed: {elapsed:.0f}s | Samples: {len(self.data)}[/dim]", end="\r")
                if "throttling_sw" in filtered:
                    if "throttling_hw" in filtered:
                        for gpu_id in range(num_gpus):
                            sw = self.data[-num_gpus + gpu_id].get("throttling_sw") or 0.0
                            hw = self.data[-num_gpus + gpu_id].get("throttling_hw") or 0.0
                            console.print(
                                f"\n[dim]GPU {gpu_id} - SW Throttle: {sw:.2f} hours | "
                                f"HW Throttle: {hw:.2f} hours[/dim]", end=""
                            )

                        console.print("", end=f"\033[{num_gpus}F")
                    else:
                        raise Exception("throttling_sw metric is present but throttling_hw is missing. This should not happen.")
                    
                time.sleep(self.poll_seconds)

            self.end_time = datetime.now()

            # Print final summary without carriage return
            console.print("")  # Clear the progress line
            self._print_summary()
            self._save_results()

        finally:
            shutdown_nvml()

"""Configuration file handling for GPU Oracle."""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Config:
    """GPU Oracle configuration."""

    metrics: dict[str, bool]

    @classmethod
    def from_file(cls, path: str | Path) -> "Config":
        """Load configuration from a YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        return cls(metrics=data.get("metrics", {}))

    def get_enabled_metrics(self) -> list[str]:
        """Get list of enabled metric names."""
        return [name for name, enabled in self.metrics.items() if enabled]


def get_default_config_path() -> Path:
    """Get the default config file path."""
    # First check if config.yaml exists in the current directory
    local_config = Path.cwd() / "config.yaml"
    if local_config.exists():
        return local_config

    # Fall back to the package's default config
    package_dir = Path(__file__).parent.parent
    return package_dir / "config.yaml"

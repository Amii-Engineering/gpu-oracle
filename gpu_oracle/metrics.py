"""Metric definitions and NVML wrappers for GPU Oracle."""

from datetime import datetime

import pynvml


class MetricError(Exception):
    """Error raised when a metric cannot be retrieved."""


def init_nvml() -> None:
    """Initialize NVML library."""
    try:
        pynvml.nvmlInit()
    except pynvml.NVMLError as e:
        raise MetricError(f"Failed to initialize NVML: {e}")


def shutdown_nvml() -> None:
    """Shutdown NVML library."""
    try:
        pynvml.nvmlShutdown()
    except pynvml.NVMLError:
        pass


def get_gpu_count() -> int:
    """Get the number of GPUs in the system."""
    try:
        return pynvml.nvmlDeviceGetCount()
    except pynvml.NVMLError as e:
        raise MetricError(f"Failed to get GPU count: {e}")


def get_gpu_name(device_index: int) -> str:
    """Get the name of a GPU."""
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(device_index)
        return pynvml.nvmlDeviceGetName(handle)
    except pynvml.NVMLError as e:
        raise MetricError(f"Failed to get GPU {device_index} name: {e}")


def get_all_metrics(gpu_id: int) -> dict[str, float | None]:
    """Get all available metrics for a specific GPU."""
    try:
        handle = pynvml.nvmlDeviceGetHandleByIndex(gpu_id)
    except pynvml.NVMLError as e:
        raise MetricError(f"Failed to get handle for GPU {gpu_id}: {e}")

    metrics: dict[str, float | None] = {"gpu_id": gpu_id}
    timestamp = datetime.now().isoformat()
    metrics["timestamp"] = timestamp

    # Utilization
    try:
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        metrics["utilization"] = float(util.gpu)
    except pynvml.NVMLError:
        metrics["utilization"] = None

    # Memory
    try:
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        metrics["memory_used"] = mem_info.used / (1024 * 1024)  # Convert to MB
        metrics["memory_free"] = mem_info.free / (1024 * 1024)
        metrics["memory_total"] = mem_info.total / (1024 * 1024)
    except pynvml.NVMLError:
        metrics["memory_used"] = None
        metrics["memory_free"] = None
        metrics["memory_total"] = None

    # Temperature
    try:
        metrics["temperature"] = float(pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU))
    except pynvml.NVMLError:
        metrics["temperature"] = None

    # Power draw
    try:
        metrics["power_draw"] = float(pynvml.nvmlDeviceGetPowerUsage(handle) / 1000)  # Convert mW to W
    except pynvml.NVMLError:
        metrics["power_draw"] = None

    # Clock speeds
    try:
        metrics["clock_graphics"] = float(pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS))
    except pynvml.NVMLError:
        metrics["clock_graphics"] = None

    try:
        metrics["clock_sm"] = float(pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_SM))
    except pynvml.NVMLError:
        metrics["clock_sm"] = None

    try:
        metrics["clock_memory"] = float(pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_MEM))
    except pynvml.NVMLError:
        metrics["clock_memory"] = None

    # Fan speed
    try:
        metrics["fan_speed"] = float(pynvml.nvmlDeviceGetFanSpeed(handle))
    except pynvml.NVMLError:
        metrics["fan_speed"] = None

    # PCI throughput
    try:
        pci_tx = pynvml.nvmlDeviceGetPcieThroughput(handle, pynvml.NVML_PCIE_UTIL_TX_BYTES)
        pci_rx = pynvml.nvmlDeviceGetPcieThroughput(handle, pynvml.NVML_PCIE_UTIL_RX_BYTES)
        metrics["pci_tx"] = pci_tx / (1024 * 1024)  # Convert KB/s to MB/s
        metrics["pci_rx"] = pci_rx / (1024 * 1024)
    except pynvml.NVMLError:
        metrics["pci_tx"] = None
        metrics["pci_rx"] = None

    # GPU thermal throttling
    try:
        throttling_reasons = int(pynvml.nvmlDeviceGetCurrentClocksThrottleReasons(handle))
        metrics["throttling_reasons"] = throttling_reasons
    except pynvml.NVMLError:
        metrics["throttling_reasons"] = None

    return metrics


def filter_metrics(all_metrics: dict[str, float | None], enabled_metrics: list[str]) -> dict[str, float | None]:
    """Filter metrics to only include enabled ones, plus timestamp and gpu_id."""
    # Always include timestamp and gpu_id
    filtered = {
        "timestamp": all_metrics["timestamp"],
        "gpu_id": all_metrics["gpu_id"],
    }

    # Add only enabled metrics
    for metric in enabled_metrics:
        if metric in all_metrics:
            filtered[metric] = all_metrics[metric]

    return filtered

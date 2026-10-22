import math
import re


def model_name(hardware, company, series, model):
    if company == "apple":
        return f"Apple {model}"
    if company == "intel":
        separator = "-" if re.fullmatch(f"Intel Core i[3579]", series) else " "
        return f"{series}{separator}{model}"
    if hardware == "cpu":
        return f"{series} {model}"
    if company == "amd":
        return f"AMD Radeon {model}"

    return f"NVIDIA {'GeForce ' if model.startswith('RTX ') else ''}{model}"


def score(record, metric):
    if not record or record.get("status") != "available":
        return None
    value = ((record.get("scores") or {}).get(metric) or {}).get("score")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(value) and value > 0:
            return value

    return None


def compare_scores(left, right, hardware):
    metrics = {"single-core": "Single-core", "multi-core": "Multi-core"}
    if hardware == "gpu":
        metrics = {"vulkan": "Vulkan compute"}

    left = left or {}
    right = right or {}
    version = left.get("geekbenchVersion")
    compatible = bool (
        version and version == right.get("geekbenchVersion") and left.get("type") == right.get("type") == hardware.upper()
    )
    rows = []
    for key, label in metrics.items():
        a, b = score(left, key), score(right, key)
        rows.append({
            "label": label, "a": a, "b": b, "difference": (a - b) / b * 100 if compatible and a is not None and b is not None else None,
        })

    return {"rows": rows, "compatible": compatible}
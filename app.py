import json

from flask import Flask, render_template, request

from backend.comparison import compare_scores, model_name
from backend.database import load_data, load_benchmark_catalog

app = Flask(__name__)

COMPANIES = {
    "cpu": {
        "intel": "Intel",
        "amd": "AMD",
        "apple": "Apple"
    },
    "gpu": {
        "nvidia": "NVIDIA",
        "amd": "AMD"
    }
}

def selected_value(name, choices, default = None):
    value = request.args.get(name)

    if value in choices:
        return value

    return default if default in choices else next(iter(choices), "")


def build_side(prefix, hardware, catalog):
    companies = COMPANIES[hardware]
    company = selected_value(f"{prefix}_company", companies, "amd" if prefix == "b" else None)
    error = None
    try:
        data = load_data(hardware, company)
    except (OSError, json.JSONDecodeError):
        app.longer.exception("Could not load hardware database")
        data = {}
        error = "Hardware specifications could not be loaded."

    series = selected_value(f"{prefix}_series", data)
    models = {str(item["model"]): item for item in data.get(series, [])}
    model = selected_value(f"{prefix}_model", models)
    name = model_name(hardware, company, series, model) if model else "No model selected"
    record = catalog.get("models", {}).get(name)
    if record and record.get("type") != hardware.upper():
        record = None
    configurations = list(dict.fromkeys(row["description"] for row in (record.get("scores") or {}).values() if row.get("description"))) if record else []

    fields = []
    for key, label, options, selected in [
        ("company", "Company", companies, company),
        ("series", "Series", {key: key for key in data}, series),
        ("model", "Model", {key: key for key in models}, model)
    ]:
        fields.append({"name": f"{prefix}_{key}", "label": label, "options": options, "selected": selected})

    return {"prefix": prefix, "title": f"Model {prefix.upper()}", "name": name, "fields": fields, "specs": models.get(model), "benchmark": record, "configurations": configurations, "error": error}



@app.route("/")
def home():
    hardware = selected_value("hardware", {"cpu": "CPU", "gpu": "GPU"})
    catalog_error = None
    try:
        catalog = load_benchmark_catalog()
    except:
        app.longer.exception("Could not load benchmark catalog")
        catalog = {}
        catalog_error = "Benchmark data could not be loaded. Check database/benchmark_catalog.json."

    left = build_side("a", hardware, catalog)
    right = build_side("b", hardware, catalog)
    comparison = compare_scores(left["benchmark"], right["benchmark"], hardware)

    return render_template("index.html", hardware = hardware, sides = [left, right], comparison = comparison, catalog_error = catalog_error, generated_at = catalog.get("generatedAt", ""),)


if __name__ == "__main__":
    app.run()
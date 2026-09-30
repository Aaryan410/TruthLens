import json
from pathlib import Path

def load_data(component, company):

    data_file = Path(__file__).parent.parent / "database" / component / f"{company}.json"

    if not data_file.exists():
        raise FileNotFoundError(f"No JSON files found in {data_file}")

    with open(data_file, "r", encoding = "utf-8") as file:
        return json.load(file)

import database

component = input("Component > ").strip().lower()
company = input("Company > ").strip().lower()

component_database = database.load_data(component, company)

print()

print("Available Series:")
for series in component_database:
    print("-", series)

series = input("Series > ").strip()

if series not in component_database:
    print("Series not found.")
    exit()

models = component_database[series]

print()

print("Available Models:")
for hardware in models:
    print("-", hardware["model"])

print()

model = input("Model > ")

selected_model = None

for hardware in models:
    if hardware["model"] == model:
        selected_model = hardware
        break

if selected_model is None:
    print("Model not found.")
    exit()

print()
print(f"Model: {selected_model['model']}")

for key, value in selected_model.items():

    if key == "model":
        continue

    if isinstance(value, dict):
        print(f"{key}:")

        for sub_key, sub_value in value.items():
            print(f" {sub_key}: {sub_value}")

    else:
        print(f"{key}: {value}")


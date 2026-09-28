import database

company = input("Company > ").strip()

component_database = database.load_data(company)

series = input("Series > ").strip()

series_data = component_database[series]

models = component_database[series]

model = input("Model > ")

selected_model = None

for hardware in models:
    if hardware["model"] == model:
        selected_model = hardware
        break

if selected_model is None:
    print("Model not found.")
    exit()


cores = selected_model["cores"]
threads = selected_model["threads"]
clock_rate_base = selected_model["clock_rate"]["base"]
clock_rate_turbo = selected_model["clock_rate"]["turbo"]

if "tvb" in selected_model["clock_rate"]:
    tvb = selected_model["clock_rate"]["tvb"]
else:
    tvb = None

tdp = selected_model["tdp"]

print()

print(f"Model: {selected_model['model']}")
print(f"Cores: {cores}")
print(f"Threads: {threads}")
print(f"Base Clock Rate: {clock_rate_base}")
print(f"Trubo Clock Rate: {clock_rate_turbo}")

if tvb is not None:
    print(f"TVB: {tvb}")

print(f"TDP: {tdp}")


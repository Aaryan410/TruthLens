import database

component = input("Component > ")

component_database = database.load_data(component)

print(component_database)

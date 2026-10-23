from pathlib import Path
import shutil

def prepare_static():
    root = Path(__file__).resolve().parent
    source = root / "static"
    destination = root / "public" / "static"
    destination.mkdir(parents = True, exist_ok = True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, destination / item.name)
        elif item.is_dir():
            shutil.copytree(item, destination / item.name, dirs_exist_ok = True)


if __name__ == "__main__":
    prepare_static()
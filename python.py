"""Start the ShockPath backend directly from PyCharm or python python.py."""
import os
from pathlib import Path
import sys


def main():
    # Keep module resolution and child processes anchored to this project.
    os.chdir(Path(__file__).resolve().parent)
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    from scripts.serve_backend import main as serve_backend
    serve_backend()


if __name__ == "__main__":
    main()

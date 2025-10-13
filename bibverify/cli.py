import os
import sys
import runpy


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    script_path = os.path.join(project_root, "bib_check.py")
    if not os.path.exists(script_path):
        print("bib_check.py Not Found")
        sys.exit(1)

    sys.argv = [script_path] + sys.argv[1:]
    runpy.run_path(script_path, run_name="__main__")



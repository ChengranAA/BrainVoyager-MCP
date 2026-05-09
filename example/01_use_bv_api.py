import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from API import bv_api as bv
from pprint import pprint

if __name__ == "__main__":
    print("Example usage with Brainvoyager API")
    print(f"Listener URL: {bv.BV_LISTENER_URL}")
    methods = bv.get_bv_methods()
    for method in methods:
        print("Method: ", method)
        description = bv.describe_bv_method(method)
        print("Description: ", description)



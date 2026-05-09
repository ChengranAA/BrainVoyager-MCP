import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from API import bv_api as bv


if __name__ == "__main__":
    bv.open_bv_document("/Users/chengran/Documents/small_projects/bv_mcp/test_data/VMRs/Pilot_UNI.vmr")
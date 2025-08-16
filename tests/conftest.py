import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

trading_platform = types.ModuleType("trading_platform")
trading_platform.__path__ = [str(ROOT)]
sys.modules.setdefault("trading_platform", trading_platform)

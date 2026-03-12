from .types import BakeMode, RelinkSpec
from .standard import STANDARD_MODES
from .pbr import PBR_MODES

BAKE_MODES: dict[str, BakeMode] = {**STANDARD_MODES, **PBR_MODES}

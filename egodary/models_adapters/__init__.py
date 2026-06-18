"""Model output adapters (Illustrious, Anima, Z-Image Turbo)."""

from egodary.models_adapters.base import ModelAdapter
from egodary.models_adapters.anima import AnimaAdapter
from egodary.models_adapters.illustrious import IllustriousAdapter
from egodary.models_adapters.zimage_turbo import ZImageTurboAdapter

__all__ = ["IllustriousAdapter", "AnimaAdapter", "ZImageTurboAdapter", "ModelAdapter"]

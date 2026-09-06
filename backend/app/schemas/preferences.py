"""
Presentation preferences for one account.

CLOSED LITERALS, not free strings. A theme of "drak" must be a 422 at
the edge, not a silent fallback three components deep where nobody
will ever find it.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field

Theme     = Literal["light", "dark", "system"]
FontSize  = Literal["small", "default", "large", "larger"]

class Preferences(BaseModel):
    theme: Theme = "system"
    font_size: FontSize = "default"
    reduce_motion: bool = False
    high_contrast: bool = False
    colourblind_safe: bool = False

class PreferencesUpdate(BaseModel):
    """Every field optional — PATCH semantics, one toggle at a time."""
    theme: Optional[Theme] = None
    font_size: Optional[FontSize] = None
    reduce_motion: Optional[bool] = None
    high_contrast: Optional[bool] = None
    colourblind_safe: Optional[bool] = None

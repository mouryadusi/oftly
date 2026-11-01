"""Contract types. Only attributes and ids cross the boundary; names, notes, photos and free text never do for ranking."""
from typing import Optional, Protocol

from pydantic import BaseModel, Field

CONTRACT = "oftly.intelligence/1"
MAX_DELTA = 8.0          # a provider can nudge a 0-100 score by at most this much, and OFTLY reports it separately


class PieceView(BaseModel):
    id: int
    slot: str
    category: str
    colour: str = ""
    pattern: str = ""
    style: str = ""
    formality: int = 3


class OutfitView(BaseModel):
    id: str
    pieces: list[PieceView]
    base_score: float


class RankContext(BaseModel):
    occasion: Optional[str] = None
    climate_band: Optional[str] = None
    temp_c: Optional[float] = None
    rain_chance: Optional[float] = None
    favorite_colors: list[str] = Field(default_factory=list)
    disliked_colors: list[str] = Field(default_factory=list)


class Adjustment(BaseModel):
    id: str
    delta: float = Field(ge=-MAX_DELTA, le=MAX_DELTA)
    note: str = Field("", max_length=200)


class Suggestion(BaseModel):
    """A model *suggestion*. Never written to a confirmed field without the user's say-so."""
    field: str = Field(max_length=40)
    value: str = Field(max_length=80)
    confidence: float = Field(ge=0, le=1)


class Provider(Protocol):
    name: str
    def status(self) -> dict: ...
    def rank_outfits(self, outfits: list[OutfitView], ctx: RankContext) -> list[Adjustment]: ...
    def suggest_attributes(self, image_bytes: bytes, content_type: str) -> list[Suggestion]: ...


class NullProvider:
    name = "none"

    def __init__(self, reason: str = "No intelligence service configured; OFTLY uses its built-in deterministic engine."):
        self.reason = reason

    def status(self):
        return {"provider": self.name, "enabled": False, "contract": CONTRACT, "detail": self.reason}

    def rank_outfits(self, outfits, ctx):
        return []

    def suggest_attributes(self, image_bytes, content_type):
        return []

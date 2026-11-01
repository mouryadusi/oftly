"""Pydantic request models."""
import re
from datetime import date as Date
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

SAFE_IMG = re.compile(r"^[A-Za-z0-9_-]{1,64}\.jpg$")
Status = Literal["available", "laundry", "retired"]

class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str
    subcategory: str = Field("", max_length=80)
    image: Optional[str] = None
    primary_color: str = Field("", max_length=40)
    secondary_colors: list[str] = Field(default_factory=list, max_length=6)
    pattern: str = Field("solid", max_length=40)
    brand: str = Field("", max_length=80)
    product_url: str = Field("", max_length=1000)
    price: Optional[float] = Field(None, ge=0, le=10_000_000)
    description: str = Field("", max_length=2000)
    style: str = Field("", max_length=40)
    occasions: list[str] = Field(default_factory=list, max_length=12)
    seasons: list[str] = Field(default_factory=list, max_length=4)
    formality: int = Field(3, ge=1, le=5)
    favorite: bool = False
    status: Status = "available"
    notes: str = Field("", max_length=2000)

    @field_validator("name", mode="before")
    @classmethod
    def _strip(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("image")
    @classmethod
    def _img(cls, v):
        if v and not SAFE_IMG.match(v):
            raise ValueError("invalid image name")
        return v or None

    @field_validator("product_url")
    @classmethod
    def _url(cls, v):
        if v and not re.match(r"^https?://", v, re.I):
            raise ValueError("product URL must start with http:// or https://")
        return v

    @field_validator("primary_color", "pattern", "style", mode="before")
    @classmethod
    def _lower(cls, v):
        return v.strip().lower() if isinstance(v, str) else v

    @field_validator("secondary_colors", "occasions", "seasons", mode="before")
    @classmethod
    def _lower_list(cls, v):
        return [str(x).strip().lower() for x in v if str(x).strip()] if isinstance(v, list) else v

class OutfitIn(BaseModel):
    name: str = Field("", max_length=120)
    notes: str = Field("", max_length=2000)
    item_ids: list[int] = Field(min_length=2, max_length=12)
    score: Optional[float] = None
    reason: str = Field("", max_length=1000)

class OutfitCtx(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=12)
    replace_id: Optional[int] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    destination: str = Field("", max_length=80)
    day: int = Field(0, ge=0, le=6)
    limit: int = Field(8, ge=1, le=30)

class WearIn(BaseModel):
    date: Optional[Date] = None

class CalendarIn(BaseModel):
    date: Date
    outfit_id: int
    worn: bool = False
    notes: str = Field("", max_length=1000)

class FeedbackIn(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=12)
    action: Literal["reject", "like", "wear"]

class CategoryIn(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_]{2,30}$")
    label: str = Field(min_length=1, max_length=50)
    slot: Literal["top", "bottom", "dress", "shoes", "bag", "accessory"]

class UrlIn(BaseModel):
    url: str = Field(max_length=1000)

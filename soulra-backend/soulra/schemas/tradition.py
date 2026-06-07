from pydantic import BaseModel


class TraditionOut(BaseModel):
    slug: str
    name: str
    origin: str
    era: str
    sources: int
    passages: int
    selected: bool

    model_config = {"from_attributes": True}


class TraditionsResponse(BaseModel):
    traditions: list[TraditionOut]
    total_sources: int
    total_passages: int


class PreferencesUpdate(BaseModel):
    selected: list[str]


class CreateTradition(BaseModel):
    name: str
    origin: str
    era: str
    slug: str | None = None
    description: str | None = None

from pydantic import BaseModel


class PassageOut(BaseModel):
    id: str
    content: str
    tradition: str | None = None
    author: str | None = None
    source: str | None = None
    era: str | None = None
    citation: str | None = None

from pydantic import BaseModel


class HTTPError(BaseModel):
    error: str
    error_description: str


class ValidationError(BaseModel):
    error: str
    error_description: str
    fields: list[str]

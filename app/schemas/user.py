from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints


class UserBase(BaseModel):
    email: EmailStr
    name: str
    identity: str
    referral_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserIn(UserBase):
    password: Annotated[str, StringConstraints(min_length=8)]


class UserOut(UserBase):
    id: int

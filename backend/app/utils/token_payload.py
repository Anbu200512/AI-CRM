from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: int
    exp: int

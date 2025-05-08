from pydantic import BaseModel

class JoinPoolRequest(BaseModel):
    token: str
from pydantic import BaseModel


class CsiRawResponse(BaseModel):
    message: str
    node_id: str
    seq_num: int

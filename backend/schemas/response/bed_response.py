from pydantic import BaseModel, ConfigDict


class BedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bed_id: str
    node_id: str
    nickname: str
    age: int
    disease: str


class BedsResponse(BaseModel):
    beds: list[BedResponse]
from pydantic import BaseModel, ConfigDict, Field, field_validator


class BedCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    bed_id: str = Field(..., min_length=1, max_length=50)
    node_id: str = Field(..., min_length=1, max_length=50)
    nickname: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=0, le=150)
    disease: str = Field(..., min_length=1, max_length=200)

    @field_validator("bed_id", "node_id", "nickname", "disease")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("공백만 입력할 수 없습니다.")

        return value

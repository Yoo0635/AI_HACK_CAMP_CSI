from sqlalchemy import Column, Integer, String

from backend.config.database import Base


class Bed(Base):
    __tablename__ = "beds"

    id = Column(Integer, primary_key=True, index=True)
    bed_id = Column(String, nullable=False, unique=True)
    node_id = Column(String, unique=True)
    nickname = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    disease = Column(String, nullable=False)

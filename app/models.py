from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db import Base

class Prayer(Base):
    __tablename__ = "prayers"

    id = Column(Integer, primary_key=True)
    prayer_name = Column(String, nullable=False)
    request = Column(String)
    phone = Column(String)
    contact_name = Column(String)
    tag_contact = Column(Boolean, default=False)
    target_list = Column(String)
    created_at = Column(DateTime, server_default=func.now())

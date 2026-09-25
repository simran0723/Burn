from sqlalchemy import Column ,String,Integer,Float,Date

from app.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True,index = True)
    name = Column(String,nullable=False)
    price = Column(Float,nullable=False)
    billing_cycle = Column(String,nullable=False)
    renewal_date  = Column(Date,nullable=False)
    
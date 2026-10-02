from sqlalchemy import Column ,String,Integer,Float,Date,Boolean,ForeignKey

from app.database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True,index = True)
    name = Column(String,nullable=False)
    email = Column(String , nullable=False)
    price = Column(Float,nullable=False)
    billing_cycle = Column(String,nullable=False)
    renewal_date  = Column(Date,nullable=False)
    notification_sent = Column(Boolean, default= False )
    user_id = Column(Integer , ForeignKey("users.id"),nullable=False)
    
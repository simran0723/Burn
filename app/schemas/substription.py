from pydantic import BaseModel
from datetime import date

class SubscriptionCreate(BaseModel):
    name : str
    price : float
    billing_cycle : str
    renewal_date  : date

class SubscriptionUpdate(BaseModel):
    name : str
    price : float
    billing_cycle : str
    renewal_date : date

    
  
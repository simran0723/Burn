from fastapi import FastAPI,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.schemas.substription import SubscriptionCreate,SubscriptionUpdate
from app.database import Base, engine
from app.models.subscription import Subscription
from datetime import date,timedelta
from dotenv import load_dotenv
import os

app = FastAPI()

load_dotenv()

print(os.getenv("EMAIL_ADDRESS"))

Base.metadata.create_all(bind=engine)
@app.get("/")
def home ():
    return{
        "message" : "Subscription Tracker"
    }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/subscriptions")
def create_subscription(subscription : SubscriptionCreate ,db : Session = Depends(get_db)):
    db = SessionLocal()
    new_subscription = Subscription(
        name = subscription.name,
        email = subscription.email,
        price = subscription.price,
        billing_cycle = subscription.billing_cycle,
        renewal_date  = subscription.renewal_date

    )
    try: 
        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException (status_code=500 , detail="Failed to create subscription")
        
    return new_subscription

@app.get("/subscriptions")
def get_subscription():
    db = SessionLocal()

    subscriptions = db.query(Subscription).all()

    db.close()
    return subscriptions

@app.get("/subscriptions/upcoming")
def get_upcoming_subscription(db : Session=Depends(get_db)):
    today = date.today()
    next_7days = today + timedelta(days=7)
    subscriptions = db.query(Subscription).filter(Subscription.renewal_date >= today , Subscription.renewal_date <= next_7days).all()
    return subscriptions

@app.get("/subscriptions/yearly_cost")
def get_yearly_cost(db :Session= Depends(get_db)):
    subscriptions = db.query(Subscription).all()
    yearly_cost = 0
    for subscription in subscriptions:
        if subscription.billing_cycle.lower() == "monthly":
            yearly_cost += subscription.price *12
        elif subscription.billing_cycle.lower() == "yearly":
            yearly_cost += subscription.price

    return {
        "yearly_cost": yearly_cost
    }

@app.get("/subscriptions/filter")
def filter_subscriptions(billing_cycle :str , db : Session = Depends(get_db)):
    subscriptions = db.query(Subscription).filter(Subscription.billing_cycle == billing_cycle).all()
    return subscriptions

@app.get("/subscriptions/renewal_alert")
def get_renewal_alert(db :Session = Depends(get_db)):
    today = date.today()
    alert_date = today+ timedelta(days=3)
    subscriptions = db.query(Subscription).filter(Subscription.renewal_date >= today ,Subscription.renewal_date <= alert_date).all()

    return subscriptions




@app.get("/subscriptions/monthly-cost")
def get_monthly_cost(db: Session = Depends(get_db)):

    subscriptions = db.query(Subscription).all()

    monthly_cost = 0

    for subscription in subscriptions:
        if subscription.billing_cycle.lower() == "monthly":
            monthly_cost += subscription.price
        elif subscription.billing_cycle.lower() == "yearly":
            monthly_cost += subscription.price/12

    return {"monthly_cost": monthly_cost}

@app.get("/subscriptions/{subscription_id}")
def get_subscription(subscription_id : int):
    db= SessionLocal()

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()

    db.close()
    return subscription

@app.put("/subscriptions/{subscription_id}")
def update_subscription(subscription_id : int , subscription : SubscriptionUpdate , db:Session = Depends(get_db)):
    existing_subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if existing_subscription is None:
        raise HTTPException (status_code=404,detail="subscription not found")
    existing_subscription.name = subscription.name
    existing_subscription.price = subscription.price
    existing_subscription.billing_cycle = subscription.billing_cycle
    existing_subscription.renewal_date = subscription.renewal_date


    try :
        db.commit()
        db.refresh(existing_subscription)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500 , detail="Failed to Update Subscription")

    return existing_subscription




@app.delete("/subscriptions/{subscription_id}")
def delete_subscription(subscription_id : int , db:Session = Depends(get_db)):
    existing_subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if existing_subscription is None:
            raise HTTPException (status_code=404,detail="subscription not found")

    try:
        db.delete(existing_subscription)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500 , detail="Failed to delete subscription")

    return {
        "message" : "Subscription deleted Successfully"
    }



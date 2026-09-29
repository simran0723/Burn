from sched import scheduler
from fastapi import FastAPI,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import SessionLocal
from app.schemas.substription import SubscriptionCreate,SubscriptionUpdate
from app.schemas.user import UserCreate , UserLogin
from app.database import Base, engine
from app.models.subscription import Subscription
from app.models.user import User
from datetime import date,timedelta
from dotenv import load_dotenv
import os
from app.email_service import send_email
from apscheduler.schedulers.background import BackgroundScheduler
import bcrypt
from app.auth import create_access_token



app = FastAPI()
Base.metadata.create_all(bind=engine)

job_schedular  = BackgroundScheduler()

load_dotenv()

print(os.getenv("EMAIL_ADDRESS"))


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

@app.post("/register")
def  register_user(user:UserCreate , db:Session = Depends(get_db)):
    hashed_password = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
      raise HTTPException(
        status_code=400,
        detail="Email already registered"
    )
    new_user = User(name = user.name,email = user.email , password = hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.post("/login")
def user_login (user : UserLogin , db:Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user is None :
        raise HTTPException (status_code= 401 , detail="Invalid user or password")
    if not bcrypt.checkpw(user.password.encode("utf-8"),existing_user.password.encode("utf-8")):
        raise HTTPException(status_code=401,detail="Invalid user email and password")
   
    access_token = create_access_token({
    "user_id": existing_user.id})

    return {
    "access_token": access_token,
    "token_type": "bearer"
}
    


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
@app.get("/test-email")
def test_email():
    send_email(
        "01simransoni@gmail.com",
        "Burn Test Email",
        "This is the test Email from burn "
    )
    return{"message":"Email sent successfully"}




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

def check_renewals():
    db = SessionLocal()

    try:
        today = date.today()
        alert_date = today + timedelta(days=3)

        subscriptions = db.query(Subscription).filter(
            Subscription.renewal_date >= today,
            Subscription.renewal_date <= alert_date
        ).all()

        for subscription in subscriptions:
            if not subscription.notification_sent:
                send_email(
                    subscription.email,
                    "Burn - Subscription Renewal Alert",
                    f"Your {subscription.name} subscription will renew on {subscription.renewal_date}. "
                    f"Amount: ₹{subscription.price}"
                )

                subscription.notification_sent = True

        db.commit()

    finally:
        db.close()




@app.get("/subscriptions/renewal_alert")

def get_renewal_alert(db :Session = Depends(get_db)):
    today = date.today()
    alert_date = today+ timedelta(days=3)
    subscriptions = db.query(Subscription).filter(Subscription.renewal_date >= today ,Subscription.renewal_date <= alert_date).all()


    for subscription in subscriptions:
        if not subscription.notification_sent:
            send_email(
            subscription.email,
            "Burn - Subscription Renewal Alert",
            f"Your {subscription.name} subscription will renew on {subscription.renewal_date}. "
            f"Amount: ₹{subscription.price}"
            )

            subscription.notification_sent = True
    db.commit()
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

job_schedular.add_job(check_renewals, "interval", days=1)
job_schedular.start()

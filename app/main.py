
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
from app.auth import create_access_token,verify_access_token
from fastapi.security import HTTPAuthorizationCredentials,HTTPBearer


app = FastAPI()
security = HTTPBearer()
Base.metadata.create_all(bind=engine)

job_schedular  = BackgroundScheduler()

load_dotenv()

print(os.getenv("EMAIL_ADDRESS"))


def get_current_user(credentials :HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    user_id = verify_access_token(token)
    if user_id is None :
        raise HTTPException(status_code=401 , detail="Invalid or expired token")
    return user_id



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

def check_renewals():
    db = SessionLocal()

    try:
        today = date.today()
        alert_date = today + timedelta(days=7)

        subscriptions = db.query(Subscription).filter(
            Subscription.renewal_date >= today,
            Subscription.renewal_date <= alert_date
        ).all()

        for subscription in subscriptions:
            if not subscription.notification_sent:

                email_body = f"""
                <html>
                    <body>
                        <h2>🔔 Burn - Subscription Renewal Reminder</h2>

                        <p>Hi,</p>

                        <p>
                            Your <strong>{subscription.name}</strong>
                            subscription is renewing soon.
                        </p>

                        <h3>Subscription Details</h3>

                        <p><strong>Subscription:</strong> {subscription.name}</p>
                        <p><strong>Amount:</strong> ₹{subscription.price}</p>
                        <p><strong>Renewal Date:</strong> {subscription.renewal_date}</p>

                        <p>
                            Please make sure your payment method is ready
                            for the upcoming renewal.
                        </p>

                        <p>
                            — <strong>Burn</strong><br>
                            <i>Track your subscriptions. Know your burn.</i>
                        </p>
                    </body>
                </html>
                """

                send_email(
                    subscription.email,
                    "🔔 Burn - Subscription Renewal Reminder",
                    email_body
                )

                subscription.notification_sent = True

        db.commit()

    finally:
        db.close()
    


@app.post("/subscriptions")
def create_subscription(subscription : SubscriptionCreate ,db : Session = Depends(get_db),current_user :int= Depends(get_current_user)):
   
    new_subscription = Subscription(
        name = subscription.name,
        email = subscription.email,
        price = subscription.price,
        billing_cycle = subscription.billing_cycle,
        renewal_date  = subscription.renewal_date,
        user_id = current_user

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
def get_subscriptions(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)):
    subscriptions = db.query(Subscription).filter(Subscription.user_id == current_user).all()
    return subscriptions




@app.get("/subscriptions/upcoming")
def get_upcoming_subscription(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    today = date.today()
    next_7days = today + timedelta(days=7)

    subscriptions = db.query(Subscription).filter(
        Subscription.renewal_date >= today,
        Subscription.renewal_date <= next_7days,
        Subscription.user_id == current_user
    ).all()

    return subscriptions

@app.get("/subscriptions/yearly_cost")
def get_yearly_cost(
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    subscriptions = db.query(Subscription).filter(
        Subscription.user_id == current_user
    ).all()

    yearly_cost = 0

    for subscription in subscriptions:
        if subscription.billing_cycle.lower() == "monthly":
            yearly_cost += subscription.price * 12
        elif subscription.billing_cycle.lower() == "yearly":
            yearly_cost += subscription.price

    return {
        "yearly_cost": yearly_cost
    }

@app.get("/subscriptions/filter")
def filter_subscriptions(
    billing_cycle: str,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):
    subscriptions = db.query(Subscription).filter(
        Subscription.billing_cycle == billing_cycle,
        Subscription.user_id == current_user
    ).all()

    return subscriptions





#  we need to manually hit this to get notification which is useless  for manual testing  
# @app.get("/subscriptions/renewal_alert")

# def get_renewal_alert(db :Session = Depends(get_db) , current_user:int = Depends(get_current_user)):
#     today = date.today()
#     alert_date = today+ timedelta(days=7)

#     subscriptions = db.query(Subscription).filter(Subscription.renewal_date >= today ,Subscription.renewal_date <= alert_date
#     ,Subscription.user_id == current_user).all()


#     for subscription in subscriptions:
#         if not subscription.notification_sent:
#             send_email(
#             subscription.email,
#             "Burn - Subscription Renewal Alert",
#             f"Your {subscription.name} subscription will renew on {subscription.renewal_date}. "
#             f"Amount: ₹{subscription.price}"
#             )

#             subscription.notification_sent = True
#     db.commit()
#     return subscriptions


# @app.get("/test-email")
# def test_email():
#     send_email(
#         "2307simransoni@gmail.com",
#         "Burn Test Email",
#         "This is a test email from Burn."
#     )

#     return {"message": "Test email sent"}



@app.get("/subscriptions/monthly-cost")
def get_monthly_cost(db: Session = Depends(get_db),current_user :int = Depends(get_current_user)):

    subscriptions = db.query(Subscription).filter(Subscription.user_id == current_user).all()

    monthly_cost = 0

    for subscription in subscriptions:
        if subscription.billing_cycle.lower() == "monthly":
            monthly_cost += subscription.price
        elif subscription.billing_cycle.lower() == "yearly":
            monthly_cost += subscription.price/12

    return {"monthly_cost": monthly_cost}

@app.get("/subscriptions/{subscription_id}")
def get_subscription(subscription_id : int,db:Session = Depends(get_db) , current_user : int = Depends(get_current_user)):
  

    subscription = db.query(Subscription).filter(Subscription.id == subscription_id,Subscription.user_id == current_user).first()

    if subscription is None:
        raise HTTPException(
            status_code=404,
            detail="Subscription not found"
        )

    return subscription

@app.put("/subscriptions/{subscription_id}")
def update_subscription(subscription_id : int , subscription : SubscriptionUpdate , db:Session = Depends(get_db)
    ,current_user:int = Depends(get_current_user)):
    existing_subscription = db.query(Subscription).filter(Subscription.id == subscription_id , Subscription.user_id == current_user).first()
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

@app.get("/dashboard") 
def get_dashboard(
    db: Session = Depends(get_db),
    currect_user: int = Depends(get_current_user)): 
    subscriptions = db.query(Subscription).filter(Subscription.user_id == currect_user).all()

    monthly_cost = 0
    yearly_cost = 0

    today = date.today()
    next_7days = today + timedelta(days=7)

    upcoming_renewals = []

    for subscription in subscriptions:
        if today <= subscription.renewal_date <= next_7days:
            upcoming_renewals.append({
                "name": subscription.name,
                "price": subscription.price,
                "renewal_date": subscription.renewal_date
            })

    highest_cost_subscription = None

    if subscriptions:
        highest_cost_subscription = max(
            subscriptions,
            key=lambda subscription: subscription.price
        )

    for subscription in subscriptions:
        if subscription.billing_cycle.lower() == "monthly":
            monthly_cost += subscription.price
            yearly_cost += subscription.price * 12

        elif subscription.billing_cycle.lower() == "yearly":
            monthly_cost += subscription.price / 12
            yearly_cost += subscription.price

    return {
        "total_subscriptions": len(subscriptions),
        "monthly_burn": monthly_cost,
        "yearly_burn": yearly_cost,
        "upcoming_renewals": upcoming_renewals,
        "highest_cost_subscription": {
            "name": highest_cost_subscription.name,
            "price": highest_cost_subscription.price
        } if highest_cost_subscription else None
    }

@app.delete("/subscriptions/{subscription_id}")
def delete_subscription(subscription_id : int , db:Session = Depends(get_db),current_user :int = Depends(get_current_user)):
    existing_subscription = db.query(Subscription).filter(Subscription.id == subscription_id,Subscription.user_id == current_user).first()
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

@app.on_event("startup")
def start_sechdualr():
    check_renewals()
    job_schedular.add_job(check_renewals,"interval",minutes=1, id = "renewal_checker",replace_existing=True)
    job_schedular.start()

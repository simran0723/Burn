from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base

DATABASE_URL = "postgresql://postgres:12345678@localhost:5432/Subscription_tracker"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


try:
    with engine.connect() as connection:
        print("DataBase connected succesfully")
except Exception as e:
    print("DataBase Connection failed :" ,e)
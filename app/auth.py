import os
from jose import jwt
from datetime import timedelta , datetime
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRETKEY")
ALGORITHM = "HS256"
def create_access_token(data : dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=5)
    to_encode.update({"exp" : expire})

    token = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)

    return token
# from passlib.context import CryptContext
# from jose import jwt, JWTError
# from datetime import datetime, timedelta

# # password hashing setup
# pwd_context = CryptContext(
#     schemes=["bcrypt"],
#     deprecated="auto"
# )

# # JWT secret key
# SECRET_KEY = "mysecretkey"

# # JWT algorithm
# ALGORITHM = "HS256"

# # token expiry time
# ACCESS_TOKEN_EXPIRE_HOURS = 2


# # hash password
# def hash_password(password: str):

#     return pwd_context.hash(password)


# # verify password
# def verify_password(
#     plain_password,
#     hashed_password
# ):

#     return pwd_context.verify(
#         plain_password,
#         hashed_password
#     )


# # create JWT token
# def create_access_token(data: dict):

#     payload = data.copy()

#     # token expiry
#     payload["exp"] = (
#         datetime.utcnow()
#         + timedelta(
#             hours=ACCESS_TOKEN_EXPIRE_HOURS
#         )
#     )

#     # generate token
#     token = jwt.encode(
#         payload,
#         SECRET_KEY,
#         algorithm=ALGORITHM
#     )

#     return token


# # verify JWT token
# def verify_token(token: str):

#     try:

#         payload = jwt.decode(
#             token,
#             SECRET_KEY,
#             algorithms=[ALGORITHM]
#         )

#         return payload

#     except JWTError:

#         return None



from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta

# password hashing setup
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# JWT secret key
SECRET_KEY = "mysecretkey"

# JWT algorithm
ALGORITHM = "HS256"

# access token expiry
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# refresh token expiry
REFRESH_TOKEN_EXPIRE_DAYS = 7


# hash password
def hash_password(password: str):

    return pwd_context.hash(password)


# verify password
def verify_password(
    plain_password,
    hashed_password
):

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# create access token
def create_access_token(data: dict):

    payload = data.copy()

    # access token expiry
    payload["exp"] = (
        datetime.utcnow()
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    # token type
    payload["type"] = "access"

    # generate token
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# create refresh token
def create_refresh_token(data: dict):

    payload = data.copy()

    # refresh token expiry
    payload["exp"] = (
        datetime.utcnow()
        + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )
    )

    # token type
    payload["type"] = "refresh"

    # generate token
    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


# verify JWT token
def verify_token(token: str):

    try:

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError:

        return None
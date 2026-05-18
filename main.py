from fastapi import FastAPI, Depends
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from models import SignupModel, LoginModel

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)

from salesforce_connection import sf

app = FastAPI()

# JWT security
security = HTTPBearer()


# Home API
@app.get("/")
def home():

    return {
        "message": "Backend Running Successfully"
    }


# Signup API using Salesforce Contact
@app.post("/signup")
def signup(user: SignupModel):

    try:

        # check existing contact
        query = f"""
        SELECT Id,
               Email
        FROM Contact
        WHERE Email = '{user.email}'
        LIMIT 1
        """

        result = sf.query(query)

        records = result["records"]

        # email already exists
        if len(records) > 0:

            return {
                "message": "Email already exists"
            }

        # hash password
        hashed_password = hash_password(
            user.password
        )

        # split full name
        name_parts = user.name.split(" ")

        first_name = name_parts[0]

        last_name = (
            name_parts[-1]
            if len(name_parts) > 1
            else first_name
        )

        # create Salesforce Contact
        sf.Contact.create({

            "FirstName": first_name,
            "LastName": last_name,
            "Email": user.email,
            "Password_Hash__c": hashed_password,
            "Role__c": "user",
            "Is_Active_User__c": True
        })

        return {

            "message": "Signup successful",

            "user": {
                "name": user.name,
                "email": user.email,
                "role": "user"
            }
        }

    except Exception as e:

        print(
            "Signup Error:",
            str(e)
        )

        return {

            "message": "Signup failed",
            "error": str(e)
        }


# Login API using Salesforce Contact
@app.post("/login")
def login(user: LoginModel):

    try:

        # Salesforce query
        query = f"""
        SELECT Id,
               Name,
               Email,
               Password_Hash__c,
               Role__c,
               Is_Active_User__c
        FROM Contact
        WHERE Email = '{user.email}'
        LIMIT 1
        """

        result = sf.query(query)

        records = result["records"]

        # user not found
        if len(records) == 0:

            return {
                "message": "User not found"
            }

        # get contact
        contact = records[0]

        print(contact)

        # check active user
        if contact.get("Is_Active_User__c") != True:

            return {
                "message": "User access disabled"
            }

        # verify password
        valid_password = verify_password(
            user.password,
            contact["Password_Hash__c"]
        )

        # invalid password
        if not valid_password:

            return {
                "message": "Invalid password"
            }

        # create access token
        access_token = create_access_token({

            "email": contact["Email"],
            "role": contact["Role__c"]
        })

        # create refresh token
        refresh_token = create_refresh_token({

            "email": contact["Email"],
            "role": contact["Role__c"]
        })

        # success response
        return {

            "message": "Login successful",

            "access_token": access_token,

            "refresh_token": refresh_token,

            "user": {

                "name": contact["Name"],
                "email": contact["Email"],
                "role": contact["Role__c"]
            }
        }

    except Exception as e:

        print(
            "Login Error:",
            str(e)
        )

        return {

            "message": "Login failed",
            "error": str(e)
        }


# Refresh Token API
@app.post("/refresh")
def refresh_token_api(refresh_token: str):

    try:

        # verify token
        payload = verify_token(refresh_token)

        # invalid token
        if not payload:

            return {
                "message": "Invalid refresh token"
            }

        # check token type
        if payload.get("type") != "refresh":

            return {
                "message": "Invalid token type"
            }

        # create new access token
        new_access_token = create_access_token({

            "email": payload["email"],
            "role": payload["role"]
        })

        return {

            "access_token": new_access_token
        }

    except Exception as e:

        print(
            "Refresh Token Error:",
            str(e)
        )

        return {

            "message": "Refresh token failed",
            "error": str(e)
        }


# Protected Dashboard API
@app.get("/dashboard")
def dashboard(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    try:

        # get token
        token = credentials.credentials

        # verify token
        payload = verify_token(token)

        # invalid token
        if not payload:

            return {
                "message": "Invalid or expired token"
            }

        # success response
        return {

            "message": "Welcome to dashboard",
            "user": payload
        }

    except Exception as e:

        print(
            "Dashboard Error:",
            str(e)
        )

        return {

            "message": "Dashboard access failed",
            "error": str(e)
        }
    # =====================================================
# AUTO START FASTAPI + OPEN SWAGGER UI
# =====================================================

if __name__ == "__main__":

    import uvicorn
    import webbrowser

    # automatically open Swagger UI
    webbrowser.open(
        "http://127.0.0.1:8000/docs"
    )

    # start FastAPI server
    uvicorn.run(

        "main:app",

        host="127.0.0.1",

        port=8000,

        reload=True
    )
# Attendance Backend Project

This is a FastAPI backend project integrated with Salesforce for user authentication and attendance management.

## Features

- User Signup
- User Login
- JWT Authentication
- Refresh Token API
- Salesforce Integration
- Password Hashing

---

# Project Files

## main.py

Main FastAPI application file.

Contains:
- API routes
- Login API
- Signup API
- Refresh token API

Example APIs:
- /login
- /signup
- /refresh

---

## auth.py

Handles authentication logic.

Contains:
- JWT token generation
- Token verification
- Password hashing
- Password validation

---

## models.py

Contains request and response models using Pydantic.

Used for:
- Input validation
- API request structure

Example:
- LoginModel
- SignupModel

---

## salesforce_connection.py

Used to connect FastAPI with Salesforce.

Handles:
- Salesforce authentication
- Salesforce queries
- Contact record operations

---

# Technologies Used

- FastAPI
- Python
- JWT
- Salesforce
- simple-salesforce
- Pydantic
- **Pydantic is a Python library used for:**

Data Validation and Data Modeling

It helps FastAPI:

validate incoming data
check data types
automatically reject wrong input
create request/response models
Why Pydantic is Needed

**Suppose user sends:**

{
  "email": "charan@gmail.com",
  "password": "1234"
}

**Backend must verify:**

email is string
password exists
required fields are present

---

# Authentication Flow

Signup
→ Store user in Salesforce

Login
→ Verify credentials
→ Generate access token
→ Generate refresh token

Refresh Token
→ Generate new access token

---

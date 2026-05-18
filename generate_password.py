from auth import hash_password

password = "abc123"

hashed_password = hash_password(password)

print(hashed_password)
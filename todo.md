road to v1.1
test script to see if it is work 
ui huge change
new funtion
ui.py ui only
github action
防禦性編程

problem:
def hash_password(password: str) -> str:
    return hashlib.sha256((password + Config.PASSWORD_SALT).encode()).hexdigest()
 is used in a hashing algorithm (SHA256) that is insecure for password hashing, since it is not a computationally expensive hash function.
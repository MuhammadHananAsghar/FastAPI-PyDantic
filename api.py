from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
import sqlite3
import cachetools

app = FastAPI()

# Database connection
conn = sqlite3.connect("posts.db")
cursor = conn.cursor()

# Cache for storing posts
cache = cachetools.TTLCache(maxsize=100, ttl=300)

# OAuth2PasswordBearer for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Models
class User(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class Post(BaseModel):
    text: str

# Create users table
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    password TEXT NOT NULL
                )''')

# Create posts table
cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )''')

# Helper function to create a new user
def create_user(user: User):
    cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (user.email, user.password))
    conn.commit()
    return cursor.lastrowid

# Helper function to get a user by email
def get_user_by_email(email: str):
    cursor.execute("SELECT id, email, password FROM users WHERE email = ?", (email,))
    return cursor.fetchone()

# Helper function to create a new post
def create_post(user_id: int, post: Post):
    cursor.execute("INSERT INTO posts (user_id, text) VALUES (?, ?)", (user_id, post.text))
    conn.commit()
    return cursor.lastrowid

# Helper function to get user's posts from the database
def get_user_posts(user_id: int):
    cursor.execute("SELECT id, text FROM posts WHERE user_id = ?", (user_id,))
    return cursor.fetchall()

# Helper function to delete a post by ID
def delete_post(post_id: int):
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()

# Token authentication function
def authenticate_user(token: str = Depends(oauth2_scheme)):
    # Here, you can implement token validation logic (e.g., JWT validation)
    # For simplicity, we'll just check if the token is in the cache
    if token not in cache:
        raise HTTPException(status_code=401, detail="Token is invalid")
    return token

# Signup endpoint
@app.post("/signup", response_model=Token)
async def signup(user: User):
    user_id = create_user(user)
    token = user.email  # For simplicity, use the email as the token
    cache[token] = user_id
    return {"access_token": token, "token_type": "bearer"}

# Login endpoint
@app.post("/login", response_model=Token)
async def login(user: User):
    db_user = get_user_by_email(user.email)
    if db_user is None or db_user[2] != user.password:
        raise HTTPException(status_code=401, detail="Login failed")
    token = user.email  # For simplicity, use the email as the token
    cache[token] = db_user[0]
    return {"access_token": token, "token_type": "bearer"}

# AddPost endpoint with token authentication and request validation
@app.post("/addPost", response_model=str)
async def add_post(post: Post, token: str = Depends(authenticate_user)):
    # Validate payload size (limit to 1MB)
    if len(post.text) > 1_000_000:
        raise HTTPException(status_code=413, detail="Payload size exceeds 1MB")
    user_id = cache[token]
    post_id = create_post(user_id, post)
    return str(post_id)

# GetPosts endpoint with token authentication and response caching
@app.get("/getPosts", response_model=list)
async def get_posts(token: str = Depends(authenticate_user)):
    user_id = cache[token]
    if user_id in cache:
        return cache[user_id]
    else:
        posts = get_user_posts(user_id)
        cache[user_id] = posts
        return posts

# DeletePost endpoint with token authentication
@app.delete("/deletePost", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: int, token: str = Depends(authenticate_user)):
    user_id = cache[token]
    # Check if the post belongs to the user
    cursor.execute("SELECT id FROM posts WHERE id = ? AND user_id = ?", (post_id, user_id))
    result = cursor.fetchone()
    if result:
        delete_post(post_id)
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port="5000")

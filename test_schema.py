from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# SQLAlchemy models
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)

    # Establish a one-to-many relationship between User and Post
    posts = relationship('Post', back_populates='user')


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    # Establish a many-to-one relationship between Post and User
    user = relationship('User', back_populates='posts')
    created_at = Column(func.now())

# Create a SQLite database and session
DATABASE_URL = "......db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in the database
Base.metadata.create_all(bind=engine)

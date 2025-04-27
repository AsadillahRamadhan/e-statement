import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SQLALCHEMY_DATABASE_URI = f'{os.getenv("DB_ENGINE")}+pymysql://{os.getenv("DB_USERNAME")}:{os.getenv("DB_PASSWORD")}@{os.getenv("DB_URL")}:{os.getenv("DB_PORT")}/{os.getenv("DB_DATABASE")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:@localhost:3306/e_statement'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
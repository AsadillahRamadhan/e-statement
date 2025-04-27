import sys
import os
from dotenv import load_dotenv

load_dotenv()


sys.path.insert(0, os.path.dirname(__file__))
from app import app as application 

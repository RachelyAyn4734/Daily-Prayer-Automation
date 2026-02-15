# settings.py
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

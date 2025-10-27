from pymongo import MongoClient
import dotenv
import os

dotenv.load_dotenv()

MLX_BASE = "https://api.multilogin.com"
MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v1"
MLX_LAUNCHER_V2 = ("https://launcher.mlx.yt:45001/api/v2")
MLX_LAUNCHER_V3 = "https://launcher.mlx.yt:45001/api/v3"

LOCALHOST = "http://127.0.0.1"
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}
USERNAME = os.getenv("MLX_USERNAME")
PASSWORD = os.getenv("MLX_PASSWORD") 
FOLDER_ID = os.getenv("FOLDER_ID")
WORKSPACE_ID = os.getenv("WORKSPACE_ID")

# AWS S3 Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "mega.iart.group")
AWS_FOLDER_NAME = os.getenv("AWS_FOLDER_NAME", "images")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# MongoDB connection with authentication
# Nếu chạy trong Docker: mongodb://wm-mega-mongodb:27017/walmart
# Nếu chạy ngoài Docker: mongodb://localhost:27017/walmart hoặc IP của server
import os
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/walmart")
client = MongoClient(MONGO_URI)
db = client["walmart"]
collection_log = db["logs"]

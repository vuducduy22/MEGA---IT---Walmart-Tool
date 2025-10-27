from pymongo import MongoClient
import dotenv
import os

dotenv.load_dotenv()

MLX_BASE = "https://api.multilogin.com"
# MLX_LAUNCHER = "https://launcher.mlx.yt:45001/api/v1"
# MLX_LAUNCHER_V2 = ("https://launcher.mlx.yt:45001/api/v2")
# MLX_LAUNCHER_V3 = "https://launcher.mlx.yt:45001/api/v3"

# Sử dụng HTTP localhost - ĐƠN GIẢN NHẤT, hoạt động cho cả local và server
# Vì MLX Launcher chạy bên trong container, localhost là đúng
MLX_LAUNCHER = "http://127.0.0.1:45001/api/v1"
MLX_LAUNCHER_V2 = "http://127.0.0.1:45001/api/v2"
MLX_LAUNCHER_V3 = "http://127.0.0.1:45001/api/v3"

# Fallback URLs (không cần thiết lắm nhưng để phòng xa)
MLX_LAUNCHER_FALLBACK = "http://127.0.0.1:45001/api/v1"
MLX_LAUNCHER_V2_FALLBACK = "http://127.0.0.1:45001/api/v2"
MLX_LAUNCHER_V3_FALLBACK = "http://127.0.0.1:45001/api/v3"

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
MONGO_URI = os.getenv("MONGO_URI", "mongodb://192.168.9.179:27017/walmart")
client = MongoClient(MONGO_URI)
db = client["walmart"]
collection_log = db["logs"]

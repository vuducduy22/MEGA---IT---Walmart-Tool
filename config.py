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

client = MongoClient(os.getenv("MONGO_URI"))
db = client["walmart"]
collection_log = db["logs"]

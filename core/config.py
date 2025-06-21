from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import httpx

config = Config(".env")

# --- App Settings ---
SESSION_SECRET_KEY = config("SESSION_SECRET_KEY", cast=str)
# Add other app-level settings here

# --- OAuth Settings ---
# Google
GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID", cast=str, default=None)
GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET", cast=str, default=None)

# WeChat
WECHAT_CLIENT_ID = config("WECHAT_CLIENT_ID", cast=str, default=None)
WECHAT_CLIENT_SECRET = config("WECHAT_CLIENT_SECRET", cast=str, default=None)

# --- Redis Settings ---
REDIS_HOST = config("REDIS_HOST", cast=str, default="localhost")
REDIS_PORT = config("REDIS_PORT", cast=int, default=6379)
REDIS_PASSWORD = config("REDIS_PASSWORD", cast=str, default=None)
REDIS_DB = config("REDIS_DB", cast=int, default=0)
SESSION_EXPIRE_MINUTES = config("SESSION_EXPIRE_MINUTES", cast=int, default=60 * 24 * 7) # 7 days

# --- Authlib OAuth Registry ---
oauth = OAuth(config)

# Define a longer timeout for connections
timeout = httpx.Timeout(10.0, connect=30.0)

# Google Provider
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={
            "scope": "openid email profile",
            "timeout": timeout,
        },
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
    )

# WeChat Provider (for QR code login on desktop)
if WECHAT_CLIENT_ID and WECHAT_CLIENT_SECRET:
    oauth.register(
        name="wechat",
        client_id=WECHAT_CLIENT_ID,
        client_secret=WECHAT_CLIENT_SECRET,
        access_token_url="https://api.weixin.qq.com/sns/oauth2/access_token",
        authorize_url="https://open.weixin.qq.com/connect/qrconnect",
        api_base_url="https://api.weixin.qq.com/sns/",
        client_kwargs={"scope": "snsapi_login"},
    )

import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///inventory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'namansingh291104@gmail.com'      # ← your Gmail
    MAIL_PASSWORD = 'durixrvhnhxrlgvy'        # ← your app password
    MAIL_DEFAULT_SENDER = 'namansingh291104@gmail.com' # ← same Gmail
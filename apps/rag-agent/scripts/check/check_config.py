"""Check config values on remote"""
from app.config import settings
print("mysql_password:", repr(settings.mysql_password))
print("mysql_host:", repr(settings.mysql_host))
print("mysql_port:", repr(settings.mysql_port))
print("env_file:", settings.model_config.get("env_file"))

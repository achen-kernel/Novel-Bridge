"""Check config values"""
import sys
sys.path.insert(0, "/home/wk/novelbridge/apps/rag-agent")
from app.config import settings
print("mysql_password:", repr(settings.mysql_password))
print("mysql_host:", repr(settings.mysql_host))
print("mysql_port:", repr(settings.mysql_port))

"""Test env file loading"""
import sys, os
sys.path.insert(0, '/home/wk/novelbridge/apps/rag-agent')

# Check if env file exists where pydantic looks
cwd = os.getcwd()
env_path = os.path.join(cwd, '.env')
print("CWD:", cwd)
print(".env path:", env_path)
print(".env exists:", os.path.isfile(env_path))
print(".env islink:", os.path.islink(env_path))
if os.path.isfile(env_path):
    with open(env_path) as f:
        content = f.read()
        print(".env contains mysql_password:", 'MYSQL_PASSWORD' in content)

# Now test WITHOUT forced env var (re-import in fresh process would need)
from app.config import settings
print("mysql_password (from .env):", repr(settings.mysql_password))

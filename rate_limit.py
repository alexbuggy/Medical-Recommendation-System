"""Shared slowapi limiter. Imported by app.py and the route modules."""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

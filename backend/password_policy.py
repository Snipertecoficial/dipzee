"""Single authoritative password policy shared by auth and administration."""
import re

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$", re.DOTALL)


def validate_password_strength(value: str) -> str:
    if len(value or "") > 128 or not _PASSWORD_RE.match(value or ""):
        raise ValueError("Password must be 8-128 characters and include a letter and a number.")
    return value

"""Password hashing and verification utilities."""

from pwdlib import PasswordHash

# Argon2 (modern, GPU-resistant)
password_hash = PasswordHash.recommended()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password."""
    return password_hash.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash password using Argon2."""
    return password_hash.hash(password)

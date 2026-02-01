#!/usr/bin/env python3
"""
Generate Encryption Key

Simple script to generate a new encryption key for database encryption.
The generated key should be stored securely in the DB_ENCRYPTION_KEY environment variable.

Usage:
    python generate_encryption_key.py
"""

from encryption_utils import generate_key

if __name__ == "__main__":
    key = generate_key()
    print("=" * 80)
    print("DATABASE ENCRYPTION KEY")
    print("=" * 80)
    print()
    print("Generated encryption key:")
    print()
    print(key)
    print()
    print("=" * 80)
    print("IMPORTANT: Store this key securely!")
    print("=" * 80)
    print()
    print("Add this key to your .env file:")
    print(f"DB_ENCRYPTION_KEY={key}")
    print()
    print("WARNING:")
    print("- Keep this key SECRET and SECURE")
    print("- DO NOT commit this key to version control")
    print("- If you lose this key, encrypted data CANNOT be recovered")
    print("- Rotating keys requires decrypting all data with the old key")
    print("=" * 80)

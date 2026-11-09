"""Administrative CLI tools for FarmShield AI.

Usage:
    python -m app.cli create-admin --email admin@farmshield.ai --name "Admin Name" --password "StrongPass123!"
"""

import argparse
import sys
import uuid
from sqlalchemy.orm import Session
from app.core.logging import logger
from app.core.security import hash_password, validate_password_complexity
from app.db.session import SessionLocal
from app.models.user import User


def create_admin_user(
    email: str,
    name: str,
    password: str,
    phone: str = None,
) -> None:
    """Provision a new administrative user with Argon2id hashed password."""
    # 1. Validate password
    validate_password_complexity(password)

    db: Session = SessionLocal()
    try:
        normalized_email = email.strip().lower()
        existing = db.query(User).filter(User.email == normalized_email).first()
        if existing:
            if existing.role == "admin":
                print(f"[!] User '{normalized_email}' is already an administrator (ID: {existing.id}).")
                return
            existing.role = "admin"
            existing.is_active = True
            existing.hashed_password = hash_password(password)
            db.commit()
            print(f"[+] Existing user '{normalized_email}' successfully upgraded to 'admin' (ID: {existing.id}).")
            return

        new_admin = User(
            id=uuid.uuid4(),
            full_name=name.strip(),
            email=normalized_email,
            phone=phone.strip() if phone else None,
            hashed_password=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(new_admin)
        db.commit()
        db.refresh(new_admin)
        print(f"[+] Administrator user successfully created!")
        print(f"    ID:    {new_admin.id}")
        print(f"    Email: {new_admin.email}")
        print(f"    Role:  {new_admin.role}")
    finally:
        db.close()


def main() -> None:
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="FarmShield AI Administrative Management CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    admin_parser = subparsers.add_parser("create-admin", help="Provision a new administrator user")
    admin_parser.add_argument("--email", required=True, help="Administrator email address")
    admin_parser.add_argument("--name", required=True, help="Full name of administrator")
    admin_parser.add_argument("--password", required=True, help="Strong password for administrator")
    admin_parser.add_argument("--phone", required=False, default=None, help="Optional contact phone")

    args = parser.parse_args()

    if args.command == "create-admin":
        try:
            create_admin_user(
                email=args.email,
                name=args.name,
                password=args.password,
                phone=args.phone,
            )
        except Exception as exc:
            print(f"[-] Error: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

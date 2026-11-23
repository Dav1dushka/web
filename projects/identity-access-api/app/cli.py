import argparse
from sqlalchemy import select
from .database import SessionLocal
from .models import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Identity Access API administration tools.")
    commands = parser.add_subparsers(dest="command", required=True)
    promote = commands.add_parser("promote-admin", help="Promote an existing user to administrator.")
    promote.add_argument("email")
    args = parser.parse_args()
    if args.command == "promote-admin":
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == args.email.strip().lower()))
            if user is None:
                parser.error("No user with that email exists. Register the user first.")
            user.role = "admin"
            db.commit()
            print(f"{user.email} is now an administrator.")


if __name__ == "__main__":
    main()

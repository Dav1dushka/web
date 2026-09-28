import argparse
import base64
import json
import os
from getpass import getpass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


VAULT_FILE = "vault.json"
SALT_SIZE = 16


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = Scrypt(
        salt=salt,
        length=32,
        n=2**14,
        r=8,
        p=1,
    )

    key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key)


def load_vault(password: str):
    if not os.path.exists(VAULT_FILE):
        raise FileNotFoundError("Vault is not initialized")

    with open(VAULT_FILE, "r", encoding="utf-8") as file:
        stored = json.load(file)

    salt = base64.b64decode(stored["salt"])
    key = derive_key(password, salt)

    try:
        data = Fernet(key).decrypt(stored["data"].encode())
    except InvalidToken:
        raise ValueError("Wrong master password")

    return json.loads(data)


def save_vault(password: str, records):
    if os.path.exists(VAULT_FILE):
        with open(VAULT_FILE, "r", encoding="utf-8") as file:
            stored = json.load(file)
        salt = base64.b64decode(stored["salt"])
    else:
        salt = os.urandom(SALT_SIZE)

    key = derive_key(password, salt)
    encrypted = Fernet(key).encrypt(
        json.dumps(records).encode()
    ).decode()

    with open(VAULT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            {
                "salt": base64.b64encode(salt).decode(),
                "data": encrypted,
            },
            file,
            indent=2,
        )


def command_init():
    if os.path.exists(VAULT_FILE):
        print("Vault already exists.")
        return

    password = getpass("Create master password: ")
    confirm = getpass("Repeat master password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    save_vault(password, [])
    print("Vault created.")


def command_add(name: str, username: str):
    password = getpass("Master password: ")
    records = load_vault(password)

    secret = getpass("Password to store: ")

    records = [record for record in records if record["name"] != name]
    records.append(
        {
            "name": name,
            "username": username,
            "password": secret,
        }
    )

    save_vault(password, records)
    print("Saved.")


def command_list():
    password = getpass("Master password: ")
    records = load_vault(password)

    if not records:
        print("Vault is empty.")
        return

    for record in records:
        print(f'- {record["name"]} ({record["username"]})')


def command_get(name: str):
    password = getpass("Master password: ")
    records = load_vault(password)

    for record in records:
        if record["name"] == name:
            print(f'Site: {record["name"]}')
            print(f'Username: {record["username"]}')
            print(f'Password: {record["password"]}')
            return

    print("Entry not found.")


def command_delete(name: str):
    password = getpass("Master password: ")
    records = load_vault(password)

    updated = [record for record in records if record["name"] != name]

    if len(updated) == len(records):
        print("Entry not found.")
        return

    save_vault(password, updated)
    print("Deleted.")


def main():
    parser = argparse.ArgumentParser(description="Small encrypted password vault")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")
    subparsers.add_parser("list")

    add_parser = subparsers.add_parser("add")
    add_parser.add_argument("name")
    add_parser.add_argument("username")

    get_parser = subparsers.add_parser("get")
    get_parser.add_argument("name")

    delete_parser = subparsers.add_parser("delete")
    delete_parser.add_argument("name")

    args = parser.parse_args()

    try:
        if args.command == "init":
            command_init()
        elif args.command == "list":
            command_list()
        elif args.command == "add":
            command_add(args.name, args.username)
        elif args.command == "get":
            command_get(args.name)
        elif args.command == "delete":
            command_delete(args.name)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)


if __name__ == "__main__":
    main()

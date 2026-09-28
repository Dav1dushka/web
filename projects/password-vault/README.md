# Password Vault

A small local password manager I made to learn more about encryption and secure storage.

It keeps the vault data encrypted and uses a master password to unlock it.

### Commands

```bash
python vault.py init
python vault.py add github myusername
python vault.py list
python vault.py get github
python vault.py delete github
```

### Built with

Python and the cryptography package.

The vault file is ignored by git on purpose.

This is a learning project, not something I would use as a real password manager for important accounts.

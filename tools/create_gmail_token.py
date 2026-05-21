from __future__ import annotations

import os
import sys

from env_utils import load_env
from send_gmail import build_service


def main() -> int:
    load_env()
    credentials_file = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.environ.get("GMAIL_TOKEN_FILE", "token.json")

    try:
        build_service(credentials_file, token_file)
        print(token_file)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

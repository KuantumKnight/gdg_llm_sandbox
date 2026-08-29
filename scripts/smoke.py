"""CLI wrapper for the packaged deployment smoke probe."""

from app.smoke import main

if __name__ == "__main__":
    raise SystemExit(main())

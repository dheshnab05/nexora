
import hashlib
from pathlib import Path


def calculate_sha256(file_path: str) -> str:
    """Calculate the SHA-256 hash of a file without changing it."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def verify_file_integrity(file_path: str, original_hash: str) -> dict:
    """Compare the current file hash with its recorded original hash."""
    path = Path(file_path)

    if not path.is_file():
        return {
            "filename": path.name,
            "integrity_status": "file_not_found",
            "verified": False,
        }

    current_hash = calculate_sha256(str(path))
    matches = current_hash == original_hash

    return {
        "filename": path.name,
        "original_sha256": original_hash,
        "current_sha256": current_hash,
        "integrity_status": "unchanged" if matches else "modified",
        "verified": matches,
    }

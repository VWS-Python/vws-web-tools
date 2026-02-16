"""VWS credentials type."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VWSCredentials:
    """Vuforia Web Services credentials."""

    email_address: str
    password: str

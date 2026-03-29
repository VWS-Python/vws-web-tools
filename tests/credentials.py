"""VWS credentials type."""

from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class VWSCredentials:
    """Vuforia Web Services credentials."""

    email_address: str
    password: str

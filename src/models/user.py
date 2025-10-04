"""User domain model for multi-tenant support."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """
    Represents a user in the system (for multi-tenant support).

    Attributes:
        id: Unique identifier for the user
        created_at: Timestamp when user was created
    """

    id: str
    created_at: datetime

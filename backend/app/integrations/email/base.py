from dataclasses import dataclass
from typing import Protocol


class EmailDeliveryError(RuntimeError):
    """Raised when a transactional message cannot be delivered to the SMTP relay."""


@dataclass(frozen=True)
class OutboundEmail:
    recipient: str
    subject: str
    text_body: str
    html_body: str


class EmailProvider(Protocol):
    def send(self, message: OutboundEmail) -> None: ...

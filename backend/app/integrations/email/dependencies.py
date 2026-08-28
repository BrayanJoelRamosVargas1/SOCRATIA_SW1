from functools import lru_cache

from app.core.config import get_settings
from app.integrations.email.base import EmailProvider
from app.integrations.email.smtp import SmtpEmailProvider


@lru_cache
def get_email_provider() -> EmailProvider:
    return SmtpEmailProvider(get_settings())

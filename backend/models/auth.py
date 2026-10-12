from typing import Literal

from pydantic import Field

from backend.models.core import CanonicalModel


class EmailCodeRequest(CanonicalModel):
    email: str = Field(min_length=3, max_length=254)
    purpose: Literal['login', 'register']


class EmailSignInRequest(CanonicalModel):
    email: str = Field(min_length=3, max_length=254)
    code: str = Field(pattern=r'^[0-9]{6}$')


class AuthUser(CanonicalModel):
    id: str
    email: str


class AuthSession(CanonicalModel):
    enabled: bool
    authenticated: bool
    user: AuthUser | None = None
    csrf_token: str = ''
    mail_configured: bool = False


class AuthSessionResponse(CanonicalModel):
    request_id: str
    data: AuthSession


class EmailChallenge(CanonicalModel):
    delivery_status: Literal['SMTP_ACCEPTED'] = 'SMTP_ACCEPTED'
    expires_in: int
    retry_after: int


class EmailChallengeResponse(CanonicalModel):
    request_id: str
    data: EmailChallenge

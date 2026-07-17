from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from kyverance.auth.deps import require_authenticated
from kyverance.auth.models import AuthenticatedSubject

router = APIRouter(tags=["me"])


class MeOut(BaseModel):
    subject: str
    user_id: str | None = None
    display_name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    idp: str | None = None
    roles: list[str] = Field(default_factory=list)
    is_dev: bool = False
    is_administrator: bool = False


@router.get("/me", response_model=MeOut)
def get_me(
    subject: Annotated[AuthenticatedSubject, Depends(require_authenticated)],
) -> MeOut:
    return MeOut(
        subject=subject.subject,
        user_id=subject.user_id,
        display_name=subject.display_name or subject.name,
        given_name=subject.given_name,
        family_name=subject.family_name,
        idp=subject.idp,
        roles=sorted(subject.roles),
        is_dev=subject.is_dev,
        is_administrator=subject.is_administrator,
    )

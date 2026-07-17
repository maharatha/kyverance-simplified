from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from kyverance.audit.service import record_audit_event
from kyverance.auth.models import AuthenticatedSubject
from kyverance.config import Settings, get_settings
from kyverance.connectors.constants import (
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_DISCONNECTED,
    CONNECTION_STATUS_PENDING_DELETION,
    CONSENT_PLAID_CONNECT,
    CONSENT_PLAID_DATA_RETENTION,
    PROVIDER_MODE_FAKE,
    PROVENANCE_PLAID_READ_ONLY,
    SOURCE_LABEL_PLAID,
)
from kyverance.connectors.factory import get_plaid_provider
from kyverance.connectors.models import PlaidAccount, PlaidConnection, PlaidDeletionRequest, PlaidHolding
from kyverance.connectors.provider_base import PlaidProvider, RemoteAccount, RemoteHolding
from kyverance.connectors.schemas import (
    ConnectorsOverviewOut,
    DeletionRequestOut,
    PlaidAccountOut,
    PlaidConnectionOut,
    PlaidHoldingOut,
    PlaidLinkTokenOut,
)
from kyverance.connectors.token_crypto import decrypt_access_token, encrypt_access_token
from kyverance.identity.models import ConsentRecord, User
from kyverance.identity.service import record_consent


def _now() -> datetime:
    return datetime.now(UTC)


def _user_uuid(subject: AuthenticatedSubject) -> uuid.UUID:
    if not subject.user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return uuid.UUID(subject.user_id)


def _load_user(db: Session, subject: AuthenticatedSubject) -> User:
    user_id = _user_uuid(subject)
    user = db.query(User).filter(User.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def _owned_connection(db: Session, subject: AuthenticatedSubject, connection_id: uuid.UUID) -> PlaidConnection:
    user_id = _user_uuid(subject)
    conn = (
        db.query(PlaidConnection)
        .filter(PlaidConnection.id == connection_id, PlaidConnection.user_id == user_id)
        .one_or_none()
    )
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return conn


def _consent_granted(db: Session, user_id: uuid.UUID, consent_type: str) -> bool:
    record = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user_id, ConsentRecord.consent_type == consent_type)
        .one_or_none()
    )
    return bool(record and record.granted)


def _require_connect_consent(db: Session, user_id: uuid.UUID) -> None:
    if not _consent_granted(db, user_id, CONSENT_PLAID_CONNECT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plaid connect consent is required",
        )


def _empty_state(
    *,
    connections: list[PlaidConnection],
    connect_consent: bool,
    plaid_configured: bool,
    mode: str,
) -> str:
    if connections:
        return "populated"
    if not connect_consent:
        return "consent_required"
    if mode == PROVIDER_MODE_FAKE:
        return "ready_fake"
    if not plaid_configured:
        return "configuration_required"
    return "ready"


def _holding_out(holding: PlaidHolding) -> PlaidHoldingOut:
    return PlaidHoldingOut(
        id=str(holding.id),
        symbol=holding.symbol,
        name=holding.name,
        quantity=holding.quantity,
        currency=holding.currency,
        provenance=holding.provenance,
        source_label=holding.source_label,
    )


def _account_out(account: PlaidAccount) -> PlaidAccountOut:
    return PlaidAccountOut(
        id=str(account.id),
        connection_id=str(account.connection_id),
        name=account.name,
        mask=account.mask,
        account_type=account.account_type,
        currency=account.currency,
        provenance=account.provenance,
        source_label=account.source_label,
        last_synced_at=account.last_synced_at,
        holdings=[_holding_out(h) for h in account.holdings],
    )


def _connection_out(conn: PlaidConnection) -> PlaidConnectionOut:
    return PlaidConnectionOut(
        id=str(conn.id),
        provider_key=conn.provider_key,
        institution_name=conn.institution_name,
        status=conn.status,
        last_synced_at=conn.last_synced_at,
        consent_recorded_at=conn.consent_recorded_at,
        disconnected_at=conn.disconnected_at,
        deletion_requested_at=conn.deletion_requested_at,
        accounts=[_account_out(a) for a in conn.accounts],
    )


def get_overview(
    db: Session,
    subject: AuthenticatedSubject,
    settings: Settings | None = None,
) -> ConnectorsOverviewOut:
    resolved = settings or get_settings()
    provider = get_plaid_provider(resolved)
    user_id = _user_uuid(subject)
    connections = (
        db.query(PlaidConnection)
        .filter(PlaidConnection.user_id == user_id)
        .order_by(PlaidConnection.created_at.desc())
        .all()
    )
    connect_consent = _consent_granted(db, user_id, CONSENT_PLAID_CONNECT)
    retention_consent = _consent_granted(db, user_id, CONSENT_PLAID_DATA_RETENTION)
    empty = _empty_state(
        connections=connections,
        connect_consent=connect_consent,
        plaid_configured=resolved.plaid_configured,
        mode=provider.mode,
    )
    message = None
    if empty == "configuration_required":
        message = "Plaid credentials are not configured. Local fake provider is unavailable in this environment."
    elif empty == "ready_fake":
        message = "Local fake provider is active. No real banking credentials are used."
    elif empty == "consent_required":
        message = "Grant read-only connection consent before linking an account."
    elif empty == "ready":
        message = "Ready to create a Plaid Link token."

    return ConnectorsOverviewOut(
        configured=resolved.plaid_configured or provider.mode == PROVIDER_MODE_FAKE,
        plaid_configured=resolved.plaid_configured,
        mode=provider.mode,
        connect_consent_granted=connect_consent,
        data_retention_consent_granted=retention_consent,
        empty_state=empty,
        connections=[_connection_out(c) for c in connections],
        message=message,
    )


def set_plaid_consent(
    db: Session,
    subject: AuthenticatedSubject,
    *,
    granted: bool,
) -> ConnectorsOverviewOut:
    user = _load_user(db, subject)
    record_consent(
        db,
        user=user,
        consent_type=CONSENT_PLAID_CONNECT,
        granted=granted,
        actor_subject=subject.subject,
        metadata={"scope": "read_only", "funding": False, "simulation_link": False},
    )
    if granted:
        # Fresh session after commit inside record_consent.
        user = _load_user(db, subject)
        record_consent(
            db,
            user=user,
            consent_type=CONSENT_PLAID_DATA_RETENTION,
            granted=True,
            actor_subject=subject.subject,
            metadata={"scope": "connection_data"},
        )
    return get_overview(db, subject)


def create_link_token(
    db: Session,
    subject: AuthenticatedSubject,
    settings: Settings | None = None,
) -> PlaidLinkTokenOut:
    resolved = settings or get_settings()
    user_id = _user_uuid(subject)
    _require_connect_consent(db, user_id)
    provider = get_plaid_provider(resolved)
    token = provider.create_link_token(client_user_id=subject.subject)
    record_audit_event(
        db,
        actor_subject=subject.subject,
        action="plaid.link_token.create",
        resource_type="plaid_link",
        resource_id=subject.subject,
        metadata={"mode": provider.mode},
    )
    db.commit()
    return PlaidLinkTokenOut(
        link_token=token,
        mode=provider.mode,
        expiration_hint="short-lived" if provider.mode != PROVIDER_MODE_FAKE else "local-fake",
    )


def _upsert_accounts(
    db: Session,
    *,
    conn: PlaidConnection,
    user_id: uuid.UUID,
    accounts: list[RemoteAccount],
    synced_at: datetime,
) -> dict[str, PlaidAccount]:
    by_external: dict[str, PlaidAccount] = {}
    for remote in accounts:
        existing = (
            db.query(PlaidAccount)
            .filter(
                PlaidAccount.connection_id == conn.id,
                PlaidAccount.external_account_id == remote.external_account_id,
            )
            .one_or_none()
        )
        if existing is None:
            existing = PlaidAccount(
                connection_id=conn.id,
                user_id=user_id,
                external_account_id=remote.external_account_id,
                name=remote.name,
                mask=remote.mask,
                account_type=remote.account_type,
                currency=remote.currency,
                provenance=PROVENANCE_PLAID_READ_ONLY,
                source_label=SOURCE_LABEL_PLAID,
                last_synced_at=synced_at,
            )
            db.add(existing)
            db.flush()
        else:
            existing.name = remote.name
            existing.mask = remote.mask
            existing.account_type = remote.account_type
            existing.currency = remote.currency
            existing.last_synced_at = synced_at
        by_external[remote.external_account_id] = existing
    return by_external


def _upsert_holdings(
    db: Session,
    *,
    user_id: uuid.UUID,
    accounts_by_external: dict[str, PlaidAccount],
    holdings: list[RemoteHolding],
    synced_at: datetime,
) -> None:
    for remote in holdings:
        account = accounts_by_external.get(remote.external_account_id)
        if account is None:
            continue
        existing = (
            db.query(PlaidHolding)
            .filter(
                PlaidHolding.account_id == account.id,
                PlaidHolding.external_security_id == remote.external_security_id,
            )
            .one_or_none()
        )
        if existing is None:
            db.add(
                PlaidHolding(
                    account_id=account.id,
                    user_id=user_id,
                    external_security_id=remote.external_security_id,
                    symbol=remote.symbol,
                    name=remote.name,
                    quantity=remote.quantity if isinstance(remote.quantity, Decimal) else Decimal(str(remote.quantity)),
                    currency=remote.currency,
                    provenance=PROVENANCE_PLAID_READ_ONLY,
                    source_label=SOURCE_LABEL_PLAID,
                    last_synced_at=synced_at,
                )
            )
        else:
            existing.symbol = remote.symbol
            existing.name = remote.name
            existing.quantity = remote.quantity
            existing.currency = remote.currency
            existing.last_synced_at = synced_at


def _access_token_for(conn: PlaidConnection, settings: Settings) -> str | None:
    if conn.access_token_ciphertext:
        return decrypt_access_token(conn.access_token_ciphertext, settings)
    # token_vault_ref is reserved for a later Key Vault task — not resolvable here.
    return None


def exchange_public_token(
    db: Session,
    subject: AuthenticatedSubject,
    *,
    public_token: str,
    provider_key: str = "any",
    settings: Settings | None = None,
) -> ConnectorsOverviewOut:
    resolved = settings or get_settings()
    user_id = _user_uuid(subject)
    _require_connect_consent(db, user_id)
    provider = get_plaid_provider(resolved)

    exchanged = provider.exchange_public_token(public_token.strip())
    ciphertext, kid = encrypt_access_token(exchanged.access_token, resolved)
    synced_at = _now()
    institution_name = provider.get_institution_name(exchanged.access_token)
    accounts = provider.get_accounts(exchanged.access_token)
    holdings = provider.get_holdings(exchanged.access_token)

    conn = (
        db.query(PlaidConnection)
        .filter(PlaidConnection.user_id == user_id, PlaidConnection.item_id == exchanged.item_id)
        .one_or_none()
    )
    if conn is None:
        conn = PlaidConnection(
            user_id=user_id,
            item_id=exchanged.item_id,
            access_token_ciphertext=ciphertext,
            token_vault_ref=None,
            encryption_kid=kid,
            provider_key=(provider_key or "any")[:64],
            institution_name=institution_name,
            status=CONNECTION_STATUS_CONNECTED,
            consent_recorded_at=synced_at,
            last_synced_at=synced_at,
        )
        db.add(conn)
        db.flush()
        action = "plaid.connection.create"
    else:
        conn.access_token_ciphertext = ciphertext
        conn.encryption_kid = kid
        conn.token_vault_ref = None
        conn.provider_key = (provider_key or conn.provider_key or "any")[:64]
        conn.institution_name = institution_name or conn.institution_name
        conn.status = CONNECTION_STATUS_CONNECTED
        conn.consent_recorded_at = conn.consent_recorded_at or synced_at
        conn.last_synced_at = synced_at
        conn.disconnected_at = None
        conn.deletion_requested_at = None
        action = "plaid.connection.reconnect"

    accounts_by_external = _upsert_accounts(
        db, conn=conn, user_id=user_id, accounts=accounts, synced_at=synced_at
    )
    _upsert_holdings(
        db,
        user_id=user_id,
        accounts_by_external=accounts_by_external,
        holdings=holdings,
        synced_at=synced_at,
    )

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action=action,
        resource_type="plaid_connection",
        resource_id=str(conn.id),
        metadata={
            "mode": provider.mode,
            "provider_key": conn.provider_key,
            "account_count": len(accounts),
            "holding_count": len(holdings),
            "item_id_suffix": exchanged.item_id[-8:],
        },
    )
    db.commit()
    return get_overview(db, subject, resolved)


def refresh_connection(
    db: Session,
    subject: AuthenticatedSubject,
    connection_id: uuid.UUID,
    settings: Settings | None = None,
) -> ConnectorsOverviewOut:
    resolved = settings or get_settings()
    conn = _owned_connection(db, subject, connection_id)
    if conn.status != CONNECTION_STATUS_CONNECTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connection is not active")
    access_token = _access_token_for(conn, resolved)
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Connection token is unavailable")

    provider = get_plaid_provider(resolved)
    synced_at = _now()
    accounts = provider.get_accounts(access_token)
    holdings = provider.get_holdings(access_token)
    institution_name = provider.get_institution_name(access_token)
    if institution_name:
        conn.institution_name = institution_name
    conn.last_synced_at = synced_at

    accounts_by_external = _upsert_accounts(
        db, conn=conn, user_id=conn.user_id, accounts=accounts, synced_at=synced_at
    )
    _upsert_holdings(
        db,
        user_id=conn.user_id,
        accounts_by_external=accounts_by_external,
        holdings=holdings,
        synced_at=synced_at,
    )
    record_audit_event(
        db,
        actor_subject=subject.subject,
        action="plaid.connection.refresh",
        resource_type="plaid_connection",
        resource_id=str(conn.id),
        metadata={"account_count": len(accounts), "holding_count": len(holdings)},
    )
    db.commit()
    return get_overview(db, subject, resolved)


def disconnect_connection(
    db: Session,
    subject: AuthenticatedSubject,
    connection_id: uuid.UUID,
    settings: Settings | None = None,
) -> ConnectorsOverviewOut:
    resolved = settings or get_settings()
    conn = _owned_connection(db, subject, connection_id)
    provider = get_plaid_provider(resolved)
    access_token = _access_token_for(conn, resolved)
    if access_token:
        provider.remove_item(access_token)

    conn.access_token_ciphertext = None
    conn.token_vault_ref = None
    conn.encryption_kid = None
    conn.status = CONNECTION_STATUS_DISCONNECTED
    conn.disconnected_at = _now()

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action="plaid.connection.disconnect",
        resource_type="plaid_connection",
        resource_id=str(conn.id),
        metadata={"mode": provider.mode},
    )
    db.commit()
    return get_overview(db, subject, resolved)


def request_deletion(
    db: Session,
    subject: AuthenticatedSubject,
    connection_id: uuid.UUID,
    settings: Settings | None = None,
) -> DeletionRequestOut:
    resolved = settings or get_settings()
    conn = _owned_connection(db, subject, connection_id)
    provider = get_plaid_provider(resolved)
    access_token = _access_token_for(conn, resolved)
    if access_token:
        provider.remove_item(access_token)

    # Purge mirrored account/holding rows while retaining an audit trail on the connection.
    for account in list(conn.accounts):
        db.delete(account)

    conn.access_token_ciphertext = None
    conn.token_vault_ref = None
    conn.encryption_kid = None
    conn.status = CONNECTION_STATUS_PENDING_DELETION
    conn.deletion_requested_at = _now()
    if conn.disconnected_at is None:
        conn.disconnected_at = conn.deletion_requested_at

    deletion = PlaidDeletionRequest(
        connection_id=conn.id,
        user_id=conn.user_id,
        status="completed",
        notes="Local purge of mirrored account and holding data",
        completed_at=_now(),
        requested_by_subject=subject.subject,
    )
    db.add(deletion)
    db.flush()

    user = _load_user(db, subject)
    # Revoke retention consent when the owner requests deletion.
    existing_retention = (
        db.query(ConsentRecord)
        .filter(ConsentRecord.user_id == user.id, ConsentRecord.consent_type == CONSENT_PLAID_DATA_RETENTION)
        .one_or_none()
    )
    if existing_retention is not None:
        existing_retention.granted = False
        existing_retention.recorded_by_subject = subject.subject
        record_audit_event(
            db,
            actor_subject=subject.subject,
            target_subject=subject.subject,
            action="consent.update",
            resource_type="consent",
            resource_id=CONSENT_PLAID_DATA_RETENTION,
            metadata={"consent_type": CONSENT_PLAID_DATA_RETENTION, "granted": False},
        )

    record_audit_event(
        db,
        actor_subject=subject.subject,
        action="plaid.connection.delete_request",
        resource_type="plaid_connection",
        resource_id=str(conn.id),
        metadata={"deletion_request_id": str(deletion.id), "status": deletion.status},
    )
    db.commit()
    db.refresh(deletion)
    return DeletionRequestOut(
        id=str(deletion.id),
        connection_id=str(conn.id),
        status=deletion.status,
        requested_at=deletion.requested_at,
    )


def fake_connect_for_local(
    db: Session,
    subject: AuthenticatedSubject,
    settings: Settings | None = None,
) -> ConnectorsOverviewOut:
    """Smoke helper: link-token + exchange through the fake provider in one step."""
    resolved = settings or get_settings()
    provider = get_plaid_provider(resolved)
    if provider.mode != PROVIDER_MODE_FAKE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fake connect is only available when Plaid credentials are unset",
        )
    create_link_token(db, subject, resolved)
    return exchange_public_token(
        db,
        subject,
        public_token=f"public-fake-{subject.subject}",
        provider_key="any",
        settings=resolved,
    )

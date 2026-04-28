from fastapi import HTTPException, status

from trms_backend.api.request_identity import (
    RequestIdentity,
    RequestIdentityActorMismatchError,
    resolve_actor_id_for_request,
)


def resolve_required_actor_request_field(
    identity: RequestIdentity,
    value: str | None,
    *,
    field_name: str,
) -> str:
    try:
        resolved_value = resolve_actor_id_for_request(identity, value)
    except RequestIdentityActorMismatchError as error:
        expected_actor_id = identity.actor_id or ""
        received_value = value.strip() if isinstance(value, str) else ""
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"{field_name} does not match the authenticated request identity: "
                f"expected '{expected_actor_id}', got '{received_value}'"
            ),
        ) from error

    if resolved_value is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} is required when request is anonymous",
        )

    return resolved_value

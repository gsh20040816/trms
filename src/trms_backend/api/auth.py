from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from trms_backend.api.request_identity import (
    RequestIdentity,
    build_authenticated_request_identity_dependency,
    build_invalid_bearer_token_exception,
    build_optional_request_identity_dependency,
    extract_bearer_token,
)
from trms_backend.domain.auth import (
    AuthRepository,
    InvalidCredentialsError,
    InvalidBootstrapRoleError,
    InvalidBootstrapTokenError,
    PrivilegedBootstrapAlreadyCompletedError,
    PrivilegedBootstrapDisabledError,
    PrivilegedSelfRegistrationDisabledError,
    UserLoginInput,
    UserRegisterInput,
    UsernameAlreadyExistsError,
    bootstrap_privileged_user,
    login_user,
    register_user,
    revoke_access_token,
)


def build_auth_router(
    repository: AuthRepository,
    *,
    allow_privileged_self_registration: bool,
    bootstrap_admin_token: str | None,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])
    optional_request_identity = build_optional_request_identity_dependency(repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(repository)

    @router.post("/register", status_code=status.HTTP_201_CREATED)
    def register(payload: UserRegisterInput):
        try:
            return register_user(
                repository,
                payload,
                allow_privileged_self_registration=allow_privileged_self_registration,
            )
        except UsernameAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except PrivilegedSelfRegistrationDisabledError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

    @router.post("/bootstrap-admin", status_code=status.HTTP_201_CREATED)
    def bootstrap_admin(
        payload: UserRegisterInput,
        bootstrap_token: Annotated[
            str | None,
            Header(alias="X-TRMS-Bootstrap-Token"),
        ] = None,
    ):
        try:
            return bootstrap_privileged_user(
                repository,
                payload,
                bootstrap_token=bootstrap_token,
                configured_bootstrap_token=bootstrap_admin_token,
            )
        except InvalidBootstrapRoleError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except PrivilegedBootstrapDisabledError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except InvalidBootstrapTokenError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
            ) from error
        except PrivilegedBootstrapAlreadyCompletedError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except UsernameAlreadyExistsError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

    @router.post("/login")
    def login(payload: UserLoginInput):
        try:
            return login_user(repository, payload)
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    @router.get("/request-context")
    def get_request_context(
        identity: Annotated[RequestIdentity, Depends(optional_request_identity)],
    ):
        return identity

    @router.get("/me")
    def me(identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)]):
        assert identity.user is not None
        return identity.user

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        response: Response,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        authorization: Annotated[str | None, Header()] = None,
    ):
        assert identity.user is not None
        access_token = extract_bearer_token(authorization)
        if access_token is None or not revoke_access_token(repository, access_token):
            raise build_invalid_bearer_token_exception()
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    return router

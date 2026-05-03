from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

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
    CurrentPasswordIncorrectError,
    MemberCodeUpdateNotAllowedError,
    RoleNotAssignedError,
    RoleSwitchInput,
    SelfServiceMultipleRolesNotAllowedError,
    UserPasswordChangeInput,
    UserProfileUpdateInput,
    UserLoginInput,
    UserRegisterInput,
    UsernameAlreadyExistsError,
    bootstrap_privileged_user,
    change_user_password,
    update_user_profile,
    login_user,
    revoke_access_token,
    switch_active_role,
)
from trms_backend.application.self_service_registration import (
    OutboundEmailNotConfiguredError,
    RegistrationEmailHostNotAllowedError,
    RegistrationEmailRequiredError,
    RegistrationEmailVerificationCodeExpiredError,
    RegistrationEmailVerificationCodeInvalidError,
    RegistrationEmailVerificationCodeRequiredError,
    SelfServiceRegistrationService,
)
from trms_backend.domain.email_bindings import EmailAccountBindingConflictError


class RegistrationVerificationCodeRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


def build_auth_router(
    repository: AuthRepository,
    *,
    self_service_registration_service: SelfServiceRegistrationService,
    bootstrap_admin_token: str | None,
) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])
    optional_request_identity = build_optional_request_identity_dependency(repository)
    authenticated_request_identity = build_authenticated_request_identity_dependency(repository)

    @router.post("/register", status_code=status.HTTP_201_CREATED)
    def register(payload: UserRegisterInput):
        try:
            return self_service_registration_service.register(payload)
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
        except SelfServiceMultipleRolesNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RegistrationEmailRequiredError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RegistrationEmailVerificationCodeRequiredError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(error),
            ) from error
        except RegistrationEmailVerificationCodeInvalidError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        except RegistrationEmailVerificationCodeExpiredError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except RegistrationEmailHostNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except EmailAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error

    @router.post("/registration-verification-code", status_code=status.HTTP_202_ACCEPTED)
    def send_registration_verification_code(payload: RegistrationVerificationCodeRequest):
        try:
            dispatch_result = self_service_registration_service.send_verification_code(
                email=payload.email,
            )
        except OutboundEmailNotConfiguredError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error
        except RegistrationEmailHostNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except EmailAccountBindingConflictError as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        return {"item": dispatch_result}

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

    @router.put("/me")
    def update_me(
        payload: UserProfileUpdateInput,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
    ):
        assert identity.user is not None
        try:
            return update_user_profile(
                repository,
                actor=identity.user,
                payload=payload,
            )
        except MemberCodeUpdateNotAllowedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    @router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
    def update_my_password(
        payload: UserPasswordChangeInput,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        response: Response,
    ):
        assert identity.user is not None
        try:
            change_user_password(
                repository,
                actor=identity.user,
                payload=payload,
            )
        except CurrentPasswordIncorrectError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    @router.post("/switch-role")
    def switch_role(
        payload: RoleSwitchInput,
        identity: Annotated[RequestIdentity, Depends(authenticated_request_identity)],
        authorization: Annotated[str | None, Header()] = None,
    ):
        assert identity.user is not None
        access_token = extract_bearer_token(authorization)
        if access_token is None:
            raise build_invalid_bearer_token_exception()
        try:
            return switch_active_role(repository, access_token, payload.role)
        except InvalidCredentialsError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
                headers={"WWW-Authenticate": "Bearer"},
            ) from error
        except RoleNotAssignedError as error:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(error),
            ) from error

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

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response, status

from trms_backend.domain.auth import (
    AuthRepository,
    InvalidCredentialsError,
    UserLoginInput,
    UserRegisterInput,
    UsernameAlreadyExistsError,
    get_user_by_access_token,
    login_user,
    register_user,
    revoke_access_token,
)


def build_auth_router(repository: AuthRepository) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/register", status_code=status.HTTP_201_CREATED)
    def register(payload: UserRegisterInput):
        try:
            return register_user(repository, payload)
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

    @router.get("/me")
    def me(authorization: Annotated[str | None, Header()] = None):
        return _require_authenticated_user(repository, authorization)

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(response: Response, authorization: Annotated[str | None, Header()] = None):
        access_token = _extract_bearer_token(authorization)
        if access_token is None or not revoke_access_token(repository, access_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid or missing bearer token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    return router


def _require_authenticated_user(repository: AuthRepository, authorization: str | None):
    access_token = _extract_bearer_token(authorization)
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = get_user_by_access_token(repository, access_token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def _extract_bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer":
        return None
    normalized_token = token.strip()
    return normalized_token if normalized_token else None

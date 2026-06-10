from __future__ import annotations

from fastapi import HTTPException, status


def unauthorized(detail: str = "Not authenticated") -> HTTPException:
    """Return a 401 HTTPException."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def forbidden(detail: str = "Forbidden") -> HTTPException:
    """Return a 403 HTTPException."""
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def not_found(detail: str = "Not found") -> HTTPException:
    """Return a 404 HTTPException."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def bad_request(detail: str) -> HTTPException:
    """Return a 400 HTTPException."""
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

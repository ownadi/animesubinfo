"""Custom exceptions for animesubinfo."""


class SessionDataError(Exception):
    """Raised when session data cannot be obtained for a subtitle."""

    def __init__(self, subtitle_id: int):
        self.subtitle_id = subtitle_id
        super().__init__(f"Could not obtain session data for subtitle ID {subtitle_id}")


class SecurityError(Exception):
    """Raised when AnimeSub.info returns a security error (błąd zabezpieczeń).

    This typically happens when the session tokens (sh and cookie) are invalid or expired.
    """

    def __init__(self, subtitle_id: int, sh: str, cookie: str):
        self.subtitle_id = subtitle_id
        self.sh = sh
        self.cookie = cookie
        super().__init__(
            f"Security error downloading subtitle ID {subtitle_id}. "
            f"The session tokens may be invalid or expired. "
            f"(sh={sh[:20]}..., cookie={cookie[:20]}...)"
        )


__all__ = ["SessionDataError", "SecurityError"]

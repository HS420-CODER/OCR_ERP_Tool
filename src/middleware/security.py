"""
ERP Arabic OCR Microservice - API Security Middleware
======================================================
Implements authentication, rate limiting, and permission control.
"""

import time
import hashlib
import logging
import functools
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict
import threading

from flask import Flask, request, g, jsonify

logger = logging.getLogger(__name__)


@dataclass
class APIClient:
    """Represents an API client with permissions."""
    api_key: str
    client_id: str
    name: str
    permissions: Set[str] = field(default_factory=lambda: {"read", "write"})
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None


@dataclass
class RateLimitEntry:
    """Rate limit tracking entry."""
    minute_requests: List[float] = field(default_factory=list)
    hour_requests: List[float] = field(default_factory=list)


class RateLimiter:
    """
    Token bucket rate limiter with per-client tracking.

    Features:
    - Per-minute and per-hour limits
    - Sliding window algorithm
    - Thread-safe operations
    """

    def __init__(self):
        """Initialize rate limiter."""
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = threading.Lock()

    def check_limit(
        self,
        client_id: str,
        limit_per_minute: int,
        limit_per_hour: int
    ) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limits.

        Args:
            client_id: Client identifier
            limit_per_minute: Max requests per minute
            limit_per_hour: Max requests per hour

        Returns:
            Tuple of (allowed, error_message)
        """
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        with self._lock:
            entry = self._entries[client_id]

            # Clean old entries
            entry.minute_requests = [t for t in entry.minute_requests if t > minute_ago]
            entry.hour_requests = [t for t in entry.hour_requests if t > hour_ago]

            # Check minute limit
            if len(entry.minute_requests) >= limit_per_minute:
                wait_time = int(60 - (now - entry.minute_requests[0]))
                return False, f"Rate limit exceeded. Try again in {wait_time} seconds"

            # Check hour limit
            if len(entry.hour_requests) >= limit_per_hour:
                wait_time = int(3600 - (now - entry.hour_requests[0]))
                return False, f"Hourly limit exceeded. Try again in {wait_time // 60} minutes"

            # Record request
            entry.minute_requests.append(now)
            entry.hour_requests.append(now)

            return True, None

    def get_usage(self, client_id: str) -> Dict[str, int]:
        """Get current usage for a client."""
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600

        with self._lock:
            entry = self._entries.get(client_id, RateLimitEntry())
            return {
                "requests_last_minute": len([t for t in entry.minute_requests if t > minute_ago]),
                "requests_last_hour": len([t for t in entry.hour_requests if t > hour_ago])
            }

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a client."""
        with self._lock:
            if client_id in self._entries:
                del self._entries[client_id]


class APISecurityMiddleware:
    """
    Flask middleware for API security.

    Features:
    - API key authentication (Bearer token)
    - Per-client rate limiting
    - Permission-based access control
    - Request logging
    - IP-based fallback identification
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = {
        '/api/v2/ocr/health',
        '/api/v2/ocr/metrics',
    }

    def __init__(self, app: Optional[Flask] = None):
        """
        Initialize security middleware.

        Args:
            app: Flask application (optional, can use init_app later)
        """
        self._clients: Dict[str, APIClient] = {}
        self._key_to_client: Dict[str, str] = {}  # API key -> client_id mapping
        self._rate_limiter = RateLimiter()
        self._enabled = True
        self._lock = threading.Lock()

        if app:
            self.init_app(app)

    def init_app(self, app: Flask) -> None:
        """
        Initialize middleware with Flask app.

        Args:
            app: Flask application
        """
        # Register before_request handler
        app.before_request(self._check_security)

        # Store reference in app config
        app.config['SECURITY_MIDDLEWARE'] = self

        # Load settings
        self._load_settings(app)

        logger.info("API Security Middleware initialized")

    def _load_settings(self, app: Flask) -> None:
        """Load security settings from app config."""
        try:
            from config.settings import get_settings
            settings = get_settings()

            self._enabled = settings.security.require_api_key

            # Register API keys from settings
            for api_key in settings.security.api_keys:
                if api_key:
                    self.register_api_key(
                        api_key=api_key,
                        client_id=f"config_{hashlib.md5(api_key.encode()).hexdigest()[:8]}",
                        name="Config API Key",
                        rate_limit_per_minute=settings.security.rate_limit_per_minute,
                        rate_limit_per_hour=settings.security.rate_limit_per_hour
                    )

            logger.info(f"Loaded {len(self._clients)} API keys from settings")

        except Exception as e:
            logger.warning(f"Could not load security settings: {e}")

    def register_api_key(
        self,
        api_key: str,
        client_id: str,
        name: str,
        permissions: Optional[Set[str]] = None,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000
    ) -> APIClient:
        """
        Register a new API key.

        Args:
            api_key: The API key string
            client_id: Unique client identifier
            name: Human-readable client name
            permissions: Set of permissions (default: read, write)
            rate_limit_per_minute: Per-minute rate limit
            rate_limit_per_hour: Per-hour rate limit

        Returns:
            Created APIClient object
        """
        with self._lock:
            client = APIClient(
                api_key=api_key,
                client_id=client_id,
                name=name,
                permissions=permissions or {"read", "write"},
                rate_limit_per_minute=rate_limit_per_minute,
                rate_limit_per_hour=rate_limit_per_hour
            )

            self._clients[client_id] = client
            self._key_to_client[api_key] = client_id

            logger.info(f"Registered API key for client: {name} ({client_id})")
            return client

    def revoke_api_key(self, api_key: str) -> bool:
        """
        Revoke an API key.

        Args:
            api_key: API key to revoke

        Returns:
            True if revoked, False if not found
        """
        with self._lock:
            client_id = self._key_to_client.get(api_key)
            if client_id:
                del self._key_to_client[api_key]
                if client_id in self._clients:
                    del self._clients[client_id]
                logger.info(f"Revoked API key for client: {client_id}")
                return True
            return False

    def _check_security(self) -> Optional[tuple]:
        """
        Before-request handler for security checks.

        Returns:
            Error response tuple if blocked, None if allowed
        """
        # Skip non-v2 API routes
        if not request.path.startswith('/api/v2/ocr'):
            return None

        # Skip public paths
        if request.path in self.PUBLIC_PATHS:
            return None

        # Skip if security is disabled
        if not self._enabled:
            g.client_id = 'anonymous'
            g.client_name = 'Anonymous'
            return None

        # Validate API key
        client = self._validate_api_key()

        if client is None:
            return self._unauthorized_response()

        if not client.enabled:
            return self._forbidden_response("API key is disabled")

        # Check rate limit
        allowed, error_msg = self._check_rate_limit(client)
        if not allowed:
            return self._rate_limit_response(error_msg)

        # Store client info in request context
        g.client_id = client.client_id
        g.client_name = client.name
        g.client_permissions = client.permissions

        # Update last used
        client.last_used = datetime.utcnow()

        return None

    def _validate_api_key(self) -> Optional[APIClient]:
        """
        Validate API key from request headers.

        Supports:
        - Authorization: Bearer <key>
        - X-API-Key: <key>

        Returns:
            APIClient if valid, None otherwise
        """
        # Try Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            api_key = auth_header[7:]
        else:
            # Try X-API-Key header
            api_key = request.headers.get('X-API-Key', '')

        if not api_key:
            return None

        # Look up client
        with self._lock:
            client_id = self._key_to_client.get(api_key)
            if client_id:
                return self._clients.get(client_id)

        return None

    def _check_rate_limit(self, client: APIClient) -> tuple[bool, Optional[str]]:
        """
        Check rate limit for client.

        Args:
            client: API client

        Returns:
            Tuple of (allowed, error_message)
        """
        return self._rate_limiter.check_limit(
            client.client_id,
            client.rate_limit_per_minute,
            client.rate_limit_per_hour
        )

    def _unauthorized_response(self) -> tuple:
        """Generate 401 Unauthorized response."""
        return jsonify({
            "success": False,
            "error": {
                "code": "UNAUTHORIZED",
                "message": "API key required. Use 'Authorization: Bearer <key>' header"
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 401

    def _forbidden_response(self, message: str) -> tuple:
        """Generate 403 Forbidden response."""
        return jsonify({
            "success": False,
            "error": {
                "code": "FORBIDDEN",
                "message": message
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 403

    def _rate_limit_response(self, message: str) -> tuple:
        """Generate 429 Rate Limited response."""
        return jsonify({
            "success": False,
            "error": {
                "code": "RATE_LIMITED",
                "message": message
            },
            "timestamp": datetime.utcnow().isoformat()
        }), 429

    def require_permission(self, permission: str) -> Callable:
        """
        Decorator to require specific permission.

        Args:
            permission: Required permission string

        Returns:
            Decorator function
        """
        def decorator(f: Callable) -> Callable:
            @functools.wraps(f)
            def decorated_function(*args, **kwargs):
                client_permissions = getattr(g, 'client_permissions', set())

                if permission not in client_permissions:
                    return jsonify({
                        "success": False,
                        "error": {
                            "code": "INSUFFICIENT_PERMISSIONS",
                            "message": f"Permission '{permission}' required"
                        },
                        "timestamp": datetime.utcnow().isoformat()
                    }), 403

                return f(*args, **kwargs)
            return decorated_function
        return decorator

    def get_client_info(self, client_id: str) -> Optional[Dict]:
        """Get client information."""
        with self._lock:
            client = self._clients.get(client_id)
            if client:
                usage = self._rate_limiter.get_usage(client_id)
                return {
                    "client_id": client.client_id,
                    "name": client.name,
                    "permissions": list(client.permissions),
                    "enabled": client.enabled,
                    "rate_limit_per_minute": client.rate_limit_per_minute,
                    "rate_limit_per_hour": client.rate_limit_per_hour,
                    "usage": usage,
                    "last_used": client.last_used.isoformat() if client.last_used else None
                }
        return None

    def list_clients(self) -> List[Dict]:
        """List all registered clients."""
        with self._lock:
            return [
                {
                    "client_id": c.client_id,
                    "name": c.name,
                    "enabled": c.enabled,
                    "permissions": list(c.permissions)
                }
                for c in self._clients.values()
            ]

    def disable_security(self) -> None:
        """Disable security checks (for testing)."""
        self._enabled = False
        logger.warning("API security disabled")

    def enable_security(self) -> None:
        """Enable security checks."""
        self._enabled = True
        logger.info("API security enabled")


# Singleton instance
_security_middleware: Optional[APISecurityMiddleware] = None


def get_security_middleware() -> APISecurityMiddleware:
    """Get the global security middleware instance."""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = APISecurityMiddleware()
    return _security_middleware


def init_security(app: Flask) -> APISecurityMiddleware:
    """Initialize security middleware for Flask app."""
    middleware = get_security_middleware()
    middleware.init_app(app)
    return middleware


# Export
__all__ = [
    "APISecurityMiddleware",
    "APIClient",
    "RateLimiter",
    "get_security_middleware",
    "init_security"
]

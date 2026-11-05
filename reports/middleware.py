CSP = (
    "default-src 'self'; "
    "script-src 'self' https://unpkg.com; "
    "style-src 'self' https://unpkg.com; "
    "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://*.supabase.co; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "base-uri 'self'"
)


class SecurityHeadersMiddleware:
    """RNF02 – Content-Security-Policy e cabeçalhos básicos de segurança."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", "geolocation=(self), camera=(self)")
        return response

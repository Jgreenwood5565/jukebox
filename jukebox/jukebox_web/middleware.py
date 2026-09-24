# scripts only from the jukebox itself, a second line of defence against
# injected song metadata; inline styles are allowed for the admin
CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'self'",
        "img-src 'self' data:",
        "style-src 'self' 'unsafe-inline'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ]
)


def content_security_policy(get_response):
    def middleware(request):
        response = get_response(request)
        response.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
        return response

    return middleware

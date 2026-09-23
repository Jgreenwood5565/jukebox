import hashlib

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.core.cache import cache
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_POST

from jukebox.jukebox_core.models import Genre, Song

from .context_processors import THEME_COOKIE_NAME, THEMES


@login_required
def index(request):
    request.session.set_expiry(settings.SESSION_TTL)

    years = (
        Song.objects.values_list("Year", flat=True)
        .exclude(Year=None)
        .exclude(Year=0)
        .order_by("Year")
        .distinct()
    )
    context = {
        "username": request.user.get_full_name() or request.user.get_username(),
        "genres": Genre.objects.all(),
        "years": years,
    }
    return render(request, "index.html", context)


def _login_attempts_key(request):
    username = request.POST.get("username", "").strip().lower()
    client = f"{request.META.get('REMOTE_ADDR', '')}:{username}"
    return "jukebox:login-attempts:" + hashlib.sha256(client.encode()).hexdigest()


class LoginView(auth_views.LoginView):
    """Login with a local account and/or links to the enabled social providers."""

    template_name = "login.html"
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["backends"] = settings.SOCIAL_AUTH_ENABLED_BACKENDS
        context["local_login"] = settings.JUKEBOX_LOCAL_LOGIN
        return context

    def post(self, request, *args, **kwargs):
        if not settings.JUKEBOX_LOCAL_LOGIN:
            return HttpResponseNotAllowed(["GET"])

        if cache.get(_login_attempts_key(request), 0) >= settings.JUKEBOX_LOGIN_ATTEMPTS:
            context = self.get_context_data(form=self.form_class(request), locked=True)
            return self.render_to_response(context, status=429)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        cache.delete(_login_attempts_key(self.request))
        return super().form_valid(form)

    def form_invalid(self, form):
        key = _login_attempts_key(self.request)
        cache.add(key, 0, settings.JUKEBOX_LOGIN_LOCKOUT)
        try:
            cache.incr(key)
        except ValueError:
            # expired in between
            pass
        return super().form_invalid(form)


class LoginErrorView(LoginView):
    """Social auth redirects here if the login failed."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["error"] = get_messages(self.request)
        return context


@require_POST
def logout(request):
    auth_logout(request)
    return redirect("jukebox_web_login")


def language(request, language):
    response = HttpResponseRedirect(reverse("jukebox_web_index"))
    if translation.check_for_language(language):
        translation.activate(language)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            language,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            secure=settings.LANGUAGE_COOKIE_SECURE,
            httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
        )
    return response


def theme(request, theme):
    response = HttpResponseRedirect(reverse("jukebox_web_index"))
    if theme in THEMES:
        response.set_cookie(
            THEME_COOKIE_NAME, theme, max_age=365 * 24 * 60 * 60, samesite="Lax", httponly=True
        )
    return response

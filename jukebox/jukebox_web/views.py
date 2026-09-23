from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.messages import get_messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_POST

from jukebox.jukebox_core.models import Genre, Song


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


def login(request):
    if request.user.is_authenticated:
        return redirect("jukebox_web_index")

    return render(request, "login.html", {"backends": settings.SOCIAL_AUTH_ENABLED_BACKENDS})


def login_error(request):
    return render(
        request,
        "login.html",
        {
            "backends": settings.SOCIAL_AUTH_ENABLED_BACKENDS,
            "error": get_messages(request),
        },
    )


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

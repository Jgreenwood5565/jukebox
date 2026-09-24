"""Managing accounts from the web interface, for admins (staff users) only."""

import functools

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

User = get_user_model()


def admin_required(view):
    @login_required
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper


def _set_name(user, name):
    user.first_name, _separator, user.last_name = name.strip().partition(" ")


class NameAndRoleMixin(forms.Form):
    name = forms.CharField(label=gettext_lazy("Name"), required=False, max_length=150)
    is_staff = forms.BooleanField(
        label=gettext_lazy("Administrator"),
        required=False,
        help_text=gettext_lazy("Can manage users and skip songs right away"),
    )

    def apply(self, user):
        _set_name(user, self.cleaned_data["name"])
        # like "jukebox_adduser --admin", admins get the Django admin too
        user.is_staff = user.is_superuser = self.cleaned_data["is_staff"]


class AddUserForm(NameAndRoleMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username",)

    field_order = ("username", "name", "password1", "password2", "is_staff")

    def save(self, commit=True):
        user = super().save(commit=False)
        self.apply(user)
        user.save()
        return user


class EditUserForm(NameAndRoleMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("is_active",)
        labels = {"is_active": gettext_lazy("Account enabled")}
        help_texts = {"is_active": gettext_lazy("Disabled accounts can't log in")}

    field_order = ("name", "is_staff", "is_active")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial.setdefault("name", self.instance.get_full_name())
        self.initial.setdefault("is_staff", self.instance.is_staff)

    def save(self, commit=True):
        self.apply(self.instance)
        return super().save(commit)


def _render(request, add_form=None, open_user=None, edit_form=None, password_form=None):
    rows = []
    for user in User.objects.order_by(Lower("username")):
        is_open = user.id == open_user
        rows.append(
            {
                "user": user,
                "open": is_open,
                "edit_form": edit_form
                if is_open and edit_form
                else EditUserForm(instance=user, prefix=f"user{user.id}"),
                "password_form": password_form
                if is_open and password_form
                else SetPasswordForm(user, prefix=f"password{user.id}"),
            }
        )
    context = {"add_form": add_form or AddUserForm(prefix="add"), "rows": rows}
    invalid = any(form is not None and form.errors for form in (add_form, edit_form, password_form))
    return render(request, "users.html", context, status=400 if invalid else 200)


@admin_required
def users(request):
    if request.method != "POST":
        return _render(request)

    form = AddUserForm(request.POST, prefix="add")
    if not form.is_valid():
        return _render(request, add_form=form)
    user = form.save()
    messages.success(request, _("Added %(username)s.") % {"username": user.username})
    return redirect("jukebox_web_users")


@require_POST
@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    form = EditUserForm(request.POST, instance=user, prefix=f"user{user.id}")
    if not form.is_valid():
        return _render(request, open_user=user.id, edit_form=form)

    if user == request.user and not (
        form.cleaned_data["is_staff"] and form.cleaned_data["is_active"]
    ):
        # somebody has to be left to manage the users
        messages.error(request, _("You can't remove your own admin rights or disable yourself."))
    else:
        form.save()
        messages.success(request, _("Saved %(username)s.") % {"username": user.username})
    return redirect("jukebox_web_users")


@require_POST
@admin_required
def user_password(request, user_id):
    user = get_object_or_404(User, id=user_id)
    form = SetPasswordForm(user, request.POST, prefix=f"password{user.id}")
    if not form.is_valid():
        return _render(request, open_user=user.id, password_form=form)

    form.save()
    if user == request.user:
        # changing the password logs out all sessions, except this one
        update_session_auth_hash(request, user)
    messages.success(
        request, _("Changed the password of %(username)s.") % {"username": user.username}
    )
    return redirect("jukebox_web_users")


@require_POST
@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, _("You can't delete yourself."))
    else:
        user.delete()
        messages.success(request, _("Deleted %(username)s.") % {"username": user.username})
    return redirect("jukebox_web_users")

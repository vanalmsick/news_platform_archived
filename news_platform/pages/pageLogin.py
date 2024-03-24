from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import redirect, render


class LoginForm(forms.Form):
    password = forms.CharField(
        max_length=63, widget=forms.TextInput(attrs={"class": "form-control"})
    )


def LoginView(request, meta=f"<title>{settings.CUSTOM_PLATFORM_NAME}</title>"):
    form = LoginForm()
    message = ""
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username="user",
                password=form.cleaned_data["password"],
            )
            if user is not None:
                message = "Login successful!"
                login(request, user)
                if "article" in request.GET:
                    return redirect(
                        f"/view/{request.GET['article']}/?previous=login"
                    )
                else:
                    return redirect("/")
            else:
                message = "Login failed!"
    return render(
        request,
        "login.html",
        context={
            "form": form,
            "message": message,
            "meta": meta,
            "platform_name": settings.CUSTOM_PLATFORM_NAME,
        },
    )



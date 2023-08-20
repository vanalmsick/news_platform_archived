from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django import forms
from django.http import HttpResponse

class LoginForm(forms.Form):
    password = forms.CharField(max_length=63, widget=forms.TextInput(attrs={'class': "form-control"}))


def LoginView(request):
    form = LoginForm()
    message = ''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username='user',
                password=form.cleaned_data['password'],
            )
            if user is not None:
                message = 'Login successful!'
                login(request, user)
                if 'article' in request.GET:
                    return redirect(f"/?article={request.GET['article']}&previous=login")
                else:
                    return redirect('/')
            else:
                message = 'Login failed!'
    return render(request, 'login.html', context={'form': form, 'message': message})


def LoginURLView(request, password):
    user = authenticate(
        username='user',
        password=password,
    )
    if user is not None:
        # login successful
        login(request, user)
        return redirect('/')
    else:
        # Login failed!
        return HttpResponse('Incorrect password provided!', content_type="text/plain")


def LoginHowToView(request):
    return HttpResponse("""
                        <html>
                        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css" rel="stylesheet"
                              integrity="sha384-4bw+/aepP/YC94hEpVNVgiZdgIC5+VKNBQNGCHeKRQN+PtmoHDEXuppvnDJzQIu9" crossorigin="anonymous">
                        <div class="p-3">
                        <h1>How-to Login:</h1>
                        <p><b>Normal Login Page:</b> <a class="btn btn-primary" href="/login/">Normal Login Page</a> (for not firewall blocked browsers)</p>
                        <p><b>Firewall blocked Login:</b> Please modify and open this link <b>news.vanAlmsick.uk/login-url/<i>[put password here]</i>/</b></p>
                        </div>
                        </html>
                        """)
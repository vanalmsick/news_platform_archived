from django.contrib.auth import login, authenticate
from django.shortcuts import redirect, render
from django import forms

class LoginForm(forms.Form):
    secret_word = forms.CharField(max_length=63, widget=forms.TextInput(attrs={'class': "form-control"}))


def LoginView(request):
    form = LoginForm()
    message = ''
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username='user',
                password=form.cleaned_data['secret_word'],
            )
            if user is not None:
                message = 'Secret word correct!'
                login(request, user)
                return redirect('/')
            else:
                message = 'Secret word incorrect!'
    return render(request, 'login.html', context={'form': form, 'message': message})
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.conf import settings

from .models import User

from .forms import RegisterForm
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_django


def register(request):
    template_name = 'cadastro.html'
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            user = authenticate(
                username=user.username,
                password=form.cleaned_data['password1']
            )
            login_django(request, user)
            return redirect(settings.LOGIN_URL)
            #return HTTPRequest('sucesso')
    else:
        form = RegisterForm()

    context = {
        'form': form
    }
    return render(request, template_name, context)


def listar(request):
    usuarios = User.objects.filter(is_active=True).order_by('username')
    context = {'usuarios': usuarios}
    return render(request, 'lista_usuarios.html', context)
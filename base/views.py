from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def not_found(request, exepction):
    return render(request, 'not_found.html')


def handler403(request, exception):
    return render(request, '403.html')

def handler500(request):
    return render(request, "500.html", status=500)


# ===================================
# View temporária para testar Sentry
# Remover após confirmar que funciona
# ===================================
def trigger_sentry_test(request):
    division_by_zero = 1 / 0
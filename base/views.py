from django.shortcuts import render

# Create your views here.
def not_found(request, exepction):
    return render(request, 'not_found.html')


def handler403(request, exception):
    return render(request, '403.html')
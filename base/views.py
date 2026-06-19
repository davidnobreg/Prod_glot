from django.shortcuts import render


def not_found(request, exception=None):
    return render(request, 'not_found.html', status=404)


def handler403(request, exception=None):
    return render(request, '403.html', status=403)


def handler500(request):
    return render(request, '500.html', status=500)


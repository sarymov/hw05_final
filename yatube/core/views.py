from django.shortcuts import render
from http import HTTPStatus


def page_not_found(request, exception):
    return render(request, 'core/404.html', {'path': request.path}, status=404)


def csrf_failure(request, reason=''):
    return render(request, 'core/403csrf.html')


def csrf_failure(request, reason=''):
    return render(request, 'core/403csrf.html')


def server_error(request):
    status = HTTPStatus.INTERNAL_SERVER_ERROR
    return render(request, 'core/500.html', status=status)

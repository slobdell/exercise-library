from django.conf import settings
from django.http import HttpResponseRedirect


def requires_ssl(fn):
    def inner(request, *args, **kwargs):
        if not any([
            settings.DEBUG,
            request.is_secure(),
            request.META.get("HTTP_X_FORWARDED_PROTO", "") == 'https',
            'HTTP_X_SSL_PROTOCOL' in request.META
        ]):
            url = request.build_absolute_uri(request.get_full_path())
            secure_url = url.replace("http://", "https://")
            return HttpResponseRedirect(secure_url)
        return fn(request, *args, **kwargs)

    return inner

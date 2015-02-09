import json

from django.http import Http404
from django.http import HttpResponse


def render_to_json(response_obj, context={}, content_type="application/json", status=200):
    json_str = json.dumps(response_obj, indent=4)
    return HttpResponse(json_str, content_type=content_type, status=status)


def requires_post(fn):
    def inner(request, *args, **kwargs):
        if request.method != "POST":
            return Http404
        # post_data = request.POST or json.loads(request.body)
        return fn(request, *args, **kwargs)
    return inner

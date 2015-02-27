import json

from django.http import Http404
from django.http import HttpResponse
from exercise_library.auto_corrector import SpellChecker, AutoCompleter


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


def autocomplete(request):
    spellchecker = SpellChecker()
    search_term_so_far = request.GET.get('q', '')
    if len(search_term_so_far) >= 4:
        tokens = spellchecker.correct_phrase(search_term_so_far)
    else:
        tokens = search_term_so_far.split()
    suggestions = AutoCompleter().guess_exercises(tokens)
    return render_to_json(suggestions)

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

    tokens = spellchecker.correct_phrase(search_term_so_far)
    suggestions = AutoCompleter().guess_exercises(tokens)

    return render_to_json(suggestions)


def exercise_from_name(request):
    exercise_name = request.GET.get('exercise', '')
    exercise_dict = AutoCompleter.get_exercise_dict_from_name(exercise_name)
    return render_to_json(exercise_dict)

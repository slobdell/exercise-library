import json

from django.http import Http404
from django.http import HttpResponse
from exercise_library.auto_corrector import SpellChecker, AutoCompleter
from exercise_library.exercise_cacher import ExerciseCacher
# from exercise_library.cloud_search.tasks import save_exercise_to_amazon

from exercise_library.auto_corrector import Tokenizer
from exercise_library.constants import Exercise
from exercise_library.constants import Equipment
from exercise_library.constants import ExerciseType
from exercise_library.constants import MuscleGroup
from exercise_library.constants import Phase
from exercise_library.constants import WorkoutComponent
from exercise_library.dynamo.dynamo_client import DynamoClient


def render_to_json(response_obj, context={}, content_type="application/json", status=200):
    json_str = json.dumps(response_obj, indent=4)
    return HttpResponse(json_str, content_type=content_type, status=status)


def requires_post(fn):
    def inner(request, *args, **kwargs):
        if request.method != "POST":
            return Http404
        post_data = request.POST or json.loads(request.body)
        kwargs["post_data"] = post_data
        return fn(request, *args, **kwargs)
    return inner


def _create_muscle_tree():
    muscle_tree = MuscleGroup.get_muscle_ids_as_tree()
    for top_level_muscle, muscle_dict in muscle_tree.items():
        for low_level_muscle, muscle_id_list in muscle_dict.items():
            for index in xrange(len(muscle_id_list)):
                muscle_name = MuscleGroup.get_name_for_id(muscle_id_list[index])
                muscle_id_list[index] = (muscle_id_list[index], muscle_name)

    # SBL probably better way to do this
    muscle_tree_as_list = []
    for top_level_muscle, muscle_dict in muscle_tree.items():
        muscle_tree_as_list.append([top_level_muscle, list(muscle_dict.items())])

    return muscle_tree_as_list


def get_exercises(request):
    return render_to_json({
        'exercises': ExerciseCacher().exercises,
        'equipment': sorted(Equipment.as_json(), key=lambda d: d['title']),
        'muscle_groups': sorted(MuscleGroup.as_json(), key=lambda d: d['title']),
        'muscle_tree': _create_muscle_tree(),
        'phases': sorted(Phase.as_json(), key=lambda p: p['title']),
        'workout_components': sorted(WorkoutComponent.as_json(), key=lambda w: w['title']),
        'exercise_types': sorted(ExerciseType.as_json(), key=lambda d: d['title'])
    })


def verbose_autocomplete(request):
    spellchecker = SpellChecker()
    search_term_so_far = request.GET.get('q', '')

    tokens = spellchecker.correct_phrase(search_term_so_far)
    suggestions = AutoCompleter().guess_exercises(tokens)

    autocompleter = AutoCompleter()
    exercise_dict_list = [autocompleter.get_exercise_dict_from_name(exercise_name) for exercise_name in suggestions]
    MAX_RESULTS = 10
    return render_to_json(exercise_dict_list[:MAX_RESULTS])


def autocomplete(request):
    # refactor this, a little bit non sober right now
    spellchecker = SpellChecker()
    search_term_so_far = request.GET.get('q', '')

    tokens = spellchecker.correct_phrase(search_term_so_far)
    suggestions = AutoCompleter().guess_exercises(tokens)

    return render_to_json(suggestions)


@requires_post
def save_exercise(request, post_data=None):
    post_data = post_data or {}
    # save_exercise_to_amazon(post_data)
    ExerciseCacher.update_cache_with_exercise(post_data)
    Tokenizer.bust_cache()
    Exercise.rebuild()
    updated_exercises = ExerciseCacher().exercises
    DynamoClient().save_exercises(updated_exercises)
    return render_to_json({}, status=204)


def exercise_from_name(request):
    exercise_name = request.GET.get('exercise', '')
    exercise_dict = AutoCompleter().get_exercise_dict_from_name(exercise_name)
    return render_to_json(exercise_dict)

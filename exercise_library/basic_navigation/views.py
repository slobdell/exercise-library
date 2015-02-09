# import datetime
import json
# import os

# from django.conf import settings
from django.http import HttpResponse
# from django.http import HttpResponseRedirect
# from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response

from exercise_library.constants import Equipment
from exercise_library.constants import Exercise
from exercise_library.constants import ExerciseType
from exercise_library.constants import MuscleGroup


def render_to_json(data, status=200):
    return HttpResponse(json.dumps(data), content_type="application/json", status=status)


def _get_grouped_exercises():
    muscle_name_to_exercises = {}
    list_of_sets = MuscleGroup.get_rings()
    for muscle_group_id_set in list_of_sets:
        for muscle_group_id in muscle_group_id_set:
            muscle_name = MuscleGroup.get_name_for_id(muscle_group_id)
            exercises = sorted(list(Exercise().for_muscle_group(muscle_group_id).query), key=lambda e: e.name)
            if exercises:
                muscle_name_to_exercises[muscle_name] = exercises
    return muscle_name_to_exercises


def global_render_to_response(template, render_data):
    muscle_tree = MuscleGroup.get_muscle_ids_as_tree()
    for top_level_muscle, muscle_dict in muscle_tree.items():
        for low_level_muscle, muscle_id_list in muscle_dict.items():
            for index in xrange(len(muscle_id_list)):
                muscle_id_list[index] = MuscleGroup.get_name_for_id(muscle_id_list[index])
    render_data["muscle_tree"] = muscle_tree
    return render_to_response(template, render_data)


def exercise(request, exercise_name):
    exercise = Exercise.get_by_canonical_name(exercise_name)
    render_data = {
        'exercise': exercise,
        'equipment_names': [Equipment.get_name_for_id(equipment_id) for equipment_id in exercise.equipment_ids],
        'exercise_types': [ExerciseType.get_name_for_id(exercise_type_id) for exercise_type_id in exercise.exercise_type_ids],
        "primary_muscle_group": MuscleGroup.get_name_for_id(exercise.muscle_group_id)
    }
    return global_render_to_response("basic_navigation/exercise.html", render_data)


def home(request):
    exercise_json = Exercise().as_json()

    JSContext = {
        'exercises': exercise_json,
        'equipment': Equipment.as_json(),
        'muscle_groups': MuscleGroup.as_json(),
        'exercise_types': ExerciseType.as_json(),
    }
    render_data = {
        "grouped_exercises": _get_grouped_exercises(),
        "JSContext": json.dumps(JSContext)
    }
    return global_render_to_response("basic_navigation/search_engine_content.html", render_data)

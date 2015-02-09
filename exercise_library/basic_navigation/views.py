# import datetime
import json
# import os

# from django.conf import settings
from django.http import HttpResponse
# from django.http import HttpResponseRedirect
# from django.http import HttpResponsePermanentRedirect
from django.shortcuts import render_to_response

from exercise_library.constants import Equipment
from exercise_library.constants import ExerciseType
from exercise_library.constants import MuscleGroup
from exercise_library.utils import read_file_as_json


def render_to_json(data, status=200):
    return HttpResponse(json.dumps(data), content_type="application/json", status=status)


def home(request):
    JSContext = {
        'exercises': read_file_as_json("exercise_library/exercises.json"),
        'equipment': Equipment.as_json(),
        'muscle_groups': MuscleGroup.as_json(),
        'exercise_types': ExerciseType.as_json(),
    }
    render_data = {
        "JSContext": json.dumps(JSContext)
    }
    return render_to_response("basic_navigation/index.html", render_data)

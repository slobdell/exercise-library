import datetime
import json

from django.conf import settings

from exercise_library.auto_corrector import Tokenizer
from exercise_library.constants import Exercise
from exercise_library.exercise_cacher import ExerciseCacher
from exercise_library.utils import read_file_as_json

from .cloud_search_indexer import CloudSearchIndexer
from .exercise_document import ExerciseDocument


def upload_exercises_to_amazon():
    all_exercises = read_file_as_json("exercise_library/exercises.json")

    # for reverting, delete this when no longer needed
    # all_exercises = read_file_as_json("2015_02_28_exercises.json")
    # for e in all_exercises:
    #     e["backup_video_id"] = e["video_id"]

    with CloudSearchIndexer.for_domain_index(settings.AWS_CLOUDSEARCH_INDEX) as indexer:
        for exercise in all_exercises:
            exercise_doc = ExerciseDocument(exercise)
            indexer.add_document(exercise_doc)


def _no_save_necessary(exercise_json):
    exercise_id = exercise_json["id"]
    exercise = Exercise.get_by_id(exercise_id)
    needs_save = False
    for attr in exercise_json.keys():
        if getattr(exercise, attr) != exercise_json[attr]:
            needs_save = True
    return not needs_save


def save_exercise_to_amazon(exercise_json):
    if _no_save_necessary(exercise_json):
        return

    with CloudSearchIndexer.for_domain_index(settings.AWS_CLOUDSEARCH_INDEX) as indexer:
        exercise_doc = ExerciseDocument(exercise_json)
        indexer.add_document(exercise_doc)

    ExerciseCacher.update_cache_with_exercise(exercise_json)
    Tokenizer.bust_cache()
    Exercise.rebuild()


def dump_from_amazon():
    json_list = ExerciseCacher().exercises
    now = datetime.datetime.utcnow()
    filename = "%s_exercises.json" % now.strftime("%Y_%m_%d")
    with open(filename, "w+") as f:
        f.write(json.dumps(json_list, indent=4))

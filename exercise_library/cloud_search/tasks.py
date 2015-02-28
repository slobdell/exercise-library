from django.conf import settings

from exercise_library.utils import read_file_as_json

from .cloud_search_indexer import CloudSearchIndexer
from .exercise_document import ExerciseDocument


def upload_exercises_to_amazon():
    all_exercises = read_file_as_json("exercise_library/exercises.json")
    with CloudSearchIndexer.for_domain_index(settings.AWS_CLOUDSEARCH_INDEX) as indexer:
        for exercise in all_exercises:
            exercise_doc = ExerciseDocument(exercise)
            indexer.add_document(exercise_doc)


from django.conf import settings
from exercise_library.cloud_search.cloud_search_searcher import CloudSearchSearcher
from exercise_library.utils import make_ints


class ExerciseCacher(object):

    _cls_cache = {}
    _cloud_search_searcher = CloudSearchSearcher(settings.AWS_CLOUDSEARCH_INDEX)

    @property
    def exercises(self):
        try:
            return self._cls_cache["exercises"]
        except KeyError:
            self._cls_cache["exercises"] = self._fetch_exercises()
            return self._cls_cache["exercises"]

    @classmethod
    def bust_cache(cls):
        '''
        Note that simply busting the cache won't work.  Operations on AWS Cloudsearch aren't atomic, so there's a delay between saving and fetching
        '''
        if 'exercises' in cls._cls_cache:
            del cls._cls_cache["exercises"]

    @classmethod
    def update_cache_with_exercise(cls, exercise_json):
        if 'exercises' not in cls._cls_cache:
            return
        all_exercises = cls._cls_cache['exercises']
        for index in xrange(len(all_exercises)):
            if all_exercises[index]["id"] == exercise_json["id"]:
                all_exercises[index] = exercise_json
                return
        all_exercises.append(exercise_json)

    def _fetch_exercises(self):
        query_string = "(not video_id: 'thiswillneverhappen')"
        exercise_json = self._cloud_search_searcher.execute_query_string(query_string)
        make_ints(exercise_json)
        self._default_keys(exercise_json)
        return exercise_json

    def _default_keys(self, json_list):
        list_keys = set()
        none_keys = set()
        for dict_obj in json_list:
            for key in dict_obj.keys():
                if isinstance(dict_obj[key], list):
                    list_keys.add(key)
                else:
                    none_keys.add(key)
        for dict_obj in json_list:
            for key in list_keys:
                if key not in dict_obj:
                    dict_obj[key] = []
            for key in none_keys:
                if key not in dict_obj:
                    dict_obj[key] = None

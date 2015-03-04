
from django.conf import settings
from exercise_library.cloud_search.cloud_search_searcher import CloudSearchSearcher


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
        if 'exercises' in cls._cls_cache:
            del cls._cls_cache["exercises"]

    def _fetch_exercises(self):
        query_string = "(not video_id: 'thiswillneverhappen')"
        exercise_json = self._cloud_search_searcher.execute_query_string(query_string)
        self._make_ints(exercise_json)
        self._default_keys(exercise_json)
        return exercise_json

    def _make_ints(self, json_item):
        if isinstance(json_item, list):
            for index in xrange(len(json_item)):
                try:
                    json_item[index] = int(json_item[index])
                except (TypeError, ValueError):
                    self._make_ints(json_item[index])
        if isinstance(json_item, dict):
            for key in json_item.keys():
                try:
                    json_item[key] = int(json_item[key])
                except:
                    self._make_ints(json_item[key])

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

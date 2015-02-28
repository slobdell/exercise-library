from .abstract_cloud_search_document import AbstractCloudSearchDocument


class ExerciseDocument(AbstractCloudSearchDocument):

    def __init__(self, exercise_dict):
        self.exercise_dict = exercise_dict

    @property
    def cloud_search_id(self):
        return self.exercise_dict["id"]

    def to_cloud_search_json(self):
        exclude_fields = (
            "gfy_name",
        )
        return {k: v for k, v in self.exercise_dict.items() if k not in exclude_fields}

import os
import json

from boto import dynamodb2
from boto.dynamodb2.table import Table

TABLE_NAME = "exercise-library-exercises"
REGION = "us-east-1"


class DynamoClient(object):
    conn = dynamodb2.connect_to_region(
        REGION,
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY'],
    )
    table = Table(
        TABLE_NAME,
        connection=conn
    )

    def get_exercises(self):
        results = self.table.query_2(exercises__eq="0")
        exercise_json = [dict(item.items()) for item in results][0]
        exercises = json.loads(exercise_json["data"])
        return exercises

    def save_exercises(self, exercise_list):
        with self.table.batch_write() as table_batch:
            required_hash_data = {
                "exercises": "0"
            }
            write_data = {
                "data": json.dumps(exercise_list)
            }
            final_dynamo_data = dict(required_hash_data.items() + write_data.items())
            table_batch.put_item(data=final_dynamo_data)

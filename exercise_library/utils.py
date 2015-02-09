import json


def read_file(file_path, mode="r"):
    with open(file_path, mode=mode) as fptr:
        return fptr.read()


def read_file_as_json(file_path, mode="r"):
    return json.loads(read_file(file_path, mode=mode))


def base_round(x, base=5):
    return int(base * round(float(x) / base))

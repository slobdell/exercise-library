import json


def read_file(file_path, mode="r"):
    with open(file_path, mode=mode) as fptr:
        return fptr.read()


def read_file_as_json(file_path, mode="r"):
    return json.loads(read_file(file_path, mode=mode))


def base_round(x, base=5):
    return int(base * round(float(x) / base))


def make_ints(json_item):
    '''
    All data passed between networks are strings.  This will cast to ints
    as available
    '''
    if isinstance(json_item, list):
        for index in xrange(len(json_item)):
            try:
                json_item[index] = int(json_item[index])
            except (TypeError, ValueError):
                make_ints(json_item[index])
    if isinstance(json_item, dict):
        for key in json_item.keys():
            try:
                json_item[key] = int(json_item[key])
            except:
                make_ints(json_item[key])

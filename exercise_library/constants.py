# SBL THIS IS A COPY OF THE FILE IN THE WORKOUT GENERATOR APP, KEEP THIS IN
# MIND

import os
import random

from collections import defaultdict
from storages.backends.s3boto import S3BotoStorage


from exercise_library.utils import base_round
from exercise_library.utils import read_file_as_json


class Exercise(object):

    class _Exercise(object):

        def __init__(self, dict_obj):
            self.json_fields = []
            for key, value in dict_obj.items():
                self.json_fields.append(key)
                setattr(self, key, value)

        def to_json(self):
            json_blob = {}
            for field in self.json_fields:
                json_blob[field] = getattr(self, field)
            return json_blob

        def __hash__(self):
            return self.id

    _exercises = [_Exercise(dict_obj) for dict_obj in read_file_as_json("exercise_library/exercises.json")]

    _exercises_by_workout_component = defaultdict(set)
    _exercises_by_muscle_group = defaultdict(set)
    _exercises_by_fitness_level = defaultdict(set)
    _exercises_by_experience = defaultdict(set)
    _exercises_by_required_equipment = defaultdict(set)
    _exercises_by_type = defaultdict(set)
    _exercises_by_phase = defaultdict(set)
    _exercises_by_id = {}

    _exercise_id_to_mutually_exclusive_set = {e.id: set() for e in _exercises}

    for e in _exercises:
        _exercises_by_workout_component[e.workout_component_id].add(e)
        _exercises_by_muscle_group[e.muscle_group_id].add(e)
        _exercises_by_fitness_level[e.min_fitness_level_id].add(e)
        _exercises_by_experience[e.min_experience_id].add(e)
        _exercises_by_id[e.id] = e

        required_equipment_key = tuple(sorted(e.equipment_ids))
        _exercises_by_required_equipment[required_equipment_key].add(e)

        for exercise_type_id in e.exercise_type_ids:
            _exercises_by_type[exercise_type_id].add(e)

        for phase_id in e.phase_ids:
            _exercises_by_phase[phase_id].add(e)

    for e in sorted(_exercises, key=lambda e: e.mutually_exclusive):
        if e.mutually_exclusive:
            _exercise_id_to_mutually_exclusive_set[e.id] = _exercise_id_to_mutually_exclusive_set[e.mutually_exclusive]

    for e in _exercises:
        _exercise_id_to_mutually_exclusive_set[e.id].add(e.id)

    @classmethod
    def get_by_id(cls, id):
        return cls._exercises_by_id[id]

    def __init__(self, existing_query=None):
        if existing_query is None:
            self.query = set(self._exercises)
        else:
            self.query = existing_query

    def copy(self):
        return Exercise(existing_query=self.query.copy())

    def discard_exercise_id(self, exercise_id):
        exercise = Exercise.get_by_id(exercise_id)
        self.query.discard(exercise)
        return self

    def discard_mutually_exclusive(self, exercise_id):
        all_mutually_exclusive_ids = self._exercise_id_to_mutually_exclusive_set[exercise_id]
        for exercise_id in all_mutually_exclusive_ids:
            self.discard_exercise_id(exercise_id)
        return self

    def discard_muscle_group_id(self, muscle_group_id):
        self.query -= self._exercises_by_muscle_group[muscle_group_id]
        return self

    def restrict_to_muscle_group_ids(self, muscle_group_ids):
        exercises_for_muscle_groups = set()
        for muscle_group_id in muscle_group_ids:
            exercises_for_muscle_groups |= self._exercises_by_muscle_group[muscle_group_id]
        self.query &= exercises_for_muscle_groups
        return self

    def compound_only(self):
        self.query = {e for e in self.query if e.compound}
        return self

    def for_exercise_type(self, exercise_type_id):
        self.query = set.intersection(self.query, self._exercises_by_type[exercise_type_id])
        return self

    def for_phase(self, phase_id):
        self.query = set.intersection(self.query, self._exercises_by_phase[phase_id])
        return self

    def for_equipment_list(self, equipment_id_list):
        equipment_id_set = set(equipment_id_list)
        possible_equipment_keys = []
        for tuple_key in self._exercises_by_required_equipment.keys():
            can_use = True
            for equipment_id in tuple_key:
                if equipment_id not in equipment_id_set:
                    can_use = False
            if can_use:
                possible_equipment_keys.append(tuple_key)

        possible_exercises = set()
        for tuple_key in possible_equipment_keys:
            possible_exercises = set.union(possible_exercises, self._exercises_by_required_equipment[tuple_key])
        self.query = set.intersection(self.query, possible_exercises)
        return self

    def for_workout_component(self, workout_component_id):
        self.query = set.intersection(self.query, self._exercises_by_workout_component[workout_component_id])
        return self

    def for_muscle_group(self, muscle_group_id):
        self.query = set.intersection(self.query, self._exercises_by_muscle_group[muscle_group_id])
        return self

    def exclude_muscle_groups(self, muscle_group_id_list):
        for muscle_group_id in muscle_group_id_list:
            self.query = self.query - self._exercises_by_muscle_group[muscle_group_id]
        return self

    def for_fitness_level(self, fitness_level_id):
        all_fitness_levels = self._exercises_by_fitness_level.keys()
        valid_fitness_levels = [f for f in all_fitness_levels if f <= fitness_level_id]

        possible_exercises = set()
        for fitness_level in valid_fitness_levels:
            possible_exercises = set.union(self._exercises_by_fitness_level[fitness_level], possible_exercises)
        self.query = set.intersection(self.query, possible_exercises)
        return self

    def for_experience(self, experience_id):
        all_experiences = self._exercises_by_experience.keys()
        valid_experiences = [e for e in all_experiences if e <= experience_id]

        possible_exercises = set()
        for experience_level in valid_experiences:
            possible_exercises = set.union(self._exercises_by_experience[experience_level], possible_exercises)
        self.query = set.intersection(self.query, possible_exercises)
        return self

    def as_json(self):
        return [e.to_json() for e in self.query]

    def count(self):
        return len(self.query)


class MuscleGroup(object):
    # id, muscle_group_name, related
    VALUES = (
        (1, "Upper Back", 29),
        (2, "Lats", 1),
        (3, "Lower Back", 2),
        (29, "Traps", 3),

        (4, "Front Neck", 6),
        (5, "Rear Neck", 4),
        (6, "SCM", 5),

        (7, "Upper Abs", 28),
        (8, "Center Abs", 7),
        (9, "Transverse Abs", 8),
        (10, "Obliques", 9),
        (28, "Lower Abs", 10),

        (11, "Front Deltoids", 13),
        (12, "Medial Deltoids", 11),
        (13, "Rear Deltoids", 12),

        (14, "Biceps", 16),
        (15, "Triceps", 14),
        (16, "Forearms", 15),

        (17, "Hamstring", 27),
        (18, "Quads", 17),
        (19, "Calves", 18),
        (20, "Shins", 19),
        (21, "Glutes", 20),
        (22, "Hip Flexors", 24),
        (27, "Triple Extension", 21),

        (23, "Abductors", 22),
        (24, "Adductors", 23),

        (25, "Upper Chest", 26),
        (26, "Lower Chest", 25),

        (30, "Total Body", 30),
    )

    ALLOWABLE_RELATED_FOR_SUPERSETS = {
        # certain leg muscle can superset to triple extension
        17: [27],
        18: [27],
        21: [27],

        # chest can be upper or lower
        25: [26],
        26: [25],

        # front and rear delts
        11: [12],
        12: [11],
    }

    @classmethod
    def as_json(cls):
        json_list = []
        list_of_sets = cls.get_rings()
        clump_id_to_set = {i: id_set for i, id_set in enumerate(list_of_sets)}
        for tuple_obj in cls.VALUES:
            for clump_id, muscle_set in clump_id_to_set.items():
                if tuple_obj[0] in muscle_set:
                    break
            json_list.append({
                "id": tuple_obj[0],
                "title": tuple_obj[1],
                "clump_id": clump_id,
            })
        return json_list

    @classmethod
    def get_related_muscle_group_ids(cls, muscle_group_id):
        list_of_sets = cls.get_rings()
        for muscle_group_id_set in list_of_sets:
            if muscle_group_id in muscle_group_id_set:
                return [id for id in muscle_group_id_set]
        return []

    @classmethod
    def get_rings(cls):
        accounted_for_muscle_tuples = set()
        id_to_muscle_tuple = {t[0]: t for t in cls.VALUES}

        muscle_tuple = None
        muscle_rings = []
        tuple_buffer = []
        while True:
            if muscle_tuple is None:
                for muscle_tuple in cls.VALUES:
                    if muscle_tuple not in accounted_for_muscle_tuples:
                        break
                else:  # everything accounted for
                    break
            else:
                if muscle_tuple in tuple_buffer:
                    muscle_tuple = None
                    muscle_rings.append(tuple_buffer)
                    tuple_buffer = []
                    continue

                tuple_buffer.append(muscle_tuple)
                accounted_for_muscle_tuples.add(muscle_tuple)
                related_id = muscle_tuple[-1]
                muscle_tuple = id_to_muscle_tuple[related_id]

        rings = []
        for muscle_list in muscle_rings:
            muscle_ids = [tuple_obj[0] for tuple_obj in muscle_list]
            rings.append(set(muscle_ids))
        return rings


class MuscleFrequency(object):
    '''
    Otherwise this generically applies to everything.  But holy shit, this sucks

    applies generically to all muscle group allegedly '''
    # id, name, minimum, maximum, minSets, maxSets, minReps, maxReps, weekLength
    VALUES = (
        (1, "Low", 2, 4, 1, 2, 15, 20, 7),
        (2, "Low-Mid", 2, 3, 2, 3, 12, 20, 7),
        (3, "Mid", 2, 2, 3, 4, 6, 15, 7),
        (4, "Mid-High", 1, 1, 3, 5, 4, 12, 4),
        (5, "High", 1, 1, 1, 6, 1, 6, 5),
    )
    '''
    FOREARMS apparently
    (6, "Low", 1, 1, 1, 2, 15, 20, 7, 1),
    (7, "Low-Mid", 1, 1, 2, 3, 12, 20, 7, 1),
    (8, "Mid", 1, 1, 3, 4, 6, 15, 7, 1),
    (9, "Mid-High", 1, 1, 3, 5, 4, 12, 7, 1),
    (10, "High", 1, 1, 1, 6, 1, 6, 7, 1),
    '''

    @classmethod
    def get_max_period(cls):
        max_period = 0
        for f_tuple in cls.VALUES:
            period = f_tuple[8]
            if period > max_period:
                max_period = period
        return max_period

    @classmethod
    def get_min_period(cls):
        min_period = cls.get_max_period() + 1
        for f_tuple in cls.VALUES:
            period = f_tuple[8]
            if period < min_period:
                min_period = period
        return min_period

    @classmethod
    def pass_fail(cls, rep_prescriptions, times_worked_this_period, period):
        for f_tuple in cls.VALUES:
            min_reps = f_tuple[6]
            max_reps = f_tuple[7]
            period_length = f_tuple[8]
            if period > period_length:
                continue
            for reps in rep_prescriptions:
                if min_reps <= reps <= max_reps:
                    max_times_per_period = f_tuple[3]
                    if times_worked_this_period >= max_times_per_period:
                        return False
        return True

    @classmethod
    def get_max_times_per_period(cls, average_sets, average_reps):
        possible_times_per_period = []
        for f_tuple in cls.VALUES:
            # min_sets = f_tuple[4]
            max_sets = f_tuple[5]

            # min_reps = f_tuple[6]
            max_reps = f_tuple[7]
            if average_sets <= max_sets and average_reps <= max_reps:
                # minimum = f_tuple[2]
                maximum = f_tuple[3]
                period = f_tuple[8]
                possible_times_per_period.append((maximum, period))

        if len(possible_times_per_period) == 0:
            default = (1, 7)
            return default
        best_maximum = 0
        best_index = 0
        for index, (maximum, period) in enumerate(possible_times_per_period):
            if maximum > best_maximum:
                best_maximum = maximum
                best_index = index
        return possible_times_per_period[best_index]


class WorkoutComponent(object):
    # id, name
    VALUES = (
        (1, "Flexibility"),
        (2, "Core"),
        (3, "Balance"),
        (4, "Reactive"),
        (5, "Resistance"),
    )
    FLEXIBILITY = 1
    CORE = 2
    BALANCE = 3
    REACTIVE = 4
    RESISTANCE = 5

    WORKOUT_ORDER = (
        BALANCE,
        REACTIVE,
        RESISTANCE,
        CORE,
        FLEXIBILITY
    )

    def __init__(self, value_tuple):
        self.id = value_tuple[0]
        self.title = value_tuple[1]

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title
        }

    def get_rest(self, phase):
        if self.id == self.FLEXIBILITY:
            return 0
        if self.id in (self.CORE, self.BALANCE, self.REACTIVE):
            return 45
        if self.id == self.RESISTANCE:
            return phase.rest

    @classmethod
    def get_all_ids(cls):
        return [t[0] for t in cls.VALUES]

    @classmethod
    def get_by_id(cls, id):
        for tuple_obj in cls.VALUES:
            if tuple_obj[0] == id:
                return WorkoutComponent(tuple_obj)


class ExerciseType(object):
    # id, name
    VALUES = (
        (1, "Strength"),
        (2, "Power"),
        (3, "Stabilization"),
        (4, "Stretch"),
    )
    STRENGTH = 1
    POWER = 2
    STABILIZATION = 3
    STRETCH = 4

    @classmethod
    def as_json(cls):
        json_list = []
        for tuple_obj in cls.VALUES:
            json_list.append({
                "id": tuple_obj[0],
                "title": tuple_obj[1],
            })
        return json_list


class Equipment(object):
    # id, name
    IMG_PATH = "img/weight_equipment/%s.jpg"
    VALUES = (
        (1, "Dumbells", IMG_PATH % "dumbbells"),
        (2, "Barbells", IMG_PATH % "barbell"),
        (3, "Kettle Bells", IMG_PATH % "kettle_bells"),
        (4, "Olympic Lifting Capability", IMG_PATH % "olympic_lifting_capability"),
        (5, "Pull Up Bar", IMG_PATH % "pull_up_bar"),
        (6, "Resistive Band/Tubing", IMG_PATH % "resistive_band_tubing"),
        (7, "Medicine Ball", IMG_PATH % "medicine_ball"),
        (8, "Swiss Ball", IMG_PATH % "swiss_ball"),
        (9, "Cable Suite", IMG_PATH % "cable_suite"),
        (10, "Full Machine Suite", IMG_PATH % "machine_suite"),
        (11, "Hammer Strength Suite", IMG_PATH % "hammer_strength_suite"),
        (20, "Smith Machine", IMG_PATH % "smith_machine"),
        (21, "Bench", IMG_PATH % "bench"),
        (22, "Bosu Ball", IMG_PATH % "bosu_ball"),
        (24, "Rings", IMG_PATH % "rings"),
    )

    DEFAULT_IDS = (
        1, 2, 5, 10, 20, 21
    )

    @classmethod
    def as_json(cls):
        json_data = []
        for equipment_tuple in cls.VALUES:
            json_data.append({
                "id": equipment_tuple[0],
                "title": equipment_tuple[1],
                "image": S3BotoStorage().url(equipment_tuple[2]) if not os.environ.get("I_AM_IN_DEV_ENV") else "/static/%s" % equipment_tuple[2],
            })
        return json_data


class Tempo(object):
    VALUES = (
        (1, "4-2-1", 7),
        (2, "2-2-0", 4),
        (3, "0-0-0", 3),
    )
    DESCRIPTION = "This is the speed at which the exercise is performed.  There are 3 basic portions of a lift, the lowering of the weight, the lifting of the weight, and the moment in-between.  " + \
        "You'll see a tempo displayed as 4-2-1, 2-2-0, or 0-0-0.  The first number is the lowering of the weight, the second is the lifting of the weight, and the last is that moment in-between. " + \
        "It is very important that you do not rush your lifts and that you execute to the tempo prescribed as it aids in the adaptation we're trying to elicit from your body.  When you see a '0 in " + \
        "the last position, that means there is no pause in the lift.  When you see 0-0-0, that means you are executing the lift as quickly as you can control the weight.  Uncontrolled speed leads to " + \
        "injuries - so never attempt to lift at a speed faster than you can safely control the weight.\n\n\nExamples:\n\nWhen doing a bench press to a 4-2-1 tempo, that means you'll lower " + \
        "it your chest to a full 4 seconds, pause just off your chest for a full second, and then lift the weight to a full 2 seconds.  Whereas a 2-2-0 means that you'll lower the weight to a full 2 " + \
        "seconds and then lift the weight to a full 2 seconds with no pause in-between.  \n\n\nWhen doing a squat to a 4-2-1 tempo, you'll be lowering for a full 4 seconds, pause for a full second " + \
        "at the bottom, and return to a stand for a full 2 seconds.  For a 2-2-0 tempo, you'll be lowering yourself for a full two seconds and then return to a stand over a full 2 seconds.\n\n\nWhen " + \
        "doing a bicep curl to a 4-2-1 tempo, you'll start with your arms extended and lift the weight over a 2 second period, pause for a full second at the top, and then lower the weight over a " + \
        "4 second period.  For a 2-2-0 tempo, you'll lift over a full 2 seconds and then lower over a full 2 seconds - no pause in the lift.\n\n\nNotes:\n\n\nWe keep saying a 'full' number of " + \
        "seconds because people have a tendency to short change themselves and count quicker than they should - especially towards the end of a set and they are fatiguing.  Be sure to count in " + \
        "a fashion that helps you keep it long such as '1 Mississippi' or '1 one thousand.' \n\n\nWhen you pause in a lift, its just that, a pause not a rest.  Don't rest the weight on your chest, " + \
        "shoulders, rack, whatever.  You want to still be contracting your muscles to hold the weight during that portion of the lift.  To be even a little more intense, you can attempt to squeeze " + \
        "your muscles as hard as you can for that second as you hold the weight.\n\n\nIf you want to know the technical terms for them, the three portions of the lift are the eccentric (lowering) " + \
        ", concentric (lifting), and isometric (the pause)."

    MAP = {t[0]: t for t in VALUES}

    def __init__(self, tuple_data):
        self.id = tuple_data[0]
        self.display_string = tuple_data[1]
        self.seconds_per_rep = tuple_data[2]

    def to_json(self):
        return {
            "id": self.id,
            "title": self.display_string
        }

    @classmethod
    def get_by_id(cls, id):
        return cls(cls.MAP[id])


class Phase(object):
    # id, name, tempo_id, rest, description_id
    VALUES = (
        (1, "Stabilization", 1, 30, "Using a combination of supported and unsupported exercises this phase keeps your muscles under constant, but varied tension.  This results in the adaptation of muscle endurance and also furthers your postural stability and control."),
        (2, "Muscle Endurance", 2, 45, "Need to write a description for muscle endurance"),
        (3, "Hypertrophy", 2, 60, "The purpose here is to grow the size of the muscle itself, thus increasing its potential for strength gains and also increasing its caloric consumption for those keenly interested in fat loss.  This is the style of lifting most people are familiar with and associate the easiest with \"traditional\" weight lifting."),
        (4, "Maximal Strength", 3, 240, "Through heavy loads and low reps, the body adapts to recruit more motor units and results in being able to lift more weight."),
        (5, "Power", 3, 120, "By combining high loads and high velocity in order to increase your overall power.  Power training allows for you to get faster, stronger, and depending on your diet - either bigger or leaner.  This is due to the large amount of neural and muscle fiber recruitment needed to complete these movements in succession."),
    )
    '''
    There's also a first time description for each Phase
    stab: 21
    muscle endurance: 22
    power: 25
    maximal strength: 24
    hypertrophy: 23
    '''
    STABILIZATION = 1
    MUSCLE_ENDURANCE = 2
    HYPERTROPHY = 3
    MAXIMAL_STRENGTH = 4
    POWER = 5

    SUPERSET_PHASES = {MUSCLE_ENDURANCE, POWER}

    MAP = {t[0]: t for t in VALUES}

    def __init__(self, tuple_obj):
        self.id = tuple_obj[0]
        self.title = tuple_obj[1]
        self.tempo = Tempo.get_by_id(tuple_obj[2])
        self.rest = tuple_obj[3]
        self.description = tuple_obj[4]

    def to_json(self):
        return {
            "title": self.title,
            "tempo": self.tempo.to_json(),
            "description": self.description
        }

    @classmethod
    def get_by_id(cls, id):
        return cls(cls.MAP[id])

    @classmethod
    def get_by_id_as_json(cls, id):
        return cls.get_by_id(id).to_json()


class CardioType(object):
    # id, name, minimum_times_per_week
    VALUES = (
        (1, "Endurance Focused", 6),
        (2, "Athlete/Performance Focused", 3),
        (3, "General/Fat Loss", 4),
        (4, "Bodybuilding", 2),
        (5, "Powerlifting/Strongman", 1),
    )

    MAP = {t[0]: t for t in VALUES}

    def __init__(self, tuple_obj):
        self.id = tuple_obj[0]
        self.title = tuple_obj[1]
        self.min_times_per_week = tuple_obj[2]

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "min_times_per_week": self.min_times_per_week
        }

    @classmethod
    def get_by_id(cls, id):
        return CardioType(cls.MAP[id])

    @classmethod
    def get_by_id_as_json(cls, id):
        return cls.get_by_id(id).to_json()


class CardioMax(object):

    # id, fitnessLevel_id, cardioType_id, loMaximum, medMaximum, hiMaximum
    VALUES = (
        (1, 1, 1, 5, 2, 0),
        (2, 1, 2, 5, 2, 0),
        (3, 1, 3, 5, 1, 0),
        (4, 1, 4, 5, 1, 0),
        (5, 1, 5, 5, 0, 0),
        (6, 2, 1, 5, 2, 0),
        (7, 2, 2, 5, 2, 0),
        (8, 2, 3, 5, 1, 0),
        (9, 2, 4, 5, 1, 0),
        (10, 2, 5, 5, 0, 0),
        (11, 3, 1, 6, 2, 1),
        (12, 3, 2, 6, 2, 0),
        (13, 3, 3, 5, 1, 1),
        (14, 3, 4, 5, 1, 0),
        (15, 3, 5, 6, 0, 0),
        (16, 4, 1, 6, 3, 2),
        (17, 4, 2, 6, 2, 1),
        (18, 4, 3, 6, 1, 1),
        (19, 4, 4, 6, 2, 0),
        (20, 4, 5, 6, 1, 0),
        (21, 5, 1, 6, 3, 2),
        (22, 5, 2, 6, 2, 1),
        (23, 5, 3, 6, 1, 1),
        (24, 5, 4, 6, 2, 0),
        (25, 5, 5, 6, 1, 0),
    )
    MAP = {(t[1], t[2]): (t[3], t[4], t[5]) for t in VALUES}

    @classmethod
    def get_values_from_fitness_level_cardio_type(cls, fitness_level_id, cardio_type_id):
        key = (fitness_level_id, cardio_type_id)
        return cls.MAP[key]


class CardioZone(object):
    '''
    Query by level and zone
    '''
    def __init__(self, tuple_data):
        self.id = tuple_data[0]
        self.level = tuple_data[1]
        self.zone = tuple_data[2]

        min_interval = tuple_data[3]
        max_interval = tuple_data[4]
        self.interval = random.random() * (max_interval - min_interval) + min_interval
        if self.interval < 1.0:
            # round to nearest 5 seconds
            seconds = self.interval * 60
            seconds = base_round(seconds, base=5)
            self.interval = float(seconds) / 60
        else:
            self.interval = float(int(self.interval))

        min_previous = tuple_data[5]
        max_previous = tuple_data[6]
        self.previous = random.random() * (max_previous - min_previous) + min_previous
        if self.previous < 1.0:
            seconds = self.previous * 60
            seconds = base_round(seconds, base=5)
            self.previous = float(seconds) / 60
        else:
            self.previous = float(int(self.previous))

        self.min_heart_rate = tuple_data[7]
        self.max_heart_rate = tuple_data[8]

        self.total_time = tuple_data[9]
        self.max_overall = tuple_data[10]

        self.cardio_types = tuple_data[11]
        self.fitness_levels = tuple_data[12]

    ALL_CARDIO_TYPES = (1, 2, 3, 4, 5)
    NOT_FOR_STRONGMAN = (1, 2, 3, 4)
    NOT_FOR_BODYBUILDER = (1, 2, 3)

    LOW_FITNESS_LEVELS = (1, 2)
    MEDIUM_FITNESS_LEVELS = (3, 4)
    HIGH_FITNESS_LEVELS = (5, )

    # id, level, zone, minInterval, maxInterval, minPrevious, maxPrevious,
    # minHeartRate (percent), maxHeartRate (percent), totalTimeThisZone, maxOverall
    VALUES = (
        (1, 1, 1, 20, 20, 0, 0, 65, 75, 20, 20, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (2, 1, 2, 1, 2, 4, 8, 80, 85, 12, 20, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),

        (5, 2, 1, 21, 30, 0, 0, 65, 75, 30, 30, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (6, 2, 2, 1, 4, 4, 8, 80, 85, 16, 35, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (7, 2, 2, 4, 6, 2, 4, 80, 85, 14, 30, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (8, 2, 3, 0.15, 0.25, 2, 6, 86, 90, 3, 35, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),

        (9, 3, 1, 30, 45, 0, 0, 65, 75, 45, 45, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (10, 3, 2, 2, 6, 4, 8, 80, 85, 24, 40, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (11, 3, 2, 6, 8, 1, 3, 80, 85, 16, 25, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),
        (12, 3, 3, 0.25, 0.5, 2, 6, 86, 90, 6, 35, ALL_CARDIO_TYPES, LOW_FITNESS_LEVELS),

        (13, 1, 1, 20, 30, 0, 0, 65, 75, 30, 30, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (14, 1, 2, 1, 3, 2, 6, 80, 85, 16, 35, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (15, 1, 2, 6, 8, 2, 3, 80, 85, 8, 13, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),

        (17, 2, 1, 31, 45, 0, 0, 65, 75, 45, 45, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (18, 2, 2, 1, 4, 2, 6, 80, 85, 24, 40, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (19, 2, 2, 9, 12, 2, 3, 80, 85, 12, 17, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (20, 2, 3, 0.15, 0.333, 2, 8, 86, 90, 5, 40, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),

        (21, 3, 1, 45, 60, 0, 0, 65, 75, 60, 60, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (22, 3, 2, 2, 5, 2, 6, 80, 85, 32, 45, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (23, 3, 2, 12, 18, 2, 3, 80, 85, 18, 23, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),
        (24, 3, 3, 0.33, 0.75, 2, 8, 86, 90, 10, 45, NOT_FOR_STRONGMAN, MEDIUM_FITNESS_LEVELS),

        (25, 1, 1, 30, 45, 0, 0, 65, 75, 45, 45, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (26, 1, 2, 1, 3, 1, 4, 80, 85, 16, 30, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (27, 1, 2, 8, 12, 2, 3, 80, 85, 12, 17, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (28, 1, 3, 0.1, 0.25, 1, 3, 86, 90, 3, 20, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),

        (29, 2, 1, 45, 60, 0, 0, 65, 75, 60, 60, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (30, 2, 2, 2, 6, 1, 4, 80, 85, 24, 50, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (31, 2, 2, 12, 18, 2, 3, 80, 85, 18, 23, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (32, 2, 3, 0.25, 0.5, 1, 4, 86, 90, 7, 40, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),

        (33, 3, 1, 60, 90, 0, 0, 65, 75, 90, 90, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (34, 3, 2, 3, 7, 1, 4, 80, 85, 35, 60, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (35, 3, 2, 18, 25, 2, 3, 80, 85, 25, 30, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
        (36, 3, 3, 0.5, 1, 1, 3, 86, 90, 15, 55, NOT_FOR_BODYBUILDER, HIGH_FITNESS_LEVELS),
    )

    MAP = defaultdict(list)
    for t in VALUES:
        key = (t[1], t[2])
        data = t
        MAP[key].append(data)

    ID_MAP = {t[0]: t for t in VALUES}

    @classmethod
    def get_by_id(cls, id):
        data = cls.ID_MAP[id]
        return CardioZone(data)

    @classmethod
    def query_by_restricted_ids(cls, level, zone, possible_cardio_zone_ids):
        '''
        Ignores CardioType and FitnessLevel
        '''
        if not possible_cardio_zone_ids:
            return None
        possible_tuples = cls.MAP[(level, zone)]
        possible_tuples = [t for t in possible_tuples if t[0] in possible_cardio_zone_ids]
        return [CardioZone(t) for t in possible_tuples]

    @classmethod
    def query(cls, level, zone, cardio_type_id, fitness_level):
        possible_tuples = cls.MAP[(level, zone)]
        possible_zones = [CardioZone(t) for t in possible_tuples]
        possible_zones = [cz for cz in possible_zones if cardio_type_id in cz.cardio_types]
        possible_zones = [cz for cz in possible_zones if fitness_level in cz.fitness_levels]
        return possible_zones


class HardcodedRule(object):
    # id, cardioType_id, phase_id, cardioZone_id
    LOW_FITNESS_CARDIO_ZONES = tuple(range(1, 12 + 1))
    MEDIUM_FITNESS_CARDIO_ZONES = tuple(range(12, 24 + 1))
    VALUES = (
        (1, 4, 3, LOW_FITNESS_CARDIO_ZONES),
        (2, 2, 4, LOW_FITNESS_CARDIO_ZONES),
        (3, 2, 5, LOW_FITNESS_CARDIO_ZONES),
        (4, 4, 4, LOW_FITNESS_CARDIO_ZONES),
        (5, 4, 5, LOW_FITNESS_CARDIO_ZONES),
        (6, 4, 1, MEDIUM_FITNESS_CARDIO_ZONES),
        (7, 4, 2, MEDIUM_FITNESS_CARDIO_ZONES),
        (8, 2, 3, MEDIUM_FITNESS_CARDIO_ZONES),
        (9, 5, 1, LOW_FITNESS_CARDIO_ZONES),
        (10, 5, 2, LOW_FITNESS_CARDIO_ZONES),
        (11, 5, 3, LOW_FITNESS_CARDIO_ZONES),
        (12, 5, 4, LOW_FITNESS_CARDIO_ZONES),
        (13, 5, 5, LOW_FITNESS_CARDIO_ZONES),
    )

    MAP = {(t[1], t[2]): t[3] for t in VALUES}

    @classmethod
    def get_by_cardio_type_phase(cls, cardio_type_id, phase_id):
        key = (cardio_type_id, phase_id)
        return cls.MAP.get(key)


class WorkoutComponentFrequency(object):
    '''
    Filter by phase, workout component, fitness level, week
    '''
    # id, minimum, maximum, phase_id, currentFitnessLevel_id, workoutComponent_id, week
    VALUES = (
        (1, 7, 7, 1, 1, 1, 1),
        (2, 7, 7, 1, 1, 1, 2),
        (3, 7, 7, 1, 1, 1, 3),
        (4, 7, 7, 1, 1, 1, 4),
        (5, 7, 7, 1, 1, 1, 5),
        (6, 7, 7, 1, 1, 1, 6),
        (7, 7, 7, 2, 1, 1, 1),
        (8, 7, 7, 2, 1, 1, 2),
        (9, 7, 7, 2, 1, 1, 3),
        (10, 7, 7, 2, 1, 1, 4),
        (11, 7, 7, 2, 1, 1, 5),
        (12, 7, 7, 2, 1, 1, 6),
        (13, 7, 7, 3, 1, 1, 1),
        (14, 7, 7, 3, 1, 1, 2),
        (15, 3, 7, 3, 1, 1, 3),
        (16, 7, 7, 3, 1, 1, 4),
        (17, 7, 7, 3, 1, 1, 5),
        (18, 7, 7, 3, 1, 1, 6),
        (19, 7, 7, 4, 1, 1, 1),
        (20, 7, 7, 4, 1, 1, 2),
        (21, 7, 7, 4, 1, 1, 3),
        (22, 7, 7, 4, 1, 1, 4),
        (23, 7, 7, 4, 1, 1, 5),
        (24, 7, 7, 4, 1, 1, 6),
        (25, 7, 7, 5, 1, 1, 1),
        (26, 7, 7, 5, 1, 1, 2),
        (27, 7, 7, 5, 1, 1, 3),
        (28, 7, 7, 5, 1, 1, 4),
        (29, 7, 7, 5, 1, 1, 5),
        (30, 7, 7, 5, 1, 1, 6),
        (31, 2, 2, 1, 1, 2, 1),
        (32, 2, 2, 1, 1, 2, 2),
        (33, 2, 3, 1, 1, 2, 3),
        (34, 3, 3, 1, 1, 2, 4),
        (35, 4, 4, 1, 1, 2, 5),
        (36, 4, 4, 1, 1, 2, 6),
        (37, 3, 3, 2, 1, 2, 1),
        (38, 3, 3, 2, 1, 2, 2),
        (39, 3, 3, 2, 1, 2, 3),
        (40, 3, 4, 2, 1, 2, 4),
        (41, 4, 4, 2, 1, 2, 5),
        (42, 4, 4, 2, 1, 2, 6),
        (43, 3, 3, 3, 1, 2, 1),
        (44, 3, 3, 3, 1, 2, 2),
        (45, 3, 3, 3, 1, 2, 3),
        (46, 3, 3, 3, 1, 2, 4),
        (47, 3, 3, 3, 1, 2, 5),
        (48, 3, 3, 3, 1, 2, 6),
        (49, 2, 3, 4, 1, 2, 1),
        (50, 2, 3, 4, 1, 2, 2),
        (51, 2, 3, 4, 1, 2, 3),
        (52, 2, 3, 4, 1, 2, 4),
        (53, 2, 3, 4, 1, 2, 5),
        (54, 2, 3, 4, 1, 2, 6),
        (55, 2, 5, 5, 1, 2, 1),
        (56, 2, 5, 5, 1, 2, 2),
        (57, 2, 5, 5, 1, 2, 3),
        (58, 2, 5, 5, 1, 2, 4),
        (59, 2, 5, 5, 1, 2, 5),
        (60, 2, 5, 5, 1, 2, 6),
        (61, 2, 2, 1, 1, 3, 1),
        (62, 2, 2, 1, 1, 3, 2),
        (63, 2, 3, 1, 1, 3, 3),
        (64, 3, 3, 1, 1, 3, 4),
        (65, 4, 4, 1, 1, 3, 5),
        (66, 4, 4, 1, 1, 3, 6),
        (67, 3, 3, 2, 1, 3, 1),
        (68, 3, 3, 2, 1, 3, 2),
        (69, 3, 3, 2, 1, 3, 3),
        (70, 3, 4, 2, 1, 3, 4),
        (71, 4, 4, 2, 1, 3, 5),
        (72, 4, 4, 2, 1, 3, 6),
        (73, 3, 3, 3, 1, 3, 1),
        (74, 3, 3, 3, 1, 3, 2),
        (75, 3, 3, 3, 1, 3, 3),
        (76, 3, 3, 3, 1, 3, 4),
        (77, 3, 3, 3, 1, 3, 5),
        (78, 3, 3, 3, 1, 3, 6),
        (79, 2, 3, 4, 1, 3, 1),
        (80, 2, 3, 4, 1, 3, 2),
        (81, 2, 3, 4, 1, 3, 3),
        (82, 2, 3, 4, 1, 3, 4),
        (83, 2, 3, 4, 1, 3, 5),
        (84, 2, 3, 4, 1, 3, 6),
        (85, 1, 3, 5, 1, 3, 1),
        (86, 1, 3, 5, 1, 3, 2),
        (87, 1, 3, 5, 1, 3, 3),
        (88, 1, 3, 5, 1, 3, 4),
        (89, 1, 3, 5, 1, 3, 5),
        (90, 1, 3, 5, 1, 3, 6),
        (91, 2, 2, 1, 1, 4, 1),
        (92, 2, 2, 1, 1, 4, 2),
        (93, 2, 3, 1, 1, 4, 3),
        (94, 3, 3, 1, 1, 4, 4),
        (95, 4, 4, 1, 1, 4, 5),
        (96, 4, 4, 1, 1, 4, 6),
        (97, 3, 3, 2, 1, 4, 1),
        (98, 3, 3, 2, 1, 4, 2),
        (99, 3, 3, 2, 1, 4, 3),
        (100, 3, 4, 2, 1, 4, 4),
        (101, 4, 4, 2, 1, 4, 5),
        (102, 4, 4, 2, 1, 4, 6),
        (103, 3, 3, 3, 1, 4, 1),
        (104, 3, 3, 3, 1, 4, 2),
        (105, 3, 3, 3, 1, 4, 3),
        (106, 3, 3, 3, 1, 4, 4),
        (107, 3, 3, 3, 1, 4, 5),
        (108, 3, 3, 3, 1, 4, 6),
        (109, 2, 3, 4, 1, 4, 1),
        (110, 2, 3, 4, 1, 4, 2),
        (111, 2, 3, 4, 1, 4, 3),
        (112, 2, 3, 4, 1, 4, 4),
        (113, 2, 3, 4, 1, 4, 5),
        (114, 2, 3, 4, 1, 4, 6),
        (115, 1, 3, 5, 1, 4, 1),
        (116, 1, 3, 5, 1, 4, 2),
        (117, 1, 3, 5, 1, 4, 3),
        (118, 1, 3, 5, 1, 4, 4),
        (119, 1, 3, 5, 1, 4, 5),
        (120, 1, 3, 5, 1, 4, 6),
        (121, 3, 3, 1, 1, 5, 1),
        (122, 3, 3, 1, 1, 5, 2),
        (123, 3, 4, 1, 1, 5, 3),
        (124, 3, 4, 1, 1, 5, 4),
        (125, 3, 4, 1, 1, 5, 5),
        (126, 3, 5, 1, 1, 5, 6),
        (127, 3, 3, 2, 1, 5, 1),
        (128, 3, 3, 2, 1, 5, 2),
        (129, 3, 3, 2, 1, 5, 3),
        (130, 3, 4, 2, 1, 5, 4),
        (131, 3, 4, 2, 1, 5, 5),
        (132, 3, 5, 2, 1, 5, 6),
        (133, 3, 3, 3, 1, 5, 1),
        (134, 3, 3, 3, 1, 5, 2),
        (135, 3, 3, 3, 1, 5, 3),
        (136, 3, 4, 3, 1, 5, 4),
        (137, 3, 4, 3, 1, 5, 5),
        (138, 3, 4, 3, 1, 5, 6),
        (139, 3, 3, 4, 1, 5, 1),
        (140, 3, 3, 4, 1, 5, 2),
        (141, 3, 3, 4, 1, 5, 3),
        (142, 3, 4, 4, 1, 5, 4),
        (143, 3, 4, 4, 1, 5, 5),
        (144, 3, 4, 4, 1, 5, 6),
        (145, 3, 3, 5, 1, 5, 1),
        (146, 3, 3, 5, 1, 5, 2),
        (147, 3, 3, 5, 1, 5, 3),
        (148, 3, 3, 5, 1, 5, 4),
        (149, 3, 3, 5, 1, 5, 5),
        (150, 3, 3, 5, 1, 5, 6),
        (151, 7, 7, 1, 2, 1, 1),
        (152, 7, 7, 1, 2, 1, 2),
        (153, 7, 7, 1, 2, 1, 3),
        (154, 7, 7, 1, 2, 1, 4),
        (155, 7, 7, 1, 2, 1, 5),
        (156, 7, 7, 1, 2, 1, 6),
        (157, 7, 7, 2, 2, 1, 1),
        (158, 7, 7, 2, 2, 1, 2),
        (159, 7, 7, 2, 2, 1, 3),
        (160, 7, 7, 2, 2, 1, 4),
        (161, 7, 7, 2, 2, 1, 5),
        (162, 7, 7, 2, 2, 1, 6),
        (163, 7, 7, 3, 2, 1, 1),
        (164, 7, 7, 3, 2, 1, 2),
        (165, 7, 7, 3, 2, 1, 3),
        (166, 7, 7, 3, 2, 1, 4),
        (167, 7, 7, 3, 2, 1, 5),
        (168, 7, 7, 3, 2, 1, 6),
        (169, 7, 7, 4, 2, 1, 1),
        (170, 7, 7, 4, 2, 1, 2),
        (171, 7, 7, 4, 2, 1, 3),
        (172, 7, 7, 4, 2, 1, 4),
        (173, 7, 7, 4, 2, 1, 5),
        (174, 7, 7, 4, 2, 1, 6),
        (175, 7, 7, 5, 2, 1, 1),
        (176, 7, 7, 5, 2, 1, 2),
        (177, 7, 7, 5, 2, 1, 3),
        (178, 7, 7, 5, 2, 1, 4),
        (179, 7, 7, 5, 2, 1, 5),
        (180, 7, 7, 5, 2, 1, 6),
        (181, 2, 2, 1, 2, 2, 1),
        (182, 2, 2, 1, 2, 2, 2),
        (183, 2, 3, 1, 2, 2, 3),
        (184, 3, 3, 1, 2, 2, 4),
        (185, 4, 4, 1, 2, 2, 5),
        (186, 2, 4, 1, 2, 2, 6),
        (187, 3, 3, 2, 2, 2, 1),
        (188, 3, 3, 2, 2, 2, 2),
        (189, 3, 3, 2, 2, 2, 3),
        (190, 3, 3, 2, 2, 2, 4),
        (191, 4, 4, 2, 2, 2, 5),
        (192, 4, 4, 2, 2, 2, 6),
        (193, 3, 3, 3, 2, 2, 1),
        (194, 3, 3, 3, 2, 2, 2),
        (195, 3, 4, 3, 2, 2, 3),
        (196, 3, 4, 3, 2, 2, 4),
        (197, 3, 4, 3, 2, 2, 5),
        (198, 3, 4, 3, 2, 2, 6),
        (199, 2, 3, 4, 2, 2, 1),
        (200, 2, 3, 4, 2, 2, 2),
        (201, 2, 3, 4, 2, 2, 3),
        (202, 2, 3, 4, 2, 2, 4),
        (203, 2, 3, 4, 2, 2, 5),
        (204, 2, 3, 4, 2, 2, 6),
        (205, 2, 5, 5, 2, 2, 1),
        (206, 2, 5, 5, 2, 2, 2),
        (207, 2, 5, 5, 2, 2, 3),
        (208, 2, 5, 5, 2, 2, 4),
        (209, 2, 5, 5, 2, 2, 5),
        (210, 2, 5, 5, 2, 2, 6),
        (211, 2, 2, 1, 2, 3, 1),
        (212, 2, 2, 1, 2, 3, 2),
        (213, 2, 3, 1, 2, 3, 3),
        (214, 3, 3, 1, 2, 3, 4),
        (215, 4, 4, 1, 2, 3, 5),
        (216, 2, 4, 1, 2, 3, 6),
        (217, 3, 3, 2, 2, 3, 1),
        (218, 3, 3, 2, 2, 3, 2),
        (219, 3, 3, 2, 2, 3, 3),
        (220, 3, 3, 2, 2, 3, 4),
        (221, 4, 4, 2, 2, 3, 5),
        (222, 4, 4, 2, 2, 3, 6),
        (223, 3, 3, 3, 2, 3, 1),
        (224, 3, 3, 3, 2, 3, 2),
        (225, 3, 4, 3, 2, 3, 3),
        (226, 3, 4, 3, 2, 3, 4),
        (227, 3, 4, 3, 2, 3, 5),
        (228, 3, 4, 3, 2, 3, 6),
        (229, 2, 3, 4, 2, 3, 1),
        (230, 2, 3, 4, 2, 3, 2),
        (231, 2, 3, 4, 2, 3, 3),
        (232, 2, 3, 4, 2, 3, 4),
        (233, 2, 3, 4, 2, 3, 5),
        (234, 2, 3, 4, 2, 3, 6),
        (235, 1, 3, 5, 2, 3, 1),
        (236, 1, 3, 5, 2, 3, 2),
        (237, 1, 3, 5, 2, 3, 3),
        (238, 1, 3, 5, 2, 3, 4),
        (239, 1, 3, 5, 2, 3, 5),
        (240, 1, 3, 5, 2, 3, 6),
        (241, 2, 2, 1, 2, 4, 1),
        (242, 2, 2, 1, 2, 4, 2),
        (243, 2, 3, 1, 2, 4, 3),
        (244, 3, 3, 1, 2, 4, 4),
        (245, 4, 4, 1, 2, 4, 5),
        (246, 2, 4, 1, 2, 4, 6),
        (247, 3, 3, 2, 2, 4, 1),
        (248, 3, 3, 2, 2, 4, 2),
        (249, 3, 3, 2, 2, 4, 3),
        (250, 3, 3, 2, 2, 4, 4),
        (251, 4, 4, 2, 2, 4, 5),
        (252, 4, 4, 2, 2, 4, 6),
        (253, 3, 3, 3, 2, 4, 1),
        (254, 3, 3, 3, 2, 4, 2),
        (255, 3, 4, 3, 2, 4, 3),
        (256, 3, 4, 3, 2, 4, 4),
        (257, 3, 4, 3, 2, 4, 5),
        (258, 3, 4, 3, 2, 4, 6),
        (259, 2, 3, 4, 2, 4, 1),
        (260, 2, 3, 4, 2, 4, 2),
        (261, 2, 3, 4, 2, 4, 3),
        (262, 2, 3, 4, 2, 4, 4),
        (263, 2, 3, 4, 2, 4, 5),
        (264, 2, 3, 4, 2, 4, 6),
        (265, 1, 3, 5, 2, 4, 1),
        (266, 1, 3, 5, 2, 4, 2),
        (267, 1, 3, 5, 2, 4, 3),
        (268, 1, 3, 5, 2, 4, 4),
        (269, 1, 3, 5, 2, 4, 5),
        (270, 1, 3, 5, 2, 4, 6),
        (271, 3, 3, 1, 2, 5, 1),
        (272, 3, 3, 1, 2, 5, 2),
        (273, 3, 4, 1, 2, 5, 3),
        (274, 3, 4, 1, 2, 5, 4),
        (275, 3, 4, 1, 2, 5, 5),
        (276, 3, 5, 1, 2, 5, 6),
        (277, 3, 3, 2, 2, 5, 1),
        (278, 3, 3, 2, 2, 5, 2),
        (279, 3, 3, 2, 2, 5, 3),
        (280, 3, 4, 2, 2, 5, 4),
        (281, 3, 4, 2, 2, 5, 5),
        (282, 3, 4, 2, 2, 5, 6),
        (283, 3, 3, 3, 2, 5, 1),
        (284, 3, 3, 3, 2, 5, 2),
        (285, 3, 3, 3, 2, 5, 3),
        (286, 3, 4, 3, 2, 5, 4),
        (287, 3, 4, 3, 2, 5, 5),
        (288, 3, 4, 3, 2, 5, 6),
        (289, 3, 3, 4, 2, 5, 1),
        (290, 3, 3, 4, 2, 5, 2),
        (291, 3, 3, 4, 2, 5, 3),
        (292, 3, 4, 4, 2, 5, 4),
        (293, 3, 4, 4, 2, 5, 5),
        (294, 3, 4, 4, 2, 5, 6),
        (295, 3, 3, 5, 2, 5, 1),
        (296, 3, 3, 5, 2, 5, 2),
        (297, 3, 3, 5, 2, 5, 3),
        (298, 3, 3, 5, 2, 5, 4),
        (299, 3, 3, 5, 2, 5, 5),
        (300, 3, 3, 5, 2, 5, 6),
        (301, 7, 7, 1, 3, 1, 1),
        (302, 7, 7, 1, 3, 1, 2),
        (303, 7, 7, 1, 3, 1, 3),
        (304, 7, 7, 1, 3, 1, 4),
        (305, 7, 7, 1, 3, 1, 5),
        (306, 7, 7, 1, 3, 1, 6),
        (307, 7, 7, 2, 3, 1, 1),
        (308, 7, 7, 2, 3, 1, 2),
        (309, 7, 7, 2, 3, 1, 3),
        (310, 7, 7, 2, 3, 1, 4),
        (311, 7, 7, 2, 3, 1, 5),
        (312, 7, 7, 2, 3, 1, 6),
        (313, 7, 7, 3, 3, 1, 1),
        (314, 7, 7, 3, 3, 1, 2),
        (315, 7, 7, 3, 3, 1, 3),
        (316, 7, 7, 3, 3, 1, 4),
        (317, 7, 7, 3, 3, 1, 5),
        (318, 7, 7, 3, 3, 1, 6),
        (319, 7, 7, 4, 3, 1, 1),
        (320, 7, 7, 4, 3, 1, 2),
        (321, 7, 7, 4, 3, 1, 3),
        (322, 7, 7, 4, 3, 1, 4),
        (323, 7, 7, 4, 3, 1, 5),
        (324, 7, 7, 4, 3, 1, 6),
        (325, 7, 7, 5, 3, 1, 1),
        (326, 7, 7, 5, 3, 1, 2),
        (327, 7, 7, 5, 3, 1, 3),
        (328, 7, 7, 5, 3, 1, 4),
        (329, 7, 7, 5, 3, 1, 5),
        (330, 7, 7, 5, 3, 1, 6),
        (331, 3, 3, 1, 3, 2, 1),
        (332, 3, 3, 1, 3, 2, 2),
        (333, 3, 3, 1, 3, 2, 3),
        (334, 3, 4, 1, 3, 2, 4),
        (335, 4, 4, 1, 3, 2, 5),
        (336, 4, 4, 1, 3, 2, 6),
        (337, 3, 3, 2, 3, 2, 1),
        (338, 3, 3, 2, 3, 2, 2),
        (339, 3, 4, 2, 3, 2, 3),
        (340, 3, 4, 2, 3, 2, 4),
        (341, 4, 4, 2, 3, 2, 5),
        (342, 4, 4, 2, 3, 2, 6),
        (343, 3, 5, 3, 3, 2, 1),
        (344, 3, 5, 3, 3, 2, 2),
        (345, 3, 5, 3, 3, 2, 3),
        (346, 3, 5, 3, 3, 2, 4),
        (347, 3, 5, 3, 3, 2, 5),
        (348, 3, 5, 3, 3, 2, 6),
        (349, 2, 4, 4, 3, 2, 1),
        (350, 2, 4, 4, 3, 2, 2),
        (351, 2, 4, 4, 3, 2, 3),
        (352, 2, 4, 4, 3, 2, 4),
        (353, 2, 4, 4, 3, 2, 5),
        (354, 2, 4, 4, 3, 2, 6),
        (355, 2, 4, 5, 3, 2, 1),
        (356, 2, 4, 5, 3, 2, 2),
        (357, 2, 4, 5, 3, 2, 3),
        (358, 2, 4, 5, 3, 2, 4),
        (359, 2, 4, 5, 3, 2, 5),
        (360, 2, 4, 5, 3, 2, 6),
        (361, 3, 3, 1, 3, 3, 1),
        (362, 3, 3, 1, 3, 3, 2),
        (363, 3, 3, 1, 3, 3, 3),
        (364, 3, 4, 1, 3, 3, 4),
        (365, 4, 4, 1, 3, 3, 5),
        (366, 4, 4, 1, 3, 3, 6),
        (367, 3, 3, 2, 3, 3, 1),
        (368, 3, 3, 2, 3, 3, 2),
        (369, 3, 4, 2, 3, 3, 3),
        (370, 3, 4, 2, 3, 3, 4),
        (371, 4, 4, 2, 3, 3, 5),
        (372, 4, 4, 2, 3, 3, 6),
        (373, 3, 5, 3, 3, 3, 1),
        (374, 3, 5, 3, 3, 3, 2),
        (375, 3, 5, 3, 3, 3, 3),
        (376, 3, 5, 3, 3, 3, 4),
        (377, 3, 5, 3, 3, 3, 5),
        (378, 3, 5, 3, 3, 3, 6),
        (379, 2, 4, 4, 3, 3, 1),
        (380, 2, 4, 4, 3, 3, 2),
        (381, 2, 4, 4, 3, 3, 3),
        (382, 2, 4, 4, 3, 3, 4),
        (383, 2, 4, 4, 3, 3, 5),
        (384, 2, 4, 4, 3, 3, 6),
        (385, 2, 4, 5, 3, 3, 1),
        (386, 2, 4, 5, 3, 3, 2),
        (387, 2, 4, 5, 3, 3, 3),
        (388, 2, 4, 5, 3, 3, 4),
        (389, 2, 4, 5, 3, 3, 5),
        (390, 2, 4, 5, 3, 3, 6),
        (391, 3, 3, 1, 3, 4, 1),
        (392, 3, 3, 1, 3, 4, 2),
        (393, 3, 3, 1, 3, 4, 3),
        (394, 3, 4, 1, 3, 4, 4),
        (395, 4, 4, 1, 3, 4, 5),
        (396, 4, 4, 1, 3, 4, 6),
        (397, 3, 3, 2, 3, 4, 1),
        (398, 3, 3, 2, 3, 4, 2),
        (399, 3, 4, 2, 3, 4, 3),
        (400, 3, 4, 2, 3, 4, 4),
        (401, 4, 4, 2, 3, 4, 5),
        (402, 4, 4, 2, 3, 4, 6),
        (403, 3, 5, 3, 3, 4, 1),
        (404, 3, 5, 3, 3, 4, 2),
        (405, 3, 5, 3, 3, 4, 3),
        (406, 3, 5, 3, 3, 4, 4),
        (407, 3, 5, 3, 3, 4, 5),
        (408, 3, 5, 3, 3, 4, 6),
        (409, 2, 4, 4, 3, 4, 1),
        (410, 2, 4, 4, 3, 4, 2),
        (411, 2, 4, 4, 3, 4, 3),
        (412, 2, 4, 4, 3, 4, 4),
        (413, 2, 4, 4, 3, 4, 5),
        (414, 2, 4, 4, 3, 4, 6),
        (415, 2, 4, 5, 3, 4, 1),
        (416, 2, 4, 5, 3, 4, 2),
        (417, 2, 4, 5, 3, 4, 3),
        (418, 2, 4, 5, 3, 4, 4),
        (419, 2, 4, 5, 3, 4, 5),
        (420, 2, 4, 5, 3, 4, 6),
        (421, 3, 3, 1, 3, 5, 1),
        (422, 3, 4, 1, 3, 5, 2),
        (423, 3, 4, 1, 3, 5, 3),
        (424, 3, 4, 1, 3, 5, 4),
        (425, 4, 5, 1, 3, 5, 5),
        (426, 3, 5, 1, 3, 5, 6),
        (427, 3, 4, 2, 3, 5, 1),
        (428, 3, 4, 2, 3, 5, 2),
        (429, 3, 4, 2, 3, 5, 3),
        (430, 4, 4, 2, 3, 5, 4),
        (431, 4, 5, 2, 3, 5, 5),
        (432, 3, 5, 2, 3, 5, 6),
        (433, 4, 5, 3, 3, 5, 1),
        (434, 4, 5, 3, 3, 5, 2),
        (435, 4, 5, 3, 3, 5, 3),
        (436, 4, 5, 3, 3, 5, 4),
        (437, 4, 5, 3, 3, 5, 5),
        (438, 4, 5, 3, 3, 5, 6),
        (439, 3, 4, 4, 3, 5, 1),
        (440, 3, 4, 4, 3, 5, 2),
        (441, 3, 4, 4, 3, 5, 3),
        (442, 3, 4, 4, 3, 5, 4),
        (443, 3, 4, 4, 3, 5, 5),
        (444, 3, 4, 4, 3, 5, 6),
        (445, 3, 4, 5, 3, 5, 1),
        (446, 3, 4, 5, 3, 5, 2),
        (447, 3, 4, 5, 3, 5, 3),
        (448, 3, 4, 5, 3, 5, 4),
        (449, 3, 4, 5, 3, 5, 5),
        (450, 3, 4, 5, 3, 5, 6),
        (451, 7, 7, 1, 4, 1, 1),
        (452, 7, 7, 1, 4, 1, 2),
        (453, 7, 7, 1, 4, 1, 3),
        (454, 7, 7, 1, 4, 1, 4),
        (455, 7, 7, 1, 4, 1, 5),
        (456, 7, 7, 1, 4, 1, 6),
        (457, 7, 7, 2, 4, 1, 1),
        (458, 7, 7, 2, 4, 1, 2),
        (459, 7, 7, 2, 4, 1, 3),
        (460, 7, 7, 2, 4, 1, 4),
        (461, 7, 7, 2, 4, 1, 5),
        (462, 7, 7, 2, 4, 1, 6),
        (463, 7, 7, 3, 4, 1, 1),
        (464, 7, 7, 3, 4, 1, 2),
        (465, 7, 7, 3, 4, 1, 3),
        (466, 7, 7, 3, 4, 1, 4),
        (467, 7, 7, 3, 4, 1, 5),
        (468, 7, 7, 3, 4, 1, 6),
        (469, 7, 7, 4, 4, 1, 1),
        (470, 7, 7, 4, 4, 1, 2),
        (471, 7, 7, 4, 4, 1, 3),
        (472, 7, 7, 4, 4, 1, 4),
        (473, 7, 7, 4, 4, 1, 5),
        (474, 7, 7, 4, 4, 1, 6),
        (475, 7, 7, 5, 4, 1, 1),
        (476, 7, 7, 5, 4, 1, 2),
        (477, 7, 7, 5, 4, 1, 3),
        (478, 7, 7, 5, 4, 1, 4),
        (479, 7, 7, 5, 4, 1, 5),
        (480, 7, 7, 5, 4, 1, 6),
        (481, 4, 4, 1, 4, 2, 1),
        (482, 4, 4, 1, 4, 2, 2),
        (483, 4, 4, 1, 4, 2, 3),
        (484, 4, 4, 1, 4, 2, 4),
        (485, 4, 4, 1, 4, 2, 5),
        (486, 4, 4, 1, 4, 2, 6),
        (487, 4, 4, 2, 4, 2, 1),
        (488, 4, 4, 2, 4, 2, 2),
        (489, 4, 4, 2, 4, 2, 3),
        (490, 4, 4, 2, 4, 2, 4),
        (491, 4, 4, 2, 4, 2, 5),
        (492, 4, 4, 2, 4, 2, 6),
        (493, 3, 6, 3, 4, 2, 1),
        (494, 3, 6, 3, 4, 2, 2),
        (495, 3, 6, 3, 4, 2, 3),
        (496, 3, 6, 3, 4, 2, 4),
        (497, 3, 6, 3, 4, 2, 5),
        (498, 3, 6, 3, 4, 2, 6),
        (499, 2, 4, 4, 4, 2, 1),
        (500, 2, 4, 4, 4, 2, 2),
        (501, 2, 4, 4, 4, 2, 3),
        (502, 2, 4, 4, 4, 2, 4),
        (503, 2, 4, 4, 4, 2, 5),
        (504, 2, 4, 4, 4, 2, 6),
        (505, 2, 4, 5, 4, 2, 1),
        (506, 2, 4, 5, 4, 2, 2),
        (507, 2, 4, 5, 4, 2, 3),
        (508, 2, 4, 5, 4, 2, 4),
        (509, 2, 4, 5, 4, 2, 5),
        (510, 2, 4, 5, 4, 2, 6),
        (511, 4, 4, 1, 4, 3, 1),
        (512, 4, 4, 1, 4, 3, 2),
        (513, 4, 4, 1, 4, 3, 3),
        (514, 4, 4, 1, 4, 3, 4),
        (515, 4, 4, 1, 4, 3, 5),
        (516, 4, 4, 1, 4, 3, 6),
        (517, 4, 4, 2, 4, 3, 1),
        (518, 4, 4, 2, 4, 3, 2),
        (519, 4, 4, 2, 4, 3, 3),
        (520, 4, 4, 2, 4, 3, 4),
        (521, 4, 4, 2, 4, 3, 5),
        (522, 4, 4, 2, 4, 3, 6),
        (523, 3, 6, 3, 4, 3, 1),
        (524, 3, 6, 3, 4, 3, 2),
        (525, 3, 6, 3, 4, 3, 3),
        (526, 3, 6, 3, 4, 3, 4),
        (527, 3, 6, 3, 4, 3, 5),
        (528, 3, 6, 3, 4, 3, 6),
        (529, 2, 4, 4, 4, 3, 1),
        (530, 2, 4, 4, 4, 3, 2),
        (531, 2, 4, 4, 4, 3, 3),
        (532, 2, 4, 4, 4, 3, 4),
        (533, 2, 4, 4, 4, 3, 5),
        (534, 2, 4, 4, 4, 3, 6),
        (535, 2, 4, 5, 4, 3, 1),
        (536, 2, 4, 5, 4, 3, 2),
        (537, 2, 4, 5, 4, 3, 3),
        (538, 2, 4, 5, 4, 3, 4),
        (539, 2, 4, 5, 4, 3, 5),
        (540, 2, 4, 5, 4, 3, 6),
        (541, 4, 4, 1, 4, 4, 1),
        (542, 4, 4, 1, 4, 4, 2),
        (543, 4, 4, 1, 4, 4, 3),
        (544, 4, 4, 1, 4, 4, 4),
        (545, 4, 4, 1, 4, 4, 5),
        (546, 4, 4, 1, 4, 4, 6),
        (547, 4, 4, 2, 4, 4, 1),
        (548, 4, 4, 2, 4, 4, 2),
        (549, 4, 4, 2, 4, 4, 3),
        (550, 4, 4, 2, 4, 4, 4),
        (551, 4, 4, 2, 4, 4, 5),
        (552, 4, 4, 2, 4, 4, 6),
        (553, 3, 6, 3, 4, 4, 1),
        (554, 3, 6, 3, 4, 4, 2),
        (555, 3, 6, 3, 4, 4, 3),
        (556, 3, 6, 3, 4, 4, 4),
        (557, 3, 6, 3, 4, 4, 5),
        (558, 3, 6, 3, 4, 4, 6),
        (559, 2, 4, 4, 4, 4, 1),
        (560, 2, 4, 4, 4, 4, 2),
        (561, 2, 4, 4, 4, 4, 3),
        (562, 2, 4, 4, 4, 4, 4),
        (563, 2, 4, 4, 4, 4, 5),
        (564, 2, 4, 4, 4, 4, 6),
        (565, 2, 4, 5, 4, 4, 1),
        (566, 2, 4, 5, 4, 4, 2),
        (567, 2, 4, 5, 4, 4, 3),
        (568, 2, 4, 5, 4, 4, 4),
        (569, 2, 4, 5, 4, 4, 5),
        (570, 2, 4, 5, 4, 4, 6),
        (571, 4, 4, 1, 4, 5, 1),
        (572, 4, 4, 1, 4, 5, 2),
        (573, 4, 4, 1, 4, 5, 3),
        (574, 4, 4, 1, 4, 5, 4),
        (575, 4, 4, 1, 4, 5, 5),
        (576, 4, 4, 1, 4, 5, 6),
        (577, 4, 4, 2, 4, 5, 1),
        (578, 4, 4, 2, 4, 5, 2),
        (579, 4, 4, 2, 4, 5, 3),
        (580, 4, 4, 2, 4, 5, 4),
        (581, 4, 4, 2, 4, 5, 5),
        (582, 4, 4, 2, 4, 5, 6),
        (583, 4, 6, 3, 4, 5, 1),
        (584, 4, 6, 3, 4, 5, 2),
        (585, 4, 6, 3, 4, 5, 3),
        (586, 4, 6, 3, 4, 5, 4),
        (587, 4, 6, 3, 4, 5, 5),
        (588, 4, 6, 3, 4, 5, 6),
        (589, 4, 4, 4, 4, 5, 1),
        (590, 4, 4, 4, 4, 5, 2),
        (591, 4, 4, 4, 4, 5, 3),
        (592, 4, 4, 4, 4, 5, 4),
        (593, 4, 4, 4, 4, 5, 5),
        (594, 3, 4, 4, 4, 5, 6),
        (595, 4, 4, 5, 4, 5, 1),
        (596, 4, 4, 5, 4, 5, 2),
        (597, 4, 4, 5, 4, 5, 3),
        (598, 4, 4, 5, 4, 5, 4),
        (599, 4, 4, 5, 4, 5, 5),
        (600, 4, 4, 5, 4, 5, 6),
        (601, 7, 7, 1, 5, 1, 1),
        (602, 7, 7, 1, 5, 1, 2),
        (603, 7, 7, 1, 5, 1, 3),
        (604, 7, 7, 1, 5, 1, 4),
        (605, 7, 7, 1, 5, 1, 5),
        (606, 7, 7, 1, 5, 1, 6),
        (607, 7, 7, 2, 5, 1, 1),
        (608, 7, 7, 2, 5, 1, 2),
        (609, 7, 7, 2, 5, 1, 3),
        (610, 7, 7, 2, 5, 1, 4),
        (611, 7, 7, 2, 5, 1, 5),
        (612, 7, 7, 2, 5, 1, 6),
        (613, 7, 7, 3, 5, 1, 1),
        (614, 7, 7, 3, 5, 1, 2),
        (615, 7, 7, 3, 5, 1, 3),
        (616, 7, 7, 3, 5, 1, 4),
        (617, 7, 7, 3, 5, 1, 5),
        (618, 7, 7, 3, 5, 1, 6),
        (619, 7, 7, 4, 5, 1, 1),
        (620, 7, 7, 4, 5, 1, 2),
        (621, 7, 7, 4, 5, 1, 3),
        (622, 7, 7, 4, 5, 1, 4),
        (623, 7, 7, 4, 5, 1, 5),
        (624, 7, 7, 4, 5, 1, 6),
        (625, 7, 7, 5, 5, 1, 1),
        (626, 7, 7, 5, 5, 1, 2),
        (627, 7, 7, 5, 5, 1, 3),
        (628, 7, 7, 5, 5, 1, 4),
        (629, 7, 7, 5, 5, 1, 5),
        (630, 7, 7, 5, 5, 1, 6),
        (631, 4, 4, 1, 5, 2, 1),
        (632, 4, 4, 1, 5, 2, 2),
        (633, 4, 4, 1, 5, 2, 3),
        (634, 4, 4, 1, 5, 2, 4),
        (635, 4, 4, 1, 5, 2, 5),
        (636, 4, 4, 1, 5, 2, 6),
        (637, 4, 6, 2, 5, 2, 1),
        (638, 4, 6, 2, 5, 2, 2),
        (639, 4, 6, 2, 5, 2, 3),
        (640, 4, 6, 2, 5, 2, 4),
        (641, 4, 6, 2, 5, 2, 5),
        (642, 4, 6, 2, 5, 2, 6),
        (643, 3, 6, 3, 5, 2, 1),
        (644, 3, 6, 3, 5, 2, 2),
        (645, 3, 6, 3, 5, 2, 3),
        (646, 3, 6, 3, 5, 2, 4),
        (647, 3, 6, 3, 5, 2, 5),
        (648, 3, 6, 3, 5, 2, 6),
        (649, 2, 4, 4, 5, 2, 1),
        (650, 2, 4, 4, 5, 2, 2),
        (651, 2, 4, 4, 5, 2, 3),
        (652, 2, 4, 4, 5, 2, 4),
        (653, 2, 4, 4, 5, 2, 5),
        (654, 2, 4, 4, 5, 2, 6),
        (655, 2, 4, 5, 5, 2, 1),
        (656, 2, 4, 5, 5, 2, 2),
        (657, 2, 4, 5, 5, 2, 3),
        (658, 2, 4, 5, 5, 2, 4),
        (659, 2, 4, 5, 5, 2, 5),
        (660, 2, 4, 5, 5, 2, 6),
        (661, 4, 4, 1, 5, 3, 1),
        (662, 4, 4, 1, 5, 3, 2),
        (663, 4, 4, 1, 5, 3, 3),
        (664, 4, 4, 1, 5, 3, 4),
        (665, 4, 4, 1, 5, 3, 5),
        (666, 4, 4, 1, 5, 3, 6),
        (667, 4, 6, 2, 5, 3, 1),
        (668, 4, 6, 2, 5, 3, 2),
        (669, 4, 6, 2, 5, 3, 3),
        (670, 4, 6, 2, 5, 3, 4),
        (671, 4, 6, 2, 5, 3, 5),
        (672, 4, 6, 2, 5, 3, 6),
        (673, 3, 6, 3, 5, 3, 1),
        (674, 3, 6, 3, 5, 3, 2),
        (675, 3, 6, 3, 5, 3, 3),
        (676, 3, 6, 3, 5, 3, 4),
        (677, 3, 6, 3, 5, 3, 5),
        (678, 3, 6, 3, 5, 3, 6),
        (679, 2, 4, 4, 5, 3, 1),
        (680, 2, 4, 4, 5, 3, 2),
        (681, 2, 4, 4, 5, 3, 3),
        (682, 2, 4, 4, 5, 3, 4),
        (683, 2, 4, 4, 5, 3, 5),
        (684, 2, 4, 4, 5, 3, 6),
        (685, 2, 4, 5, 5, 3, 1),
        (686, 2, 4, 5, 5, 3, 2),
        (687, 2, 4, 5, 5, 3, 3),
        (688, 2, 4, 5, 5, 3, 4),
        (689, 2, 4, 5, 5, 3, 5),
        (690, 2, 4, 5, 5, 3, 6),
        (691, 4, 4, 1, 5, 4, 1),
        (692, 4, 4, 1, 5, 4, 2),
        (693, 4, 4, 1, 5, 4, 3),
        (694, 4, 4, 1, 5, 4, 4),
        (695, 4, 4, 1, 5, 4, 5),
        (696, 4, 4, 1, 5, 4, 6),
        (697, 4, 6, 2, 5, 4, 1),
        (698, 4, 6, 2, 5, 4, 2),
        (699, 4, 6, 2, 5, 4, 3),
        (700, 4, 6, 2, 5, 4, 4),
        (701, 4, 6, 2, 5, 4, 5),
        (702, 4, 6, 2, 5, 4, 6),
        (703, 3, 6, 3, 5, 4, 1),
        (704, 3, 6, 3, 5, 4, 2),
        (705, 3, 6, 3, 5, 4, 3),
        (706, 3, 6, 3, 5, 4, 4),
        (707, 3, 6, 3, 5, 4, 5),
        (708, 3, 6, 3, 5, 4, 6),
        (709, 2, 4, 4, 5, 4, 1),
        (710, 2, 4, 4, 5, 4, 2),
        (711, 2, 4, 4, 5, 4, 3),
        (712, 2, 4, 4, 5, 4, 4),
        (713, 2, 4, 4, 5, 4, 5),
        (714, 2, 4, 4, 5, 4, 6),
        (715, 2, 4, 5, 5, 4, 1),
        (716, 2, 4, 5, 5, 4, 2),
        (717, 2, 4, 5, 5, 4, 3),
        (718, 2, 4, 5, 5, 4, 4),
        (719, 2, 4, 5, 5, 4, 5),
        (720, 2, 4, 5, 5, 4, 6),
        (721, 4, 4, 1, 5, 5, 1),
        (722, 4, 4, 1, 5, 5, 2),
        (723, 4, 4, 1, 5, 5, 3),
        (724, 4, 4, 1, 5, 5, 4),
        (725, 4, 4, 1, 5, 5, 5),
        (726, 4, 4, 1, 5, 5, 6),
        (727, 4, 6, 2, 5, 5, 1),
        (728, 4, 6, 2, 5, 5, 2),
        (729, 4, 6, 2, 5, 5, 3),
        (730, 4, 6, 2, 5, 5, 4),
        (731, 4, 6, 2, 5, 5, 5),
        (732, 4, 6, 2, 5, 5, 6),
        (733, 4, 6, 3, 5, 5, 1),
        (734, 4, 6, 3, 5, 5, 2),
        (735, 4, 6, 3, 5, 5, 3),
        (736, 4, 6, 3, 5, 5, 4),
        (737, 4, 6, 3, 5, 5, 5),
        (738, 4, 6, 3, 5, 5, 6),
        (739, 4, 4, 4, 5, 5, 1),
        (740, 4, 4, 4, 5, 5, 2),
        (741, 4, 4, 4, 5, 5, 3),
        (742, 4, 4, 4, 5, 5, 4),
        (743, 4, 4, 4, 5, 5, 5),
        (744, 4, 4, 4, 5, 5, 6),
        (745, 4, 4, 5, 5, 5, 1),
        (746, 4, 4, 5, 5, 5, 2),
        (747, 4, 4, 5, 5, 5, 3),
        (748, 4, 4, 5, 5, 5, 4),
        (749, 4, 4, 5, 5, 5, 5),
        (750, 4, 4, 5, 5, 5, 6),
    )

    MAP = defaultdict(list)
    for t in VALUES:
        key = (t[3], t[4], t[6])
        values = (t[5], t[1], t[2])
        MAP[key].append(values)

    def __init__(self, workout_component_id, minimum, maximum):
        self.workout_component_id = workout_component_id
        self.minimum = minimum
        self.maximum = maximum

    @classmethod
    def get_by_week_phase_fitness_level(cls, week, phase_id, fitness_level_id):
        key = (phase_id, fitness_level_id, week)
        workout_component_frequencies = cls.MAP[key]
        frequencies = []
        for tuple_obj in workout_component_frequencies:
            workout_component_id, minimum, maximum = tuple_obj
            frequencies.append(cls(workout_component_id, minimum, maximum))
        return frequencies


class Exhaustion(object):
    # id, daysPerWeek, phase_id, percent
    VALUES = (
        (1, 1, 1, 25),
        (2, 2, 1, 33),
        (3, 3, 1, 50),
        (4, 4, 1, 80),
        (5, 5, 1, 90),
        (6, 6, 1, 100),
        (7, 7, 1, 100),
        (8, 1, 2, 25),
        (9, 2, 2, 33),
        (10, 3, 2, 50),
        (11, 4, 2, 80),
        (12, 5, 2, 90),
        (13, 6, 2, 100),
        (14, 7, 2, 100),
        (15, 1, 3, 25),
        (16, 2, 3, 33),
        (17, 3, 3, 50),
        (18, 4, 3, 80),
        (19, 5, 3, 90),
        (20, 6, 3, 100),
        (21, 7, 3, 100),
        (22, 1, 4, 25),
        (23, 2, 4, 33),
        (24, 3, 4, 50),
        (25, 4, 4, 80),
        (26, 5, 4, 90),
        (27, 6, 4, 100),
        (28, 7, 4, 100),
        (29, 1, 5, 25),
        (30, 2, 5, 33),
        (31, 3, 5, 50),
        (32, 4, 5, 80),
        (33, 5, 5, 90),
        (34, 6, 5, 100),
        (35, 7, 5, 100),
    )

    MAP = {(t[1], t[2]): t[3] for t in VALUES}

    @classmethod
    def get_percent(cls, days_per_week, phase_id):
        key = (days_per_week, phase_id)
        return float(cls.MAP[key]) / 100.0


class ExercisesPerMuscleGroup(object):
    # id, muscleGroup_id, phase_id, minimum, maximum, fitnessLevel_id
    VALUES = (
        (1, 1, 1, 1, 1, 1),
        (2, 1, 1, 1, 1, 2),
        (3, 1, 1, 1, 2, 3),
        (4, 1, 1, 1, 3, 4),
        (5, 1, 1, 1, 3, 5),
        (6, 1, 2, 2, 4, 1),
        (7, 1, 2, 2, 4, 2),
        (8, 1, 2, 2, 2, 3),
        (9, 1, 2, 2, 4, 4),
        (10, 1, 2, 2, 4, 5),
        (11, 1, 3, 1, 2, 1),
        (12, 1, 3, 1, 2, 2),
        (13, 1, 3, 1, 2, 3),
        (14, 1, 3, 1, 3, 4),
        (15, 1, 3, 1, 3, 5),
        (16, 1, 4, 1, 1, 1),
        (17, 1, 4, 1, 1, 2),
        (18, 1, 4, 1, 1, 3),
        (19, 1, 4, 1, 1, 4),
        (20, 1, 4, 1, 1, 5),
        (21, 1, 5, 2, 2, 1),
        (22, 1, 5, 2, 2, 2),
        (23, 1, 5, 1, 1, 3),
        (24, 1, 5, 2, 2, 4),
        (25, 1, 5, 2, 2, 5),
        (26, 2, 1, 1, 2, 1),
        (27, 2, 1, 1, 2, 2),
        (28, 2, 1, 1, 2, 3),
        (29, 2, 1, 1, 3, 4),
        (30, 2, 1, 1, 3, 5),
        (31, 2, 2, 2, 4, 1),
        (32, 2, 2, 2, 4, 2),
        (33, 2, 2, 2, 4, 3),
        (34, 2, 2, 2, 6, 4),
        (35, 2, 2, 2, 6, 5),
        (36, 2, 3, 1, 2, 1),
        (37, 2, 3, 1, 2, 2),
        (38, 2, 3, 1, 3, 3),
        (39, 2, 3, 1, 3, 4),
        (40, 2, 3, 1, 3, 5),
        (41, 2, 4, 1, 1, 1),
        (42, 2, 4, 1, 1, 2),
        (43, 2, 4, 1, 2, 3),
        (44, 2, 4, 1, 2, 4),
        (45, 2, 4, 1, 2, 5),
        (46, 2, 5, 2, 4, 1),
        (47, 2, 5, 2, 4, 2),
        (48, 2, 5, 2, 4, 3),
        (49, 2, 5, 2, 4, 4),
        (50, 2, 5, 2, 4, 5),
        (51, 3, 1, 1, 1, 1),
        (52, 3, 1, 1, 1, 2),
        (53, 3, 1, 1, 1, 3),
        (54, 3, 1, 1, 2, 4),
        (55, 3, 1, 1, 2, 5),
        (56, 3, 2, 2, 2, 1),
        (57, 3, 2, 2, 2, 2),
        (58, 3, 2, 2, 2, 3),
        (59, 3, 2, 2, 4, 4),
        (60, 3, 2, 2, 4, 5),
        (61, 3, 3, 1, 1, 1),
        (62, 3, 3, 1, 1, 2),
        (63, 3, 3, 1, 2, 3),
        (64, 3, 3, 1, 3, 4),
        (65, 3, 3, 1, 3, 5),
        (66, 3, 4, 1, 1, 1),
        (67, 3, 4, 1, 1, 2),
        (68, 3, 4, 1, 1, 3),
        (69, 3, 4, 1, 1, 4),
        (70, 3, 4, 1, 1, 5),
        (71, 3, 5, 2, 2, 1),
        (72, 3, 5, 2, 2, 2),
        (73, 3, 5, 2, 2, 3),
        (74, 3, 5, 2, 2, 4),
        (75, 3, 5, 2, 2, 5),
        (76, 4, 1, 0, 0, 1),
        (77, 4, 1, 0, 0, 2),
        (78, 4, 1, 0, 0, 3),
        (79, 4, 1, 0, 0, 4),
        (80, 4, 1, 0, 0, 5),
        (81, 4, 2, 0, 0, 1),
        (82, 4, 2, 0, 0, 2),
        (83, 4, 2, 0, 0, 3),
        (84, 4, 2, 0, 0, 4),
        (85, 4, 2, 0, 0, 5),
        (86, 4, 3, 1, 1, 1),
        (87, 4, 3, 1, 1, 2),
        (88, 4, 3, 1, 1, 3),
        (89, 4, 3, 1, 2, 4),
        (90, 4, 3, 1, 2, 5),
        (91, 4, 4, 1, 1, 1),
        (92, 4, 4, 1, 1, 2),
        (93, 4, 4, 0, 0, 3),
        (94, 4, 4, 0, 0, 4),
        (95, 4, 4, 0, 0, 5),
        (96, 4, 5, 0, 0, 1),
        (97, 4, 5, 0, 0, 2),
        (98, 4, 5, 0, 0, 3),
        (99, 4, 5, 0, 0, 4),
        (100, 4, 5, 0, 0, 5),
        (101, 5, 1, 0, 0, 1),
        (102, 5, 1, 0, 0, 2),
        (103, 5, 1, 0, 0, 3),
        (104, 5, 1, 0, 0, 4),
        (105, 5, 1, 0, 0, 5),
        (106, 5, 2, 0, 0, 1),
        (107, 5, 2, 0, 0, 2),
        (108, 5, 2, 0, 0, 3),
        (109, 5, 2, 0, 0, 4),
        (110, 5, 2, 0, 0, 5),
        (111, 5, 3, 1, 1, 1),
        (112, 5, 3, 1, 1, 2),
        (113, 5, 3, 1, 1, 3),
        (114, 5, 3, 1, 2, 4),
        (115, 5, 3, 1, 2, 5),
        (116, 5, 4, 1, 1, 1),
        (117, 5, 4, 1, 1, 2),
        (118, 5, 4, 0, 0, 3),
        (119, 5, 4, 0, 0, 4),
        (120, 5, 4, 0, 0, 5),
        (121, 5, 5, 0, 0, 1),
        (122, 5, 5, 0, 0, 2),
        (123, 5, 5, 0, 0, 3),
        (124, 5, 5, 0, 0, 4),
        (125, 5, 5, 0, 0, 5),
        (126, 6, 1, 0, 0, 1),
        (127, 6, 1, 0, 0, 2),
        (128, 6, 1, 0, 0, 3),
        (129, 6, 1, 0, 0, 4),
        (130, 6, 1, 0, 0, 5),
        (131, 6, 2, 0, 0, 1),
        (132, 6, 2, 0, 0, 2),
        (133, 6, 2, 0, 0, 3),
        (134, 6, 2, 0, 0, 4),
        (135, 6, 2, 0, 0, 5),
        (136, 6, 3, 1, 1, 1),
        (137, 6, 3, 1, 1, 2),
        (138, 6, 3, 1, 1, 3),
        (139, 6, 3, 1, 2, 4),
        (140, 6, 3, 1, 2, 5),
        (141, 6, 4, 1, 1, 1),
        (142, 6, 4, 1, 1, 2),
        (143, 6, 4, 0, 0, 3),
        (144, 6, 4, 0, 0, 4),
        (145, 6, 4, 0, 0, 5),
        (146, 6, 5, 0, 0, 1),
        (147, 6, 5, 0, 0, 2),
        (148, 6, 5, 0, 0, 3),
        (149, 6, 5, 0, 0, 4),
        (150, 6, 5, 0, 0, 5),
        (151, 7, 1, 1, 2, 1),
        (152, 7, 1, 1, 2, 2),
        (153, 7, 1, 1, 2, 3),
        (154, 7, 1, 1, 3, 4),
        (155, 7, 1, 1, 3, 5),
        (156, 7, 2, 1, 2, 1),
        (157, 7, 2, 1, 2, 2),
        (158, 7, 2, 1, 2, 3),
        (159, 7, 2, 1, 3, 4),
        (160, 7, 2, 1, 3, 5),
        (161, 7, 3, 1, 3, 1),
        (162, 7, 3, 1, 3, 2),
        (163, 7, 3, 1, 2, 3),
        (164, 7, 3, 1, 3, 4),
        (165, 7, 3, 1, 3, 5),
        (166, 7, 4, 1, 2, 1),
        (167, 7, 4, 1, 2, 2),
        (168, 7, 4, 1, 2, 3),
        (169, 7, 4, 1, 3, 4),
        (170, 7, 4, 1, 3, 5),
        (171, 7, 5, 1, 2, 1),
        (172, 7, 5, 1, 2, 2),
        (173, 7, 5, 1, 2, 3),
        (174, 7, 5, 1, 3, 4),
        (175, 7, 5, 1, 3, 5),
        (176, 8, 1, 1, 2, 1),
        (177, 8, 1, 1, 2, 2),
        (178, 8, 1, 1, 2, 3),
        (179, 8, 1, 1, 3, 4),
        (180, 8, 1, 1, 3, 5),
        (181, 8, 2, 1, 2, 1),
        (182, 8, 2, 1, 2, 2),
        (183, 8, 2, 1, 2, 3),
        (184, 8, 2, 1, 3, 4),
        (185, 8, 2, 1, 3, 5),
        (186, 8, 3, 1, 2, 1),
        (187, 8, 3, 1, 2, 2),
        (188, 8, 3, 1, 2, 3),
        (189, 8, 3, 1, 3, 4),
        (190, 8, 3, 1, 3, 5),
        (191, 8, 4, 1, 2, 1),
        (192, 8, 4, 1, 2, 2),
        (193, 8, 4, 1, 2, 3),
        (194, 8, 4, 1, 3, 4),
        (195, 8, 4, 1, 3, 5),
        (196, 8, 5, 1, 2, 1),
        (197, 8, 5, 1, 2, 2),
        (198, 8, 5, 1, 2, 3),
        (199, 8, 5, 1, 3, 4),
        (200, 8, 5, 1, 3, 5),
        (201, 9, 1, 1, 4, 1),
        (202, 9, 1, 1, 4, 2),
        (203, 9, 1, 1, 3, 3),
        (204, 9, 1, 1, 4, 4),
        (205, 9, 1, 1, 4, 5),
        (206, 9, 2, 1, 4, 1),
        (207, 9, 2, 1, 4, 2),
        (208, 9, 2, 1, 3, 3),
        (209, 9, 2, 1, 4, 4),
        (210, 9, 2, 1, 4, 5),
        (211, 9, 3, 1, 2, 1),
        (212, 9, 3, 1, 2, 2),
        (213, 9, 3, 1, 2, 3),
        (214, 9, 3, 1, 3, 4),
        (215, 9, 3, 1, 3, 5),
        (216, 9, 4, 1, 2, 1),
        (217, 9, 4, 1, 2, 2),
        (218, 9, 4, 1, 2, 3),
        (219, 9, 4, 1, 3, 4),
        (220, 9, 4, 1, 3, 5),
        (221, 9, 5, 1, 2, 1),
        (222, 9, 5, 1, 2, 2),
        (223, 9, 5, 1, 2, 3),
        (224, 9, 5, 1, 3, 4),
        (225, 9, 5, 1, 3, 5),
        (226, 10, 1, 1, 1, 1),
        (227, 10, 1, 1, 1, 2),
        (228, 10, 1, 1, 2, 3),
        (229, 10, 1, 1, 3, 4),
        (230, 10, 1, 1, 3, 5),
        (231, 10, 2, 1, 2, 1),
        (232, 10, 2, 1, 2, 2),
        (233, 10, 2, 1, 2, 3),
        (234, 10, 2, 1, 3, 4),
        (235, 10, 2, 1, 3, 5),
        (236, 10, 3, 1, 2, 1),
        (237, 10, 3, 1, 2, 2),
        (238, 10, 3, 1, 2, 3),
        (239, 10, 3, 1, 3, 4),
        (240, 10, 3, 1, 3, 5),
        (241, 10, 4, 1, 2, 1),
        (242, 10, 4, 1, 2, 2),
        (243, 10, 4, 1, 2, 3),
        (244, 10, 4, 1, 3, 4),
        (245, 10, 4, 1, 3, 5),
        (246, 10, 5, 1, 2, 1),
        (247, 10, 5, 1, 2, 2),
        (248, 10, 5, 1, 2, 3),
        (249, 10, 5, 1, 3, 4),
        (250, 10, 5, 1, 3, 5),
        (251, 11, 1, 1, 2, 1),
        (252, 11, 1, 1, 2, 2),
        (253, 11, 1, 1, 2, 3),
        (254, 11, 1, 1, 3, 4),
        (255, 11, 1, 1, 3, 5),
        (256, 11, 2, 2, 4, 1),
        (257, 11, 2, 2, 4, 2),
        (258, 11, 2, 2, 2, 3),
        (259, 11, 2, 2, 4, 4),
        (260, 11, 2, 2, 4, 5),
        (261, 11, 3, 1, 2, 1),
        (262, 11, 3, 1, 2, 2),
        (263, 11, 3, 1, 2, 3),
        (264, 11, 3, 1, 3, 4),
        (265, 11, 3, 1, 3, 5),
        (266, 11, 4, 1, 1, 1),
        (267, 11, 4, 1, 1, 2),
        (268, 11, 4, 1, 1, 3),
        (269, 11, 4, 1, 2, 4),
        (270, 11, 4, 1, 2, 5),
        (271, 11, 5, 2, 2, 1),
        (272, 11, 5, 2, 2, 2),
        (273, 11, 5, 2, 2, 3),
        (274, 11, 5, 2, 4, 4),
        (275, 11, 5, 2, 4, 5),
        (276, 12, 1, 1, 1, 1),
        (277, 12, 1, 1, 1, 2),
        (278, 12, 1, 1, 1, 3),
        (279, 12, 1, 1, 2, 4),
        (280, 12, 1, 1, 2, 5),
        (281, 12, 2, 2, 4, 1),
        (282, 12, 2, 2, 4, 2),
        (283, 12, 2, 2, 2, 3),
        (284, 12, 2, 2, 2, 4),
        (285, 12, 2, 2, 2, 5),
        (286, 12, 3, 1, 2, 1),
        (287, 12, 3, 1, 2, 2),
        (288, 12, 3, 1, 3, 3),
        (289, 12, 3, 1, 3, 4),
        (290, 12, 3, 1, 3, 5),
        (291, 12, 4, 1, 1, 1),
        (292, 12, 4, 1, 1, 2),
        (293, 12, 4, 1, 1, 3),
        (294, 12, 4, 1, 1, 4),
        (295, 12, 4, 1, 1, 5),
        (296, 12, 5, 2, 2, 1),
        (297, 12, 5, 2, 2, 2),
        (298, 12, 5, 2, 2, 3),
        (299, 12, 5, 2, 2, 4),
        (300, 12, 5, 2, 2, 5),
        (301, 13, 1, 1, 1, 1),
        (302, 13, 1, 1, 1, 2),
        (303, 13, 1, 1, 1, 3),
        (304, 13, 1, 1, 2, 4),
        (305, 13, 1, 1, 2, 5),
        (306, 13, 2, 2, 2, 1),
        (307, 13, 2, 2, 2, 2),
        (308, 13, 2, 2, 2, 3),
        (309, 13, 2, 2, 2, 4),
        (310, 13, 2, 2, 2, 5),
        (311, 13, 3, 1, 2, 1),
        (312, 13, 3, 1, 2, 2),
        (313, 13, 3, 1, 2, 3),
        (314, 13, 3, 1, 3, 4),
        (315, 13, 3, 1, 3, 5),
        (316, 13, 4, 1, 1, 1),
        (317, 13, 4, 1, 1, 2),
        (318, 13, 4, 1, 1, 3),
        (319, 13, 4, 1, 1, 4),
        (320, 13, 4, 1, 1, 5),
        (321, 13, 5, 2, 2, 1),
        (322, 13, 5, 2, 2, 2),
        (323, 13, 5, 0, 0, 3),
        (324, 13, 5, 0, 0, 4),
        (325, 13, 5, 0, 0, 5),
        (326, 14, 1, 1, 1, 1),
        (327, 14, 1, 1, 1, 2),
        (328, 14, 1, 1, 2, 3),
        (329, 14, 1, 1, 2, 4),
        (330, 14, 1, 1, 2, 5),
        (331, 14, 2, 2, 2, 1),
        (332, 14, 2, 2, 2, 2),
        (333, 14, 2, 2, 4, 3),
        (334, 14, 2, 2, 4, 4),
        (335, 14, 2, 2, 4, 5),
        (336, 14, 3, 1, 2, 1),
        (337, 14, 3, 1, 2, 2),
        (338, 14, 3, 1, 2, 3),
        (339, 14, 3, 1, 3, 4),
        (340, 14, 3, 1, 3, 5),
        (341, 14, 4, 1, 1, 1),
        (342, 14, 4, 1, 1, 2),
        (343, 14, 4, 0, 0, 3),
        (344, 14, 4, 1, 1, 4),
        (345, 14, 4, 1, 1, 5),
        (346, 14, 5, 0, 0, 1),
        (347, 14, 5, 0, 0, 2),
        (348, 14, 5, 0, 0, 3),
        (349, 14, 5, 0, 0, 4),
        (350, 14, 5, 0, 0, 5),
        (351, 15, 1, 1, 2, 1),
        (352, 15, 1, 1, 2, 2),
        (353, 15, 1, 1, 3, 3),
        (354, 15, 1, 1, 2, 4),
        (355, 15, 1, 1, 2, 5),
        (356, 15, 2, 2, 4, 1),
        (357, 15, 2, 2, 4, 2),
        (358, 15, 2, 2, 4, 3),
        (359, 15, 2, 2, 6, 4),
        (360, 15, 2, 2, 6, 5),
        (361, 15, 3, 1, 2, 1),
        (362, 15, 3, 1, 2, 2),
        (363, 15, 3, 1, 3, 3),
        (364, 15, 3, 1, 3, 4),
        (365, 15, 3, 1, 3, 5),
        (366, 15, 4, 1, 1, 1),
        (367, 15, 4, 1, 1, 2),
        (368, 15, 4, 1, 1, 3),
        (369, 15, 4, 1, 2, 4),
        (370, 15, 4, 1, 2, 5),
        (371, 15, 5, 2, 2, 1),
        (372, 15, 5, 2, 2, 2),
        (373, 15, 5, 2, 2, 3),
        (374, 15, 5, 2, 4, 4),
        (375, 15, 5, 2, 4, 5),
        (376, 16, 1, 1, 1, 1),
        (377, 16, 1, 1, 1, 2),
        (378, 16, 1, 0, 0, 3),
        (379, 16, 1, 0, 0, 4),
        (380, 16, 1, 0, 0, 5),
        (381, 16, 2, 2, 2, 1),
        (382, 16, 2, 2, 2, 2),
        (383, 16, 2, 0, 0, 3),
        (384, 16, 2, 0, 0, 4),
        (385, 16, 2, 0, 0, 5),
        (386, 16, 3, 1, 2, 1),
        (387, 16, 3, 1, 2, 2),
        (388, 16, 3, 1, 2, 3),
        (389, 16, 3, 1, 3, 4),
        (390, 16, 3, 1, 3, 5),
        (391, 16, 4, 1, 1, 1),
        (392, 16, 4, 1, 1, 2),
        (393, 16, 4, 0, 0, 3),
        (394, 16, 4, 0, 0, 4),
        (395, 16, 4, 0, 0, 5),
        (396, 16, 5, 0, 0, 1),
        (397, 16, 5, 0, 0, 2),
        (398, 16, 5, 0, 0, 3),
        (399, 16, 5, 0, 0, 4),
        (400, 16, 5, 0, 0, 5),
        (401, 17, 1, 1, 2, 1),
        (402, 17, 1, 1, 2, 2),
        (403, 17, 1, 1, 2, 3),
        (404, 17, 1, 1, 3, 4),
        (405, 17, 1, 1, 3, 5),
        (406, 17, 2, 2, 4, 1),
        (407, 17, 2, 2, 4, 2),
        (408, 17, 2, 2, 2, 3),
        (409, 17, 2, 2, 4, 4),
        (410, 17, 2, 2, 4, 5),
        (411, 17, 3, 1, 2, 1),
        (412, 17, 3, 1, 2, 2),
        (413, 17, 3, 1, 2, 3),
        (414, 17, 3, 1, 3, 4),
        (415, 17, 3, 1, 3, 5),
        (416, 17, 4, 1, 1, 1),
        (417, 17, 4, 1, 1, 2),
        (418, 17, 4, 1, 1, 3),
        (419, 17, 4, 1, 1, 4),
        (420, 17, 4, 1, 1, 5),
        (421, 17, 5, 2, 2, 1),
        (422, 17, 5, 2, 2, 2),
        (423, 17, 5, 2, 2, 3),
        (424, 17, 5, 2, 4, 4),
        (425, 17, 5, 2, 4, 5),
        (426, 18, 1, 1, 2, 1),
        (427, 18, 1, 1, 2, 2),
        (428, 18, 1, 1, 2, 3),
        (429, 18, 1, 1, 3, 4),
        (430, 18, 1, 1, 3, 5),
        (431, 18, 2, 2, 4, 1),
        (432, 18, 2, 2, 4, 2),
        (433, 18, 2, 2, 2, 3),
        (434, 18, 2, 2, 4, 4),
        (435, 18, 2, 2, 4, 5),
        (436, 18, 3, 1, 2, 1),
        (437, 18, 3, 1, 2, 2),
        (438, 18, 3, 1, 2, 3),
        (439, 18, 3, 1, 3, 4),
        (440, 18, 3, 1, 3, 5),
        (441, 18, 4, 1, 1, 1),
        (442, 18, 4, 1, 1, 2),
        (443, 18, 4, 1, 1, 3),
        (444, 18, 4, 1, 1, 4),
        (445, 18, 4, 1, 1, 5),
        (446, 18, 5, 2, 2, 1),
        (447, 18, 5, 2, 2, 2),
        (448, 18, 5, 2, 2, 3),
        (449, 18, 5, 2, 4, 4),
        (450, 18, 5, 2, 4, 5),
        (451, 19, 1, 1, 1, 1),
        (452, 19, 1, 1, 1, 2),
        (453, 19, 1, 0, 0, 3),
        (454, 19, 1, 0, 0, 4),
        (455, 19, 1, 0, 0, 5),
        (456, 19, 2, 1, 1, 1),
        (457, 19, 2, 1, 1, 2),
        (458, 19, 2, 0, 0, 3),
        (459, 19, 2, 0, 0, 4),
        (460, 19, 2, 0, 0, 5),
        (461, 19, 3, 1, 2, 1),
        (462, 19, 3, 1, 2, 2),
        (463, 19, 3, 1, 2, 3),
        (464, 19, 3, 1, 3, 4),
        (465, 19, 3, 1, 3, 5),
        (466, 19, 4, 1, 1, 1),
        (467, 19, 4, 1, 1, 2),
        (468, 19, 4, 0, 0, 3),
        (469, 19, 4, 1, 1, 4),
        (470, 19, 4, 1, 1, 5),
        (471, 19, 5, 2, 2, 1),
        (472, 19, 5, 2, 2, 2),
        (473, 19, 5, 2, 2, 3),
        (474, 19, 5, 2, 2, 4),
        (475, 19, 5, 2, 2, 5),
        (476, 20, 1, 1, 1, 1),
        (477, 20, 1, 1, 1, 2),
        (478, 20, 1, 0, 0, 3),
        (479, 20, 1, 0, 0, 4),
        (480, 20, 1, 0, 0, 5),
        (481, 20, 2, 0, 0, 1),
        (482, 20, 2, 0, 0, 2),
        (483, 20, 2, 0, 0, 3),
        (484, 20, 2, 0, 0, 4),
        (485, 20, 2, 0, 0, 5),
        (486, 20, 3, 1, 1, 1),
        (487, 20, 3, 1, 1, 2),
        (488, 20, 3, 1, 1, 3),
        (489, 20, 3, 1, 1, 4),
        (490, 20, 3, 1, 1, 5),
        (491, 20, 4, 0, 0, 1),
        (492, 20, 4, 0, 0, 2),
        (493, 20, 4, 0, 0, 3),
        (494, 20, 4, 0, 0, 4),
        (495, 20, 4, 0, 0, 5),
        (496, 20, 5, 0, 0, 1),
        (497, 20, 5, 0, 0, 2),
        (498, 20, 5, 0, 0, 3),
        (499, 20, 5, 0, 0, 4),
        (500, 20, 5, 0, 0, 5),
        (501, 21, 1, 1, 2, 1),
        (502, 21, 1, 1, 2, 2),
        (503, 21, 1, 1, 2, 3),
        (504, 21, 1, 1, 2, 4),
        (505, 21, 1, 1, 2, 5),
        (506, 21, 2, 2, 4, 1),
        (507, 21, 2, 2, 4, 2),
        (508, 21, 2, 2, 2, 3),
        (509, 21, 2, 2, 4, 4),
        (510, 21, 2, 2, 4, 5),
        (511, 21, 3, 1, 2, 1),
        (512, 21, 3, 1, 2, 2),
        (513, 21, 3, 1, 2, 3),
        (514, 21, 3, 1, 3, 4),
        (515, 21, 3, 1, 3, 5),
        (516, 21, 4, 1, 2, 1),
        (517, 21, 4, 1, 2, 2),
        (518, 21, 4, 1, 1, 3),
        (519, 21, 4, 1, 2, 4),
        (520, 21, 4, 1, 2, 5),
        (521, 21, 5, 2, 4, 1),
        (522, 21, 5, 2, 4, 2),
        (523, 21, 5, 2, 2, 3),
        (524, 21, 5, 2, 4, 4),
        (525, 21, 5, 2, 4, 5),
        (526, 22, 1, 1, 2, 1),
        (527, 22, 1, 1, 2, 2),
        (528, 22, 1, 1, 2, 3),
        (529, 22, 1, 1, 3, 4),
        (530, 22, 1, 1, 3, 5),
        (531, 22, 2, 1, 2, 1),
        (532, 22, 2, 1, 2, 2),
        (533, 22, 2, 1, 2, 3),
        (534, 22, 2, 1, 3, 4),
        (535, 22, 2, 1, 3, 5),
        (536, 22, 3, 1, 2, 1),
        (537, 22, 3, 1, 2, 2),
        (538, 22, 3, 1, 2, 3),
        (539, 22, 3, 1, 3, 4),
        (540, 22, 3, 1, 3, 5),
        (541, 22, 4, 1, 1, 1),
        (542, 22, 4, 1, 1, 2),
        (543, 22, 4, 1, 2, 3),
        (544, 22, 4, 1, 3, 4),
        (545, 22, 4, 1, 3, 5),
        (546, 22, 5, 1, 1, 1),
        (547, 22, 5, 1, 1, 2),
        (548, 22, 5, 1, 2, 3),
        (549, 22, 5, 1, 3, 4),
        (550, 22, 5, 1, 3, 5),
        (551, 23, 1, 1, 1, 1),
        (552, 23, 1, 1, 1, 2),
        (553, 23, 1, 1, 2, 3),
        (554, 23, 1, 1, 3, 4),
        (555, 23, 1, 1, 3, 5),
        (556, 23, 2, 1, 1, 1),
        (557, 23, 2, 1, 1, 2),
        (558, 23, 2, 1, 2, 3),
        (559, 23, 2, 1, 3, 4),
        (560, 23, 2, 1, 3, 5),
        (561, 23, 3, 1, 1, 1),
        (562, 23, 3, 1, 1, 2),
        (563, 23, 3, 1, 2, 3),
        (564, 23, 3, 1, 3, 4),
        (565, 23, 3, 1, 3, 5),
        (566, 23, 4, 1, 1, 1),
        (567, 23, 4, 1, 1, 2),
        (568, 23, 4, 1, 2, 3),
        (569, 23, 4, 1, 3, 4),
        (570, 23, 4, 1, 3, 5),
        (571, 23, 5, 1, 1, 1),
        (572, 23, 5, 1, 1, 2),
        (573, 23, 5, 1, 2, 3),
        (574, 23, 5, 1, 3, 4),
        (575, 23, 5, 1, 3, 5),
        (576, 24, 1, 1, 1, 1),
        (577, 24, 1, 1, 1, 2),
        (578, 24, 1, 1, 2, 3),
        (579, 24, 1, 1, 3, 4),
        (580, 24, 1, 1, 3, 5),
        (581, 24, 2, 1, 1, 1),
        (582, 24, 2, 1, 1, 2),
        (583, 24, 2, 1, 2, 3),
        (584, 24, 2, 1, 3, 4),
        (585, 24, 2, 1, 3, 5),
        (586, 24, 3, 1, 1, 1),
        (587, 24, 3, 1, 1, 2),
        (588, 24, 3, 1, 2, 3),
        (589, 24, 3, 1, 3, 4),
        (590, 24, 3, 1, 3, 5),
        (591, 24, 4, 1, 1, 1),
        (592, 24, 4, 1, 1, 2),
        (593, 24, 4, 1, 2, 3),
        (594, 24, 4, 1, 3, 4),
        (595, 24, 4, 1, 3, 5),
        (596, 24, 5, 1, 1, 1),
        (597, 24, 5, 1, 1, 2),
        (598, 24, 5, 1, 2, 3),
        (599, 24, 5, 1, 3, 4),
        (600, 24, 5, 1, 3, 5),
        (601, 25, 1, 1, 2, 1),
        (602, 25, 1, 1, 2, 2),
        (603, 25, 1, 1, 1, 3),
        (604, 25, 1, 1, 2, 4),
        (605, 25, 1, 1, 2, 5),
        (606, 25, 2, 2, 4, 1),
        (607, 25, 2, 2, 4, 2),
        (608, 25, 2, 2, 2, 3),
        (609, 25, 2, 2, 4, 4),
        (610, 25, 2, 2, 4, 5),
        (611, 25, 3, 1, 2, 1),
        (612, 25, 3, 1, 2, 2),
        (613, 25, 3, 1, 2, 3),
        (614, 25, 3, 1, 3, 4),
        (615, 25, 3, 1, 3, 5),
        (616, 25, 4, 1, 1, 1),
        (617, 25, 4, 1, 1, 2),
        (618, 25, 4, 1, 1, 3),
        (619, 25, 4, 1, 1, 4),
        (620, 25, 4, 1, 1, 5),
        (621, 25, 5, 1, 1, 1),
        (622, 25, 5, 2, 2, 2),
        (623, 25, 5, 2, 2, 3),
        (624, 25, 5, 2, 4, 4),
        (625, 25, 5, 2, 4, 5),
        (626, 26, 1, 1, 2, 1),
        (627, 26, 1, 1, 2, 2),
        (628, 26, 1, 1, 2, 3),
        (629, 26, 1, 1, 3, 4),
        (630, 26, 1, 1, 3, 5),
        (631, 26, 2, 2, 4, 1),
        (632, 26, 2, 2, 4, 2),
        (633, 26, 2, 2, 4, 3),
        (634, 26, 2, 2, 4, 4),
        (635, 26, 2, 2, 4, 5),
        (636, 26, 3, 1, 2, 1),
        (637, 26, 3, 1, 2, 2),
        (638, 26, 3, 1, 2, 3),
        (639, 26, 3, 1, 3, 4),
        (640, 26, 3, 1, 3, 5),
        (641, 26, 4, 1, 1, 1),
        (642, 26, 4, 1, 1, 2),
        (643, 26, 4, 1, 1, 3),
        (644, 26, 4, 1, 1, 4),
        (645, 26, 4, 1, 1, 5),
        (646, 26, 5, 1, 1, 1),
        (647, 26, 5, 2, 2, 2),
        (648, 26, 5, 2, 4, 3),
        (649, 26, 5, 2, 4, 4),
        (650, 26, 5, 2, 4, 5),
        (651, 27, 1, 1, 1, 1),
        (652, 27, 1, 0, 0, 2),
        (653, 27, 1, 0, 0, 3),
        (654, 27, 1, 0, 0, 4),
        (655, 27, 1, 0, 0, 5),
        (656, 27, 2, 0, 0, 1),
        (657, 27, 2, 0, 0, 2),
        (658, 27, 2, 0, 0, 3),
        (659, 27, 2, 0, 0, 4),
        (660, 27, 2, 0, 0, 5),
        (661, 27, 3, 1, 1, 1),
        (662, 27, 3, 1, 1, 2),
        (663, 27, 3, 0, 0, 3),
        (664, 27, 3, 1, 3, 4),
        (665, 27, 3, 1, 3, 5),
        (666, 27, 4, 1, 1, 1),
        (667, 27, 4, 1, 1, 2),
        (668, 27, 4, 1, 1, 3),
        (669, 27, 4, 1, 1, 4),
        (670, 27, 4, 1, 1, 5),
        (671, 27, 5, 2, 2, 1),
        (672, 27, 5, 2, 2, 2),
        (673, 27, 5, 1, 1, 3),
        (674, 27, 5, 2, 4, 4),
        (675, 27, 5, 2, 4, 5),
        (676, 28, 4, 1, 2, 3),
        (677, 29, 2, 2, 2, 5),
        (678, 29, 3, 1, 2, 5),
        (679, 28, 4, 1, 3, 4),
        (680, 28, 2, 1, 2, 1),
        (681, 28, 2, 1, 2, 3),
        (682, 28, 2, 1, 3, 5),
        (683, 29, 3, 1, 2, 1),
        (684, 29, 3, 1, 2, 3),
        (685, 29, 2, 0, 0, 2),
        (686, 29, 1, 1, 1, 4),
        (687, 29, 1, 1, 1, 1),
        (688, 29, 4, 1, 1, 5),
        (689, 29, 4, 0, 0, 3),
        (690, 29, 1, 1, 1, 5),
        (691, 29, 4, 1, 1, 1),
        (692, 29, 1, 0, 0, 3),
        (693, 29, 5, 0, 0, 3),
        (694, 29, 5, 0, 0, 4),
        (695, 29, 5, 0, 0, 1),
        (696, 28, 2, 1, 3, 4),
        (697, 28, 5, 1, 2, 2),
        (698, 28, 5, 1, 3, 5),
        (699, 28, 3, 1, 3, 5),
        (700, 28, 3, 1, 2, 3),
        (701, 29, 2, 2, 2, 4),
        (702, 28, 4, 1, 2, 1),
        (703, 28, 1, 1, 2, 1),
        (704, 28, 4, 1, 3, 5),
        (705, 28, 2, 1, 2, 2),
        (706, 28, 1, 1, 2, 3),
        (707, 29, 2, 0, 0, 1),
        (708, 29, 2, 0, 0, 3),
        (709, 28, 4, 1, 2, 2),
        (710, 29, 3, 1, 2, 4),
        (711, 29, 3, 1, 2, 2),
        (712, 29, 4, 1, 1, 4),
        (713, 29, 4, 1, 1, 2),
        (714, 29, 1, 1, 1, 2),
        (715, 29, 5, 0, 0, 2),
        (716, 28, 3, 1, 2, 2),
        (717, 29, 5, 0, 0, 5),
        (718, 28, 1, 1, 3, 5),
        (719, 28, 5, 1, 3, 4),
        (720, 28, 5, 1, 2, 3),
        (721, 28, 5, 1, 2, 1),
        (722, 28, 3, 1, 3, 4),
        (723, 28, 3, 1, 2, 1),
        (724, 28, 1, 1, 3, 4),
        (725, 28, 1, 1, 2, 2),
        (726, 30, 1, 1, 2, 1),
        (727, 30, 1, 1, 2, 2),
        (728, 30, 1, 0, 2, 3),
        (729, 30, 1, 0, 2, 4),
        (730, 30, 1, 0, 1, 5),
        (731, 30, 2, 1, 2, 1),
        (732, 30, 2, 1, 2, 2),
        (733, 30, 2, 0, 1, 3),
        (734, 30, 2, 0, 1, 4),
        (735, 30, 2, 0, 1, 5),
        (736, 30, 3, 0, 0, 1),
        (737, 30, 3, 0, 0, 2),
        (738, 30, 3, 0, 0, 3),
        (739, 30, 3, 0, 0, 4),
        (740, 30, 3, 0, 0, 5),
        (741, 30, 4, 1, 1, 1),
        (742, 30, 4, 1, 1, 2),
        (743, 30, 4, 0, 1, 3),
        (744, 30, 4, 0, 1, 4),
        (745, 30, 4, 0, 1, 5),
        (746, 30, 5, 1, 1, 1),
        (747, 30, 5, 1, 1, 2),
        (748, 30, 5, 0, 1, 3),
        (749, 30, 5, 0, 1, 4),
        (750, 30, 5, 0, 1, 5),
    )
    MAP = {(t[1], t[2], t[5]): (t[3], t[4]) for t in VALUES}

    @classmethod
    def get_min_max(cls, muscle_group_id, phase_id, fitness_level_id):
        key = (muscle_group_id, phase_id, fitness_level_id)
        return cls.MAP[key]


class CardioVolume(object):
    # queries by fitness level, phase, and week

    # this is originally VolumeTable
    # id, fitnessLevel_id, phase_id, week, minTimedCardio, maxTimedCardio

    VALUES = (
        (1, 1, 1, 1, 2, 2),
        (2, 1, 1, 2, 2, 2),
        (3, 1, 1, 3, 2, 3),
        (4, 1, 1, 4, 2, 3),
        (5, 1, 1, 5, 2, 4),
        (6, 1, 1, 6, 2, 4),
        (7, 1, 2, 1, 3, 3),
        (8, 1, 2, 2, 3, 3),
        (9, 1, 2, 3, 3, 3),
        (10, 1, 2, 4, 3, 3),
        (11, 1, 2, 5, 3, 3),
        (12, 1, 2, 6, 3, 3),
        (13, 1, 3, 1, 2, 5),
        (14, 1, 3, 2, 2, 5),
        (15, 1, 3, 3, 2, 5),
        (16, 1, 3, 4, 2, 5),
        (17, 1, 3, 5, 2, 5),
        (18, 1, 3, 6, 2, 5),
        (19, 1, 4, 1, 0, 1),
        (20, 1, 4, 2, 0, 1),
        (21, 1, 4, 3, 0, 1),
        (22, 1, 4, 4, 0, 1),
        (23, 1, 4, 5, 0, 1),
        (24, 1, 4, 6, 0, 1),
        (25, 1, 5, 1, 1, 2),
        (26, 1, 5, 2, 1, 2),
        (27, 1, 5, 3, 1, 2),
        (28, 1, 5, 4, 1, 2),
        (29, 1, 5, 5, 1, 2),
        (30, 1, 5, 6, 1, 2),
        (31, 2, 1, 1, 2, 2),
        (32, 2, 1, 2, 2, 3),
        (33, 2, 1, 3, 2, 3),
        (34, 2, 1, 4, 2, 4),
        (35, 2, 1, 5, 2, 4),
        (36, 2, 1, 6, 2, 4),
        (37, 2, 2, 1, 3, 3),
        (38, 2, 2, 2, 3, 3),
        (39, 2, 2, 3, 3, 4),
        (40, 2, 2, 4, 3, 4),
        (41, 2, 2, 5, 3, 4),
        (42, 2, 2, 6, 3, 4),
        (43, 2, 3, 1, 2, 2),
        (44, 2, 3, 2, 2, 2),
        (45, 2, 3, 3, 2, 2),
        (46, 2, 3, 4, 2, 2),
        (47, 2, 3, 5, 2, 2),
        (48, 2, 3, 6, 2, 2),
        (49, 2, 4, 1, 0, 1),
        (50, 2, 4, 2, 0, 1),
        (51, 2, 4, 3, 0, 1),
        (52, 2, 4, 4, 0, 1),
        (53, 2, 4, 5, 0, 1),
        (54, 2, 4, 6, 0, 1),
        (55, 2, 5, 1, 1, 2),
        (56, 2, 5, 2, 1, 2),
        (57, 2, 5, 3, 1, 2),
        (58, 2, 5, 4, 1, 2),
        (59, 2, 5, 5, 1, 2),
        (60, 2, 5, 6, 1, 2),
        (61, 3, 1, 1, 3, 3),
        (62, 3, 1, 2, 3, 3),
        (63, 3, 1, 3, 3, 4),
        (64, 3, 1, 4, 3, 4),
        (65, 3, 1, 5, 3, 4),
        (66, 3, 1, 6, 3, 4),
        (67, 3, 2, 1, 2, 6),
        (68, 3, 2, 2, 2, 6),
        (69, 3, 2, 3, 2, 6),
        (70, 3, 2, 4, 2, 6),
        (71, 3, 2, 5, 2, 6),
        (72, 3, 2, 6, 2, 6),
        (73, 3, 3, 1, 2, 2),
        (74, 3, 3, 2, 2, 2),
        (75, 3, 3, 3, 2, 2),
        (76, 3, 3, 4, 2, 2),
        (77, 3, 3, 5, 2, 2),
        (78, 3, 3, 6, 2, 2),
        (79, 3, 4, 1, 0, 2),
        (80, 3, 4, 2, 0, 2),
        (81, 3, 4, 3, 0, 2),
        (82, 3, 4, 4, 0, 2),
        (83, 3, 4, 5, 0, 2),
        (84, 3, 4, 6, 0, 2),
        (85, 3, 5, 1, 2, 3),
        (86, 3, 5, 2, 2, 3),
        (87, 3, 5, 3, 2, 3),
        (88, 3, 5, 4, 2, 3),
        (89, 3, 5, 5, 2, 3),
        (90, 3, 5, 6, 2, 3),
        (91, 4, 1, 1, 3, 4),
        (92, 4, 1, 2, 3, 4),
        (93, 4, 1, 3, 3, 4),
        (94, 4, 1, 4, 3, 4),
        (95, 4, 1, 5, 3, 4),
        (96, 4, 1, 6, 3, 4),
        (97, 4, 2, 1, 3, 3),
        (98, 4, 2, 2, 3, 3),
        (99, 4, 2, 3, 3, 4),
        (100, 4, 2, 4, 3, 5),
        (101, 4, 2, 5, 3, 5),
        (102, 4, 2, 6, 3, 5),
        (103, 4, 3, 1, 2, 3),
        (104, 4, 3, 2, 2, 3),
        (105, 4, 3, 3, 2, 3),
        (106, 4, 3, 4, 2, 3),
        (107, 4, 3, 5, 2, 3),
        (108, 4, 3, 6, 2, 3),
        (109, 4, 4, 1, 0, 2),
        (110, 4, 4, 2, 0, 2),
        (111, 4, 4, 3, 0, 2),
        (112, 4, 4, 4, 0, 2),
        (113, 4, 4, 5, 0, 2),
        (114, 4, 4, 6, 0, 2),
        (115, 4, 5, 1, 2, 4),
        (116, 4, 5, 2, 2, 44),
        (117, 4, 5, 3, 2, 4),
        (118, 4, 5, 4, 2, 4),
        (119, 4, 5, 5, 2, 4),
        (120, 4, 5, 6, 2, 4),
        (121, 5, 1, 1, 3, 4),
        (122, 5, 1, 2, 3, 4),
        (123, 5, 1, 3, 3, 4),
        (124, 5, 1, 4, 3, 4),
        (125, 5, 1, 5, 3, 4),
        (126, 5, 1, 6, 3, 4),
        (127, 5, 2, 1, 4, 4),
        (128, 5, 2, 2, 4, 4),
        (129, 5, 2, 3, 4, 4),
        (130, 5, 2, 4, 4, 5),
        (131, 5, 2, 5, 4, 5),
        (132, 5, 2, 6, 4, 6),
        (133, 5, 3, 1, 2, 4),
        (134, 5, 3, 2, 2, 4),
        (135, 5, 3, 3, 2, 4),
        (136, 5, 3, 4, 2, 4),
        (137, 5, 3, 5, 2, 4),
        (138, 5, 3, 6, 2, 4),
        (139, 5, 4, 1, 0, 3),
        (140, 5, 4, 2, 0, 3),
        (141, 5, 4, 3, 0, 3),
        (142, 5, 4, 4, 0, 3),
        (143, 5, 4, 5, 0, 3),
        (144, 5, 4, 6, 0, 3),
        (145, 5, 5, 1, 2, 4),
        (146, 5, 5, 2, 2, 4),
        (147, 5, 5, 3, 2, 4),
        (148, 5, 5, 4, 2, 4),
        (149, 5, 5, 5, 2, 4),
        (150, 5, 5, 6, 2, 4),
    )

    MAP = {(t[1], t[2], t[3]): t for t in VALUES}

    class VolumeInfo(object):

        def __init__(self, cardio_row, lifting_row):
            self.min_reps = lifting_row[1]
            self.max_reps = lifting_row[2]

            self.min_sets = lifting_row[3]
            self.max_sets = lifting_row[4]

            self.min_exercises = lifting_row[5]
            self.max_exercises = lifting_row[6]

    @classmethod
    def get_all_volume_info(cls, phase_id, fitness_level_id, week, workout_component_id):
        key = (fitness_level_id, phase_id, week)
        cardio_row = cls.MAP[key]
        id = cardio_row[0]
        lifting_row = LiftingVolume.get(id, workout_component_id)
        return cls.VolumeInfo(cardio_row, lifting_row)

    @classmethod
    def get_min_max_cardio(cls, phase_id, fitness_level_id, week):
        key = (fitness_level_id, phase_id, week)
        cardio_row = cls.MAP[key]
        return cardio_row[4], cardio_row[5]


class LiftingVolume(object):
    # this is originally Volume

    # queries by workout_component_id and parent_table_id

    # id, minReps, maxReps, minSets, maxSets, minExercises, maxExercises,
    # workoutComponent_id, parentTable_id, maxTotalReps

    # parentTable_id references the fucking cardio table
    VALUES = (
        (1, 20, 30, 1, 3, 3, 3, 1, 1, 1000),
        (2, 12, 12, 1, 1, 1, 2, 2, 1, 1000),
        (3, 12, 12, 1, 1, 1, 2, 3, 1, 1000),
        (4, 5, 5, 1, 1, 1, 1, 4, 1, 1000),
        (5, 12, 12, 1, 1, 4, 6, 5, 1, 1000),

        (6, 20, 30, 1, 3, 3, 3, 1, 2, 1000),
        (7, 15, 15, 2, 2, 1, 2, 2, 2, 1000),
        (8, 15, 15, 2, 2, 1, 2, 3, 2, 1000),
        (9, 5, 5, 2, 2, 1, 1, 4, 2, 1000),
        (10, 15, 15, 2, 2, 4, 6, 5, 2, 1000),

        (11, 20, 30, 1, 3, 3, 3, 1, 3, 1000),
        (12, 20, 20, 2, 2, 1, 2, 2, 3, 1000),
        (13, 20, 20, 2, 2, 1, 2, 3, 3, 1000),
        (14, 6, 6, 2, 2, 1, 1, 4, 3, 1000),
        (15, 20, 20, 2, 2, 4, 6, 5, 3, 1000),

        (16, 20, 30, 1, 3, 3, 3, 1, 4, 1000),
        (17, 20, 20, 3, 3, 1, 2, 2, 4, 1000),
        (18, 20, 20, 3, 3, 1, 2, 3, 4, 1000),
        (19, 8, 8, 2, 2, 1, 1, 4, 4, 1000),
        (20, 20, 20, 3, 3, 4, 6, 5, 4, 1000),

        (21, 20, 30, 1, 3, 3, 3, 1, 5, 1000),
        (22, 15, 15, 3, 3, 1, 2, 2, 5, 1000),
        (23, 15, 15, 3, 3, 1, 2, 3, 5, 1000),
        (24, 6, 6, 3, 3, 1, 1, 4, 5, 1000),
        (25, 15, 20, 3, 3, 4, 6, 5, 5, 1000),

        (26, 20, 30, 1, 3, 3, 3, 1, 6, 1000),
        (27, 15, 20, 2, 3, 1, 2, 2, 6, 1000),
        (28, 15, 20, 2, 3, 1, 2, 3, 6, 1000),
        (29, 6, 8, 2, 3, 1, 1, 4, 6, 1000),
        (30, 12, 20, 2, 3, 4, 6, 5, 6, 1000),

        (31, 20, 30, 1, 3, 3, 6, 1, 7, 1000),
        (32, 12, 12, 2, 2, 1, 2, 2, 7, 1000),
        (33, 12, 12, 2, 2, 1, 2, 3, 7, 1000),
        (34, 8, 8, 2, 2, 1, 2, 4, 7, 1000),
        (35, 12, 12, 2, 2, 3, 5, 5, 7, 1000),

        (36, 20, 30, 1, 3, 3, 6, 1, 8, 1000),
        (37, 12, 12, 2, 2, 1, 2, 2, 8, 1000),
        (38, 12, 12, 2, 2, 1, 2, 3, 8, 1000),
        (39, 8, 8, 2, 2, 1, 2, 4, 8, 1000),
        (40, 12, 12, 2, 2, 3, 5, 5, 8, 1000),

        (41, 20, 30, 1, 3, 3, 6, 1, 9, 1000),
        (42, 12, 12, 2, 2, 1, 2, 2, 9, 1000),
        (43, 12, 12, 2, 2, 1, 2, 3, 9, 1000),
        (44, 8, 8, 2, 2, 1, 2, 4, 9, 1000),
        (45, 10, 10, 2, 2, 3, 5, 5, 9, 1000),

        (46, 20, 30, 1, 3, 3, 6, 1, 10, 1000),
        (47, 12, 12, 2, 2, 1, 2, 2, 10, 1000),
        (48, 12, 12, 2, 2, 1, 2, 3, 10, 1000),
        (49, 8, 8, 2, 2, 1, 2, 4, 10, 1000),
        (50, 10, 10, 2, 2, 3, 5, 5, 10, 1000),

        (51, 20, 30, 1, 3, 3, 6, 1, 11, 1000),
        (52, 10, 12, 2, 2, 1, 2, 2, 11, 1000),
        (53, 10, 12, 2, 2, 1, 2, 3, 11, 1000),
        (54, 6, 8, 2, 2, 1, 2, 4, 11, 1000),
        (55, 10, 12, 2, 2, 3, 5, 5, 11, 1000),

        (56, 20, 30, 1, 3, 3, 6, 1, 12, 1000),
        (57, 10, 12, 2, 2, 1, 2, 2, 12, 1000),
        (58, 10, 12, 2, 2, 1, 2, 3, 12, 1000),
        (59, 6, 8, 2, 2, 1, 2, 4, 12, 1000),
        (60, 10, 12, 2, 2, 3, 5, 5, 12, 1000),

        (61, 20, 30, 1, 3, 1, 3, 1, 13, 1000),
        (62, 8, 12, 2, 3, 1, 4, 2, 13, 1000),
        (63, 8, 12, 2, 3, 1, 3, 3, 13, 1000),
        (64, 8, 10, 1, 1, 1, 2, 4, 13, 1000),
        (65, 12, 12, 3, 3, 3, 4, 5, 13, 1000),

        (66, 20, 30, 1, 3, 1, 3, 1, 14, 1000),
        (67, 8, 12, 2, 3, 1, 4, 2, 14, 1000),
        (68, 8, 12, 2, 3, 1, 3, 3, 14, 1000),
        (69, 8, 10, 1, 1, 1, 2, 4, 14, 1000),
        (70, 10, 10, 3, 3, 3, 4, 5, 14, 1000),

        (71, 20, 30, 1, 3, 1, 3, 1, 15, 1000),
        (72, 8, 12, 2, 3, 1, 4, 2, 15, 1000),
        (73, 8, 12, 2, 3, 1, 3, 3, 15, 1000),
        (74, 8, 10, 1, 2, 1, 2, 4, 15, 1000),
        (75, 8, 8, 4, 4, 3, 4, 5, 15, 1000),

        (76, 20, 30, 1, 3, 1, 3, 1, 16, 1000),
        (77, 8, 12, 2, 3, 1, 4, 2, 16, 1000),
        (78, 8, 12, 2, 3, 1, 3, 3, 16, 1000),
        (79, 8, 10, 2, 2, 1, 2, 4, 16, 1000),
        (80, 6, 6, 5, 5, 3, 4, 5, 16, 1000),

        (81, 20, 30, 1, 3, 1, 3, 1, 17, 1000),
        (82, 8, 12, 2, 3, 1, 4, 2, 17, 1000),
        (83, 8, 12, 2, 3, 1, 3, 3, 17, 1000),
        (84, 8, 10, 2, 2, 1, 2, 4, 17, 1000),
        (85, 6, 12, 3, 5, 3, 4, 5, 17, 1000),

        (86, 20, 30, 1, 3, 1, 3, 1, 18, 1000),
        (87, 8, 12, 2, 3, 1, 4, 2, 18, 1000),
        (88, 8, 12, 2, 3, 1, 3, 3, 18, 1000),
        (89, 8, 10, 2, 3, 1, 2, 4, 18, 1000),
        (90, 6, 12, 3, 5, 3, 4, 5, 18, 1000),

        (91, 20, 30, 1, 3, 3, 6, 1, 19, 1000),
        (92, 8, 12, 2, 3, 1, 3, 2, 19, 1000),
        (93, 8, 12, 2, 3, 1, 2, 3, 19, 1000),
        (94, 8, 10, 1, 2, 1, 2, 4, 19, 1000),
        (95, 5, 5, 4, 4, 2, 2, 5, 19, 20),

        (96, 20, 30, 1, 3, 3, 6, 1, 20, 1000),
        (97, 8, 12, 2, 3, 1, 3, 2, 20, 1000),
        (98, 8, 12, 2, 3, 1, 2, 3, 20, 1000),
        (99, 8, 10, 1, 2, 1, 2, 4, 20, 1000),
        (100, 5, 5, 5, 5, 2, 2, 5, 20, 25),

        (101, 20, 30, 1, 3, 3, 6, 1, 21, 1000),
        (102, 8, 12, 2, 3, 1, 3, 2, 21, 1000),
        (103, 8, 12, 2, 3, 1, 2, 3, 21, 1000),
        (104, 8, 10, 1, 2, 1, 2, 4, 21, 1000),
        (105, 4, 4, 5, 5, 2, 2, 5, 21, 20),
        (106, 20, 30, 1, 3, 3, 6, 1, 22, 999),
        (107, 8, 12, 2, 3, 1, 3, 2, 22, 1000),
        (108, 8, 12, 2, 3, 1, 2, 3, 22, 1000),
        (109, 8, 10, 1, 2, 1, 2, 4, 22, 1000),
        (110, 3, 3, 6, 6, 2, 2, 5, 22, 18),
        (111, 20, 30, 1, 3, 3, 6, 1, 23, 1000),
        (112, 8, 12, 2, 3, 1, 3, 2, 23, 1000),
        (113, 8, 12, 2, 3, 1, 2, 3, 23, 1000),
        (114, 8, 10, 1, 2, 1, 2, 4, 23, 1000),
        (115, 3, 6, 3, 6, 2, 2, 5, 23, 20),
        (116, 20, 30, 1, 3, 3, 6, 1, 24, 1000),
        (117, 8, 12, 2, 3, 1, 3, 2, 24, 1000),
        (118, 8, 12, 2, 3, 1, 2, 3, 24, 1000),
        (119, 8, 10, 1, 2, 1, 2, 4, 24, 1000),
        (120, 3, 6, 3, 6, 2, 2, 5, 24, 20),
        (121, 20, 30, 1, 3, 3, 5, 1, 25, 1000),
        (122, 12, 12, 2, 2, 1, 2, 2, 25, 1000),
        (123, 12, 12, 2, 2, 1, 2, 3, 25, 1000),
        (124, 8, 8, 2, 2, 1, 1, 4, 25, 1000),
        (125, 10, 10, 3, 3, 4, 6, 5, 25, 30),
        (126, 20, 30, 1, 3, 3, 5, 1, 26, 1000),
        (127, 12, 12, 2, 2, 1, 2, 2, 26, 1000),
        (128, 12, 12, 2, 2, 1, 2, 3, 26, 1000),
        (129, 8, 8, 2, 2, 1, 1, 4, 26, 1000),
        (130, 10, 10, 4, 4, 4, 6, 5, 26, 40),
        (131, 20, 30, 1, 3, 3, 5, 1, 27, 1000),
        (132, 10, 10, 3, 3, 1, 2, 2, 27, 1000),
        (133, 10, 10, 3, 3, 1, 2, 3, 27, 1000),
        (134, 8, 8, 3, 3, 1, 1, 4, 27, 1000),
        (135, 8, 8, 4, 4, 4, 6, 5, 27, 32),
        (136, 20, 30, 1, 3, 3, 5, 1, 28, 1000),
        (137, 8, 8, 3, 3, 1, 2, 2, 28, 1000),
        (138, 8, 8, 3, 3, 1, 2, 3, 28, 1000),
        (139, 10, 10, 3, 3, 1, 1, 4, 28, 1000),
        (140, 8, 8, 3, 5, 4, 6, 5, 28, 40),
        (141, 20, 30, 1, 3, 3, 5, 1, 29, 1000),
        (142, 8, 12, 2, 3, 1, 2, 2, 29, 1000),
        (143, 8, 12, 2, 3, 1, 2, 3, 29, 1000),
        (144, 8, 12, 1, 3, 1, 1, 4, 29, 1000),
        (145, 8, 10, 3, 6, 4, 6, 5, 29, 48),
        (146, 20, 30, 1, 3, 3, 5, 1, 30, 1000),
        (147, 8, 12, 2, 3, 1, 2, 2, 30, 1000),
        (148, 8, 12, 2, 3, 1, 2, 3, 30, 1000),
        (149, 8, 12, 1, 3, 1, 1, 4, 30, 1000),
        (150, 8, 10, 3, 6, 4, 6, 5, 30, 48),
        (151, 20, 30, 1, 3, 3, 3, 1, 31, 1000),
        (152, 12, 12, 1, 1, 1, 2, 2, 31, 1000),
        (153, 12, 12, 1, 1, 1, 2, 3, 31, 1000),
        (154, 5, 5, 1, 1, 1, 1, 4, 31, 1000),
        (155, 12, 12, 1, 1, 3, 6, 5, 31, 1000),
        (156, 20, 30, 1, 3, 3, 3, 1, 32, 1000),
        (157, 15, 15, 2, 2, 1, 2, 2, 32, 1000),
        (158, 15, 15, 2, 2, 1, 2, 3, 32, 1000),
        (159, 5, 5, 2, 2, 1, 1, 4, 32, 1000),
        (160, 15, 15, 2, 2, 3, 6, 5, 32, 1000),
        (161, 20, 30, 1, 3, 3, 3, 1, 33, 1000),
        (162, 20, 20, 2, 2, 1, 2, 2, 33, 1000),
        (163, 20, 20, 2, 2, 1, 2, 3, 33, 1000),
        (164, 6, 6, 2, 2, 1, 1, 4, 33, 1000),
        (165, 20, 20, 2, 2, 3, 6, 5, 33, 1000),
        (166, 20, 30, 1, 3, 3, 3, 1, 34, 1000),
        (167, 20, 20, 3, 3, 1, 2, 2, 34, 1000),
        (168, 20, 20, 3, 3, 1, 2, 3, 34, 1000),
        (169, 8, 8, 2, 2, 1, 1, 4, 34, 1000),
        (170, 20, 20, 3, 3, 3, 6, 5, 34, 1000),
        (171, 20, 30, 1, 3, 3, 3, 1, 35, 1000),
        (172, 15, 15, 3, 3, 1, 2, 2, 35, 1000),
        (173, 15, 15, 3, 3, 1, 2, 3, 35, 1000),
        (174, 6, 6, 3, 3, 1, 1, 4, 35, 1000),
        (175, 15, 20, 3, 3, 3, 6, 5, 35, 1000),
        (176, 20, 30, 1, 3, 3, 3, 1, 36, 1000),
        (177, 15, 20, 2, 3, 1, 2, 2, 36, 1000),
        (178, 15, 20, 2, 3, 1, 2, 3, 36, 1000),
        (179, 6, 8, 2, 3, 1, 1, 4, 36, 1000),
        (180, 12, 20, 2, 3, 3, 6, 5, 36, 1000),
        (181, 20, 30, 1, 3, 3, 6, 1, 37, 1000),
        (182, 12, 12, 2, 2, 1, 2, 2, 37, 1000),
        (183, 12, 12, 2, 2, 1, 2, 3, 37, 1000),
        (184, 8, 8, 2, 2, 1, 2, 4, 37, 1000),
        (185, 12, 12, 2, 2, 3, 6, 5, 37, 1000),
        (186, 20, 30, 1, 3, 3, 6, 1, 38, 1000),
        (187, 12, 12, 2, 2, 1, 2, 2, 38, 1000),
        (188, 12, 12, 2, 2, 1, 2, 3, 38, 1000),
        (189, 8, 8, 2, 2, 1, 2, 4, 38, 1000),
        (190, 12, 12, 2, 2, 3, 6, 5, 38, 1000),
        (191, 20, 30, 1, 3, 3, 6, 1, 39, 1000),
        (192, 12, 12, 2, 2, 1, 2, 2, 39, 1000),
        (193, 12, 12, 2, 2, 1, 2, 3, 39, 1000),
        (194, 8, 8, 2, 2, 1, 2, 4, 39, 1000),
        (195, 10, 10, 2, 2, 3, 6, 5, 39, 1000),
        (196, 20, 30, 1, 3, 3, 6, 1, 40, 1000),
        (197, 12, 12, 2, 2, 1, 2, 2, 40, 1000),
        (198, 12, 12, 2, 2, 1, 2, 3, 40, 1000),
        (199, 8, 8, 2, 2, 1, 2, 4, 40, 1000),
        (200, 10, 10, 2, 2, 3, 6, 5, 40, 1000),
        (201, 20, 30, 1, 3, 3, 6, 1, 41, 1000),
        (202, 10, 12, 2, 2, 1, 2, 2, 41, 1000),
        (203, 10, 12, 2, 2, 1, 2, 3, 41, 1000),
        (204, 6, 8, 2, 2, 1, 2, 4, 41, 1000),
        (205, 10, 12, 2, 2, 3, 6, 5, 41, 1000),
        (206, 20, 30, 1, 3, 3, 6, 1, 42, 1000),
        (207, 10, 12, 2, 2, 1, 2, 2, 42, 1000),
        (208, 10, 12, 2, 2, 1, 2, 3, 42, 1000),
        (209, 6, 8, 2, 2, 1, 2, 4, 42, 1000),
        (210, 10, 12, 2, 2, 3, 6, 5, 42, 1000),
        (211, 20, 30, 1, 3, 1, 3, 1, 43, 1000),
        (212, 8, 12, 2, 3, 1, 4, 2, 43, 1000),
        (213, 8, 12, 2, 3, 1, 2, 3, 43, 1000),
        (214, 8, 10, 1, 2, 1, 1, 4, 43, 1000),
        (215, 12, 12, 3, 3, 4, 5, 5, 43, 1000),
        (216, 20, 30, 1, 3, 1, 3, 1, 44, 1000),
        (217, 8, 12, 2, 3, 1, 4, 2, 44, 1000),
        (218, 8, 12, 2, 3, 1, 2, 3, 44, 1000),
        (219, 8, 10, 1, 2, 1, 1, 4, 44, 1000),
        (220, 10, 10, 3, 3, 4, 5, 5, 44, 1000),
        (221, 20, 30, 2, 3, 1, 3, 1, 45, 1000),
        (222, 8, 12, 2, 3, 1, 4, 2, 45, 1000),
        (223, 8, 12, 2, 3, 1, 2, 3, 45, 1000),
        (224, 8, 10, 2, 3, 1, 1, 4, 45, 1000),
        (225, 8, 8, 4, 4, 4, 5, 5, 45, 1000),
        (226, 20, 30, 1, 3, 1, 3, 1, 46, 1000),
        (227, 8, 12, 2, 3, 1, 4, 2, 46, 1000),
        (228, 8, 12, 2, 2, 1, 2, 3, 46, 1000),
        (229, 8, 10, 2, 3, 1, 1, 4, 46, 1000),
        (230, 6, 6, 5, 5, 4, 5, 5, 46, 1000),
        (231, 20, 30, 1, 3, 1, 3, 1, 47, 1000),
        (232, 8, 12, 2, 3, 1, 4, 2, 47, 1000),
        (233, 8, 12, 2, 3, 1, 2, 3, 47, 1000),
        (234, 8, 10, 2, 3, 1, 1, 4, 47, 1000),
        (235, 6, 12, 3, 5, 4, 5, 5, 47, 1000),
        (236, 20, 30, 1, 3, 1, 3, 1, 48, 1000),
        (237, 8, 12, 2, 3, 1, 4, 2, 48, 1000),
        (238, 8, 12, 2, 3, 1, 2, 3, 48, 1000),
        (239, 8, 10, 2, 3, 1, 1, 4, 48, 1000),
        (240, 6, 12, 3, 5, 4, 5, 5, 48, 1000),
        (241, 20, 30, 1, 3, 3, 6, 1, 49, 1000),
        (242, 8, 12, 2, 3, 1, 3, 2, 49, 1000),
        (243, 8, 12, 2, 3, 1, 2, 3, 49, 1000),
        (244, 8, 10, 1, 2, 1, 2, 4, 49, 1000),
        (245, 5, 5, 4, 4, 2, 3, 5, 49, 20),
        (246, 20, 30, 1, 3, 3, 6, 1, 50, 1000),
        (247, 8, 12, 2, 3, 1, 3, 2, 50, 1000),
        (248, 8, 12, 2, 3, 1, 2, 3, 50, 1000),
        (249, 8, 10, 1, 2, 1, 2, 4, 50, 1000),
        (250, 5, 5, 5, 5, 2, 3, 5, 50, 25),
        (251, 20, 30, 1, 3, 3, 6, 1, 51, 1000),
        (252, 8, 12, 2, 3, 1, 3, 2, 51, 1000),
        (253, 8, 12, 2, 3, 1, 2, 3, 51, 1000),
        (254, 8, 10, 1, 2, 1, 2, 4, 51, 1000),
        (255, 4, 4, 5, 5, 2, 3, 5, 51, 20),
        (256, 20, 30, 1, 3, 3, 6, 1, 52, 1000),
        (257, 8, 12, 2, 3, 1, 3, 2, 52, 1000),
        (258, 8, 12, 2, 3, 1, 2, 3, 52, 1000),
        (259, 8, 10, 1, 2, 1, 2, 4, 52, 1000),
        (260, 3, 3, 6, 6, 2, 3, 5, 52, 18),
        (261, 20, 30, 1, 3, 3, 6, 1, 53, 1000),
        (262, 8, 12, 2, 3, 1, 3, 2, 53, 1000),
        (263, 8, 12, 2, 3, 1, 2, 3, 53, 1000),
        (264, 8, 10, 1, 2, 1, 2, 4, 53, 1000),
        (265, 3, 6, 3, 6, 2, 3, 5, 53, 25),
        (266, 20, 30, 1, 3, 3, 6, 1, 54, 1000),
        (267, 8, 12, 2, 3, 1, 3, 2, 54, 1000),
        (268, 8, 12, 2, 3, 1, 2, 3, 54, 1000),
        (269, 8, 10, 1, 2, 1, 2, 4, 54, 1000),
        (270, 3, 6, 3, 6, 2, 3, 5, 54, 25),
        (271, 20, 30, 1, 3, 3, 5, 1, 55, 1000),
        (272, 12, 12, 2, 2, 1, 2, 2, 55, 1000),
        (273, 12, 12, 2, 2, 1, 2, 3, 55, 1000),
        (274, 8, 8, 2, 2, 1, 2, 4, 55, 1000),
        (275, 10, 10, 3, 3, 4, 6, 5, 55, 30),
        (276, 20, 30, 1, 3, 3, 5, 1, 56, 1000),
        (277, 12, 12, 2, 2, 1, 2, 2, 56, 1000),
        (278, 12, 12, 2, 2, 1, 2, 3, 56, 1000),
        (279, 8, 8, 2, 2, 1, 2, 4, 56, 1000),
        (280, 10, 10, 4, 4, 4, 6, 5, 56, 40),
        (281, 20, 30, 1, 3, 3, 5, 1, 57, 1000),
        (282, 10, 10, 3, 3, 1, 2, 2, 57, 1000),
        (283, 10, 10, 3, 3, 1, 2, 3, 57, 1000),
        (284, 8, 8, 3, 3, 1, 2, 4, 57, 1000),
        (285, 8, 8, 4, 4, 4, 6, 5, 57, 32),
        (286, 20, 30, 1, 3, 3, 5, 1, 58, 1000),
        (287, 8, 8, 3, 3, 1, 2, 2, 58, 1000),
        (288, 8, 8, 3, 3, 1, 2, 3, 58, 1000),
        (289, 10, 10, 3, 3, 1, 2, 4, 58, 1000),
        (290, 8, 8, 5, 5, 4, 6, 5, 58, 40),
        (291, 20, 30, 1, 3, 3, 5, 1, 59, 1000),
        (292, 8, 12, 2, 3, 1, 2, 2, 59, 1000),
        (293, 8, 12, 2, 3, 1, 2, 3, 59, 1000),
        (294, 8, 10, 1, 3, 1, 2, 4, 59, 1000),
        (295, 8, 10, 3, 6, 4, 6, 5, 59, 48),
        (296, 20, 30, 1, 3, 3, 5, 1, 60, 1000),
        (297, 8, 12, 2, 3, 1, 2, 2, 60, 1000),
        (298, 8, 12, 2, 3, 1, 2, 3, 60, 1000),
        (299, 8, 10, 1, 3, 1, 2, 4, 60, 1000),
        (300, 8, 10, 3, 6, 4, 6, 5, 60, 48),
        (301, 20, 30, 1, 3, 3, 5, 1, 61, 1000),
        (302, 20, 20, 1, 1, 2, 3, 2, 61, 1000),
        (303, 20, 20, 1, 1, 2, 2, 3, 61, 1000),
        (304, 6, 6, 1, 1, 2, 3, 4, 61, 1000),
        (305, 20, 20, 1, 2, 4, 6, 5, 61, 1000),
        (306, 20, 30, 1, 3, 3, 5, 1, 62, 1000),
        (307, 20, 20, 2, 2, 2, 3, 2, 62, 1000),
        (308, 20, 20, 2, 2, 2, 2, 3, 62, 1000),
        (309, 6, 6, 2, 2, 2, 3, 4, 62, 1000),
        (310, 15, 15, 2, 2, 4, 6, 5, 62, 1000),
        (311, 20, 30, 1, 3, 3, 5, 1, 63, 1000),
        (312, 15, 15, 3, 3, 2, 3, 2, 63, 1000),
        (313, 15, 15, 3, 3, 2, 2, 3, 63, 1000),
        (314, 6, 6, 3, 3, 2, 3, 4, 63, 1000),
        (315, 15, 15, 3, 3, 4, 6, 5, 63, 1000),
        (316, 20, 30, 1, 3, 3, 5, 1, 64, 1000),
        (317, 15, 15, 3, 3, 2, 3, 2, 64, 1000),
        (318, 15, 15, 3, 3, 2, 2, 3, 64, 1000),
        (319, 8, 8, 3, 3, 2, 3, 4, 64, 1000),
        (320, 12, 12, 3, 3, 4, 6, 5, 64, 1000),
        (321, 20, 30, 1, 3, 3, 5, 1, 65, 1000),
        (322, 15, 20, 1, 3, 2, 3, 2, 65, 1000),
        (323, 15, 20, 1, 3, 2, 2, 3, 65, 1000),
        (324, 6, 8, 2, 3, 2, 3, 4, 65, 1000),
        (325, 15, 20, 2, 3, 4, 6, 5, 65, 1000),
        (326, 20, 30, 1, 3, 3, 5, 1, 66, 1000),
        (327, 12, 15, 1, 3, 2, 3, 2, 66, 1000),
        (328, 12, 15, 1, 3, 2, 2, 3, 66, 1000),
        (329, 6, 8, 1, 3, 2, 3, 4, 66, 1000),
        (330, 12, 15, 2, 3, 4, 6, 5, 66, 1000),
        (331, 20, 30, 1, 3, 3, 6, 1, 67, 1000),
        (332, 12, 12, 2, 2, 2, 3, 2, 67, 1000),
        (333, 12, 12, 2, 2, 1, 2, 3, 67, 1000),
        (334, 8, 8, 2, 2, 2, 3, 4, 67, 1000),
        (335, 12, 12, 2, 2, 3, 6, 5, 67, 1000),
        (336, 20, 30, 1, 3, 3, 6, 1, 68, 1000),
        (337, 12, 12, 2, 2, 2, 3, 2, 68, 1000),
        (338, 12, 12, 2, 2, 1, 2, 3, 68, 1000),
        (339, 8, 8, 3, 3, 2, 3, 4, 68, 1000),
        (340, 10, 10, 3, 3, 3, 6, 5, 68, 1000),
        (341, 20, 30, 1, 3, 3, 6, 1, 69, 1000),
        (342, 10, 10, 3, 3, 2, 3, 2, 69, 1000),
        (343, 10, 10, 3, 3, 1, 2, 3, 69, 1000),
        (344, 10, 10, 3, 3, 2, 3, 4, 69, 1000),
        (345, 8, 8, 3, 3, 3, 6, 5, 69, 1000),
        (346, 20, 30, 1, 3, 3, 6, 1, 70, 1000),
        (347, 8, 8, 3, 3, 2, 3, 2, 70, 1000),
        (348, 8, 8, 3, 3, 1, 2, 3, 70, 1000),
        (349, 10, 10, 3, 3, 2, 3, 4, 70, 1000),
        (350, 8, 8, 4, 4, 3, 6, 5, 70, 1000),
        (351, 20, 30, 1, 3, 3, 6, 1, 71, 1000),
        (352, 8, 8, 3, 3, 2, 3, 2, 71, 1000),
        (353, 8, 8, 3, 3, 1, 2, 3, 71, 1000),
        (354, 8, 10, 2, 3, 2, 3, 4, 71, 1000),
        (355, 8, 12, 3, 4, 3, 6, 5, 71, 1000),
        (356, 20, 30, 1, 3, 3, 6, 1, 72, 1000),
        (357, 8, 12, 2, 3, 2, 3, 2, 72, 1000),
        (358, 8, 12, 2, 3, 1, 2, 3, 72, 1000),
        (359, 8, 10, 2, 4, 2, 3, 4, 72, 1000),
        (360, 8, 12, 2, 4, 3, 6, 5, 72, 1000),
        (361, 20, 30, 1, 3, 1, 2, 1, 73, 1000),
        (362, 8, 12, 2, 3, 1, 4, 2, 73, 1000),
        (363, 8, 12, 2, 3, 1, 2, 3, 73, 1000),
        (364, 8, 10, 2, 3, 1, 2, 4, 73, 1000),
        (365, 12, 12, 3, 3, 4, 5, 5, 73, 1000),
        (366, 20, 30, 1, 3, 1, 2, 1, 74, 1000),
        (367, 8, 12, 2, 3, 1, 4, 2, 74, 1000),
        (368, 8, 12, 2, 3, 1, 2, 3, 74, 1000),
        (369, 8, 10, 2, 3, 1, 2, 4, 74, 1000),
        (370, 10, 10, 3, 3, 4, 5, 5, 74, 1000),
        (371, 20, 30, 1, 3, 1, 2, 1, 75, 1000),
        (372, 8, 12, 2, 3, 1, 4, 2, 75, 1000),
        (373, 8, 12, 2, 3, 1, 2, 3, 75, 1000),
        (374, 8, 10, 2, 3, 1, 2, 4, 75, 1000),
        (375, 8, 8, 4, 4, 4, 5, 5, 75, 1000),
        (376, 20, 30, 1, 3, 1, 2, 1, 76, 1000),
        (377, 8, 12, 2, 3, 1, 4, 2, 76, 1000),
        (378, 8, 12, 2, 3, 1, 2, 3, 76, 1000),
        (379, 8, 10, 2, 3, 1, 2, 4, 76, 1000),
        (380, 6, 6, 5, 5, 4, 5, 5, 76, 1000),
        (381, 20, 30, 1, 3, 1, 2, 1, 77, 1000),
        (382, 8, 12, 2, 3, 1, 4, 2, 77, 1000),
        (383, 8, 12, 2, 3, 1, 2, 3, 77, 1000),
        (384, 8, 10, 2, 3, 1, 2, 4, 77, 1000),
        (385, 6, 12, 3, 5, 4, 5, 5, 77, 1000),
        (386, 20, 30, 1, 3, 1, 2, 1, 78, 1000),
        (387, 8, 12, 2, 3, 1, 4, 2, 78, 1000),
        (388, 8, 12, 2, 3, 1, 2, 3, 78, 1000),
        (389, 8, 10, 2, 3, 1, 2, 4, 78, 1000),
        (390, 6, 12, 3, 5, 4, 5, 5, 78, 1000),
        (391, 20, 30, 1, 3, 3, 6, 1, 79, 1000),
        (392, 8, 12, 2, 3, 1, 4, 2, 79, 1000),
        (393, 8, 12, 2, 3, 1, 2, 3, 79, 1000),
        (394, 8, 10, 2, 3, 1, 3, 4, 79, 1000),
        (395, 5, 5, 4, 4, 3, 3, 5, 79, 20),
        (396, 20, 30, 1, 3, 3, 6, 1, 80, 1000),
        (397, 8, 12, 2, 3, 1, 4, 2, 80, 1000),
        (398, 8, 12, 2, 3, 1, 2, 3, 80, 1000),
        (399, 8, 10, 2, 3, 1, 3, 4, 80, 1000),
        (400, 5, 5, 5, 5, 3, 3, 5, 80, 25),
        (401, 20, 30, 1, 3, 3, 6, 1, 81, 1000),
        (402, 8, 12, 2, 3, 1, 4, 2, 81, 1000),
        (403, 8, 12, 2, 3, 1, 2, 3, 81, 1000),
        (404, 8, 10, 2, 3, 1, 3, 4, 81, 1000),
        (405, 4, 4, 5, 5, 3, 3, 5, 81, 20),
        (406, 20, 30, 1, 3, 3, 6, 1, 82, 1000),
        (407, 8, 12, 2, 3, 1, 4, 2, 82, 1000),
        (408, 8, 12, 2, 3, 1, 2, 3, 82, 1000),
        (409, 8, 10, 2, 3, 1, 3, 4, 82, 1000),
        (410, 3, 3, 6, 6, 3, 3, 5, 82, 18),
        (411, 20, 30, 1, 3, 3, 6, 1, 83, 1000),
        (412, 8, 12, 2, 3, 1, 4, 2, 83, 1000),
        (413, 8, 12, 2, 3, 1, 2, 3, 83, 1000),
        (414, 8, 10, 2, 3, 1, 3, 4, 83, 1000),
        (415, 3, 6, 3, 6, 3, 3, 5, 83, 25),
        (416, 20, 30, 1, 3, 3, 6, 1, 84, 1000),
        (417, 8, 12, 2, 3, 1, 4, 2, 84, 1000),
        (418, 8, 12, 2, 3, 1, 2, 3, 84, 1000),
        (419, 8, 10, 2, 3, 1, 3, 4, 84, 1000),
        (420, 3, 6, 3, 6, 3, 3, 5, 84, 25),
        (421, 20, 30, 1, 3, 3, 5, 1, 85, 1000),
        (422, 12, 12, 2, 2, 1, 2, 2, 85, 1000),
        (423, 12, 12, 2, 2, 1, 2, 3, 85, 1000),
        (424, 8, 8, 2, 4, 1, 2, 4, 85, 1000),
        (425, 10, 10, 3, 3, 6, 6, 5, 85, 30),
        (426, 20, 30, 1, 3, 3, 5, 1, 86, 1000),
        (427, 12, 12, 2, 2, 1, 2, 2, 86, 1000),
        (428, 12, 12, 2, 2, 1, 2, 3, 86, 1000),
        (429, 8, 8, 3, 3, 1, 2, 4, 86, 1000),
        (430, 10, 10, 4, 4, 6, 6, 5, 86, 40),
        (431, 20, 30, 1, 3, 3, 5, 1, 87, 1000),
        (432, 10, 10, 3, 3, 1, 2, 2, 87, 1000),
        (433, 10, 10, 3, 3, 1, 2, 3, 87, 1000),
        (434, 10, 10, 3, 3, 1, 2, 4, 87, 1000),
        (435, 8, 8, 4, 4, 6, 6, 5, 87, 32),
        (436, 20, 30, 1, 3, 3, 5, 1, 88, 1000),
        (437, 8, 8, 3, 3, 1, 2, 2, 88, 1000),
        (438, 8, 8, 3, 3, 1, 2, 3, 88, 1000),
        (439, 10, 10, 3, 3, 1, 2, 4, 88, 1000),
        (440, 8, 8, 5, 5, 6, 6, 5, 88, 40),
        (441, 20, 30, 1, 3, 3, 5, 1, 89, 1000),
        (442, 8, 12, 2, 3, 1, 2, 2, 89, 1000),
        (443, 8, 12, 2, 3, 1, 2, 3, 89, 1000),
        (444, 8, 12, 2, 3, 1, 2, 4, 89, 1000),
        (445, 8, 10, 3, 6, 6, 6, 5, 89, 48),
        (446, 20, 30, 1, 3, 3, 5, 1, 90, 1000),
        (447, 8, 12, 2, 3, 1, 2, 2, 90, 1000),
        (448, 8, 12, 2, 3, 1, 2, 3, 90, 1000),
        (449, 8, 12, 2, 3, 1, 2, 4, 90, 1000),
        (450, 8, 10, 3, 6, 6, 6, 5, 90, 48),
        (451, 20, 30, 1, 3, 3, 6, 1, 91, 1000),
        (452, 20, 20, 1, 1, 2, 3, 2, 91, 1000),
        (453, 20, 20, 1, 1, 1, 2, 3, 91, 1000),
        (454, 6, 6, 1, 1, 2, 4, 4, 91, 1000),
        (455, 20, 20, 1, 2, 4, 8, 5, 91, 1000),
        (456, 20, 30, 1, 3, 3, 6, 1, 92, 1000),
        (457, 20, 20, 2, 2, 2, 3, 2, 92, 1000),
        (458, 20, 20, 2, 2, 1, 2, 3, 92, 1000),
        (459, 6, 6, 2, 2, 2, 4, 4, 92, 1000),
        (460, 15, 15, 2, 2, 4, 8, 5, 92, 1000),
        (461, 20, 30, 1, 3, 3, 6, 1, 93, 1000),
        (462, 15, 15, 3, 3, 2, 3, 2, 93, 1000),
        (463, 15, 15, 3, 3, 1, 2, 3, 93, 1000),
        (464, 6, 6, 3, 3, 2, 4, 4, 93, 1000),
        (465, 15, 15, 3, 3, 4, 8, 5, 93, 1000),
        (466, 20, 30, 1, 3, 3, 6, 1, 94, 1000),
        (467, 15, 15, 3, 3, 2, 3, 2, 94, 1000),
        (468, 15, 15, 3, 3, 1, 2, 3, 94, 1000),
        (469, 8, 8, 3, 3, 2, 4, 4, 94, 1000),
        (470, 12, 12, 3, 3, 4, 8, 5, 94, 1000),
        (471, 20, 30, 1, 3, 3, 6, 1, 95, 1000),
        (472, 15, 20, 1, 3, 2, 3, 2, 95, 1000),
        (473, 15, 20, 1, 3, 1, 2, 3, 95, 1000),
        (474, 6, 8, 2, 3, 2, 4, 4, 95, 1000),
        (475, 15, 20, 2, 3, 4, 8, 5, 95, 1000),
        (476, 20, 30, 1, 3, 3, 6, 1, 96, 1000),
        (477, 12, 15, 1, 3, 2, 3, 2, 96, 1000),
        (478, 12, 15, 1, 3, 1, 2, 3, 96, 1000),
        (479, 6, 8, 1, 3, 2, 4, 4, 96, 1000),
        (480, 12, 15, 2, 3, 4, 8, 5, 96, 1000),
        (481, 20, 30, 1, 3, 3, 6, 1, 97, 1000),
        (482, 12, 12, 2, 2, 2, 4, 2, 97, 1000),
        (483, 12, 12, 2, 2, 1, 2, 3, 97, 1000),
        (484, 8, 8, 2, 2, 2, 3, 4, 97, 1000),
        (485, 12, 12, 2, 2, 4, 6, 5, 97, 1000),
        (486, 20, 30, 1, 3, 3, 6, 1, 98, 1000),
        (487, 12, 12, 2, 2, 2, 4, 2, 98, 1000),
        (488, 12, 12, 2, 2, 1, 2, 3, 98, 1000),
        (489, 8, 8, 3, 3, 2, 3, 4, 98, 1000),
        (490, 10, 10, 3, 3, 4, 6, 5, 98, 1000),
        (491, 20, 30, 1, 3, 3, 6, 1, 99, 1000),
        (492, 10, 10, 3, 3, 2, 4, 2, 99, 1000),
        (493, 10, 10, 3, 3, 1, 2, 3, 99, 1000),
        (494, 10, 10, 3, 3, 2, 3, 4, 99, 1000),
        (495, 8, 8, 3, 3, 4, 6, 5, 99, 1000),
        (496, 20, 30, 1, 3, 3, 6, 1, 100, 1000),
        (497, 8, 8, 3, 3, 2, 4, 2, 100, 1000),
        (498, 8, 8, 3, 3, 1, 2, 3, 100, 1000),
        (499, 10, 10, 3, 3, 2, 3, 4, 100, 1000),
        (500, 8, 8, 4, 4, 4, 6, 5, 100, 1000),
        (501, 20, 30, 1, 3, 3, 6, 1, 101, 1000),
        (502, 8, 8, 3, 3, 2, 4, 2, 101, 1000),
        (503, 8, 8, 3, 3, 1, 2, 3, 101, 1000),
        (504, 8, 10, 2, 4, 2, 3, 4, 101, 1000),
        (505, 8, 12, 3, 4, 4, 6, 5, 101, 1000),
        (506, 20, 30, 1, 3, 3, 6, 1, 102, 1000),
        (507, 8, 12, 2, 3, 2, 4, 2, 102, 1000),
        (508, 8, 12, 2, 3, 1, 2, 3, 102, 1000),
        (509, 8, 10, 2, 4, 2, 3, 4, 102, 1000),
        (510, 8, 12, 2, 4, 4, 6, 5, 102, 1000),
        (511, 20, 30, 1, 3, 1, 3, 1, 103, 1000),
        (512, 8, 12, 2, 3, 1, 4, 2, 103, 1000),
        (513, 8, 12, 2, 3, 1, 1, 3, 103, 1000),
        (514, 8, 10, 2, 3, 1, 4, 4, 103, 1000),
        (515, 6, 12, 3, 5, 4, 6, 5, 103, 1000),
        (516, 20, 30, 1, 3, 1, 3, 1, 104, 1000),
        (517, 8, 12, 2, 3, 1, 4, 2, 104, 1000),
        (518, 8, 12, 2, 3, 1, 1, 3, 104, 1000),
        (519, 8, 10, 2, 3, 1, 4, 4, 104, 1000),
        (520, 6, 12, 3, 5, 4, 6, 5, 104, 1000),
        (521, 20, 30, 1, 3, 1, 3, 1, 105, 1000),
        (522, 8, 12, 2, 3, 1, 4, 2, 105, 1000),
        (523, 8, 12, 2, 3, 1, 1, 3, 105, 1000),
        (524, 8, 10, 2, 3, 1, 4, 4, 105, 1000),
        (525, 6, 12, 3, 5, 4, 6, 5, 105, 1000),
        (526, 20, 30, 1, 3, 1, 3, 1, 106, 1000),
        (527, 8, 12, 2, 3, 1, 4, 2, 106, 1000),
        (528, 8, 12, 2, 3, 1, 1, 3, 106, 1000),
        (529, 8, 10, 2, 3, 1, 4, 4, 106, 1000),
        (530, 6, 12, 3, 5, 4, 6, 5, 106, 1000),
        (531, 20, 30, 1, 3, 1, 3, 1, 107, 1000),
        (532, 8, 12, 2, 3, 1, 4, 2, 107, 1000),
        (533, 8, 12, 2, 3, 1, 1, 3, 107, 1000),
        (534, 8, 10, 2, 3, 1, 4, 4, 107, 1000),
        (535, 6, 12, 3, 5, 4, 6, 5, 107, 1000),
        (536, 20, 30, 1, 3, 1, 3, 1, 108, 1000),
        (537, 8, 12, 2, 3, 1, 4, 2, 108, 1000),
        (538, 8, 12, 2, 3, 1, 1, 3, 108, 1000),
        (539, 8, 10, 2, 3, 1, 4, 4, 108, 1000),
        (540, 6, 12, 3, 5, 4, 6, 5, 108, 1000),
        (541, 20, 30, 2, 3, 3, 6, 1, 109, 1000),
        (542, 8, 12, 2, 3, 1, 4, 2, 109, 1000),
        (543, 8, 12, 2, 3, 1, 1, 3, 109, 1000),
        (544, 8, 10, 2, 3, 1, 3, 4, 109, 1000),
        (545, 3, 6, 3, 6, 3, 4, 5, 109, 30),
        (546, 20, 30, 1, 3, 3, 6, 1, 110, 1000),
        (547, 8, 12, 2, 3, 1, 4, 2, 110, 1000),
        (548, 8, 12, 2, 3, 1, 1, 3, 110, 1000),
        (549, 8, 10, 2, 3, 1, 3, 4, 110, 1000),
        (550, 3, 6, 3, 6, 3, 4, 5, 110, 30),
        (551, 20, 30, 1, 3, 3, 6, 1, 111, 1000),
        (552, 8, 12, 2, 3, 1, 4, 2, 111, 1000),
        (553, 8, 12, 2, 3, 1, 1, 3, 111, 1000),
        (554, 8, 10, 2, 3, 1, 3, 4, 111, 1000),
        (555, 3, 6, 3, 6, 3, 4, 5, 111, 30),
        (556, 20, 30, 1, 3, 3, 6, 1, 112, 1000),
        (557, 8, 12, 2, 3, 1, 4, 2, 112, 1000),
        (558, 8, 12, 2, 3, 1, 1, 3, 112, 1000),
        (559, 8, 10, 2, 3, 1, 3, 4, 112, 1000),
        (560, 3, 6, 3, 6, 3, 4, 5, 112, 30),
        (561, 20, 30, 1, 3, 3, 6, 1, 113, 1000),
        (562, 8, 12, 2, 3, 1, 4, 2, 113, 1000),
        (563, 8, 12, 2, 3, 1, 1, 3, 113, 1000),
        (564, 8, 10, 2, 3, 1, 3, 4, 113, 1000),
        (565, 3, 3, 3, 6, 3, 4, 5, 113, 30),
        (566, 20, 30, 1, 3, 3, 6, 1, 114, 1000),
        (567, 8, 12, 2, 3, 1, 4, 2, 114, 1000),
        (568, 8, 12, 2, 3, 1, 1, 3, 114, 1000),
        (569, 8, 10, 2, 3, 1, 3, 4, 114, 1000),
        (570, 3, 6, 3, 6, 3, 4, 5, 114, 30),
        (571, 20, 30, 1, 3, 3, 5, 1, 115, 1000),
        (572, 8, 12, 2, 3, 1, 2, 2, 115, 1000),
        (573, 8, 12, 2, 3, 1, 1, 3, 115, 1000),
        (574, 8, 12, 2, 3, 1, 2, 4, 115, 1000),
        (575, 8, 10, 3, 6, 6, 8, 5, 115, 48),
        (576, 20, 30, 1, 3, 3, 5, 1, 116, 1000),
        (577, 8, 12, 2, 3, 1, 2, 2, 116, 1000),
        (578, 8, 12, 2, 3, 1, 1, 3, 116, 1000),
        (579, 8, 12, 2, 3, 1, 2, 4, 116, 1000),
        (580, 8, 10, 3, 6, 6, 8, 5, 116, 48),
        (581, 20, 30, 1, 3, 3, 5, 1, 117, 1000),
        (582, 8, 12, 2, 3, 1, 2, 2, 117, 1000),
        (583, 8, 12, 2, 3, 1, 1, 3, 117, 1000),
        (584, 8, 12, 2, 3, 1, 2, 4, 117, 1000),
        (585, 8, 10, 3, 6, 6, 8, 5, 117, 48),
        (586, 20, 30, 1, 3, 3, 5, 1, 118, 1000),
        (587, 8, 12, 2, 3, 1, 2, 2, 118, 1000),
        (588, 8, 12, 2, 3, 1, 1, 3, 118, 1000),
        (589, 8, 12, 2, 3, 1, 2, 4, 118, 1000),
        (590, 8, 10, 3, 6, 6, 8, 5, 118, 48),
        (591, 20, 30, 1, 3, 3, 5, 1, 119, 1000),
        (592, 8, 12, 2, 3, 1, 2, 2, 119, 1000),
        (593, 8, 12, 2, 3, 1, 1, 3, 119, 1000),
        (594, 8, 12, 2, 3, 1, 2, 4, 119, 1000),
        (595, 8, 10, 3, 6, 6, 8, 5, 119, 48),
        (596, 20, 30, 1, 3, 3, 5, 1, 120, 1000),
        (597, 8, 12, 2, 3, 1, 2, 2, 120, 1000),
        (598, 8, 12, 2, 3, 1, 1, 3, 120, 1000),
        (599, 8, 12, 2, 3, 1, 2, 4, 120, 1000),
        (600, 8, 10, 3, 6, 6, 8, 5, 120, 48),
        (601, 20, 30, 1, 3, 3, 6, 1, 121, 1000),
        (602, 20, 20, 2, 2, 2, 4, 2, 121, 1000),
        (603, 20, 20, 2, 2, 1, 2, 3, 121, 1000),
        (604, 6, 6, 2, 2, 2, 4, 4, 121, 1000),
        (605, 15, 20, 2, 2, 4, 8, 5, 121, 1000),
        (606, 20, 30, 1, 3, 3, 6, 1, 122, 1000),
        (607, 15, 20, 2, 3, 2, 4, 2, 122, 1000),
        (608, 15, 20, 2, 3, 1, 2, 3, 122, 1000),
        (609, 6, 8, 2, 3, 2, 4, 4, 122, 1000),
        (610, 15, 20, 3, 3, 4, 8, 5, 122, 1000),
        (611, 20, 30, 1, 3, 3, 6, 1, 123, 1000),
        (612, 12, 15, 3, 3, 2, 4, 2, 123, 1000),
        (613, 12, 15, 3, 3, 1, 2, 3, 123, 1000),
        (614, 8, 8, 3, 3, 2, 4, 4, 123, 1000),
        (615, 12, 15, 3, 3, 4, 8, 5, 123, 1000),
        (616, 20, 30, 1, 3, 3, 6, 1, 124, 1000),
        (617, 12, 15, 3, 3, 2, 4, 2, 124, 1000),
        (618, 12, 15, 3, 3, 1, 2, 3, 124, 1000),
        (619, 8, 8, 3, 3, 2, 4, 4, 124, 1000),
        (620, 12, 15, 3, 3, 4, 8, 5, 124, 1000),
        (621, 20, 30, 1, 3, 3, 6, 1, 125, 1000),
        (622, 12, 20, 2, 3, 2, 4, 2, 125, 1000),
        (623, 12, 20, 2, 3, 1, 2, 3, 125, 1000),
        (624, 6, 8, 2, 3, 2, 4, 4, 125, 1000),
        (625, 12, 20, 2, 3, 4, 8, 5, 125, 1000),
        (626, 20, 30, 1, 3, 3, 6, 1, 126, 1000),
        (627, 12, 20, 2, 3, 2, 4, 2, 126, 1000),
        (628, 12, 20, 2, 3, 1, 2, 3, 126, 1000),
        (629, 6, 8, 2, 3, 2, 4, 4, 126, 1000),
        (630, 12, 20, 2, 3, 4, 8, 5, 126, 1000),
        (631, 20, 30, 1, 3, 3, 6, 1, 127, 1000),
        (632, 12, 12, 2, 2, 2, 4, 2, 127, 1000),
        (633, 12, 12, 2, 2, 1, 2, 3, 127, 1000),
        (634, 8, 8, 2, 2, 2, 4, 4, 127, 1000),
        (635, 12, 12, 2, 2, 4, 8, 5, 127, 1000),
        (636, 20, 30, 1, 3, 3, 6, 1, 128, 1000),
        (637, 10, 10, 3, 3, 2, 4, 2, 128, 1000),
        (638, 10, 10, 3, 3, 1, 2, 3, 128, 1000),
        (639, 10, 10, 3, 3, 2, 4, 4, 128, 1000),
        (640, 10, 10, 3, 3, 4, 8, 5, 128, 1000),
        (641, 20, 30, 1, 3, 3, 6, 1, 129, 1000),
        (642, 8, 8, 3, 3, 2, 4, 2, 129, 1000),
        (643, 8, 8, 3, 3, 1, 2, 3, 129, 1000),
        (644, 10, 10, 4, 4, 2, 4, 4, 129, 1000),
        (645, 10, 10, 4, 4, 4, 8, 5, 129, 1000),
        (646, 20, 30, 1, 3, 3, 6, 1, 130, 1000),
        (647, 12, 12, 3, 3, 2, 4, 2, 130, 1000),
        (648, 12, 12, 3, 3, 1, 2, 3, 130, 1000),
        (649, 10, 10, 4, 4, 2, 4, 4, 130, 1000),
        (650, 12, 12, 4, 4, 4, 8, 5, 130, 1000),
        (651, 20, 30, 1, 3, 3, 6, 1, 131, 1000),
        (652, 8, 12, 1, 3, 2, 4, 2, 131, 1000),
        (653, 8, 12, 1, 3, 1, 2, 3, 131, 1000),
        (654, 8, 10, 2, 4, 2, 4, 4, 131, 1000),
        (655, 8, 12, 2, 4, 4, 8, 5, 131, 1000),
        (656, 20, 30, 1, 3, 3, 6, 1, 132, 1000),
        (657, 8, 12, 1, 3, 2, 4, 2, 132, 1000),
        (658, 8, 12, 1, 3, 1, 2, 3, 132, 1000),
        (659, 8, 10, 2, 4, 2, 4, 4, 132, 1000),
        (660, 8, 12, 2, 4, 4, 8, 5, 132, 1000),
        (661, 20, 30, 1, 3, 1, 3, 1, 133, 1000),
        (662, 8, 12, 2, 3, 1, 4, 2, 133, 1000),
        (663, 8, 12, 2, 3, 1, 1, 3, 133, 1000),
        (664, 8, 10, 2, 3, 1, 4, 4, 133, 1000),
        (665, 6, 12, 3, 5, 4, 6, 5, 133, 1000),
        (666, 20, 30, 1, 3, 1, 3, 1, 134, 1000),
        (667, 8, 12, 2, 3, 1, 4, 2, 134, 1000),
        (668, 8, 12, 2, 3, 1, 1, 3, 134, 1000),
        (669, 8, 10, 2, 3, 1, 4, 4, 134, 1000),
        (670, 6, 12, 3, 5, 4, 6, 5, 134, 1000),
        (671, 20, 30, 1, 3, 1, 3, 1, 135, 1000),
        (672, 8, 12, 2, 3, 1, 4, 2, 135, 1000),
        (673, 8, 12, 2, 3, 1, 1, 3, 135, 1000),
        (674, 8, 10, 2, 3, 1, 4, 4, 135, 1000),
        (675, 6, 12, 3, 5, 4, 6, 5, 135, 1000),
        (676, 20, 30, 1, 3, 1, 3, 1, 136, 1000),
        (677, 8, 12, 2, 3, 1, 4, 2, 136, 1000),
        (678, 8, 12, 2, 3, 1, 1, 3, 136, 1000),
        (679, 8, 10, 2, 3, 1, 4, 4, 136, 1000),
        (680, 6, 12, 3, 5, 4, 6, 5, 136, 1000),
        (681, 20, 30, 1, 3, 1, 3, 1, 137, 1000),
        (682, 8, 12, 2, 3, 1, 4, 2, 137, 1000),
        (683, 8, 12, 2, 3, 1, 1, 3, 137, 1000),
        (684, 8, 10, 2, 3, 1, 4, 4, 137, 1000),
        (685, 6, 12, 3, 5, 4, 6, 5, 137, 1000),
        (686, 20, 30, 1, 3, 1, 3, 1, 138, 1000),
        (687, 8, 12, 2, 3, 1, 4, 2, 138, 1000),
        (688, 8, 12, 2, 3, 1, 1, 3, 138, 1000),
        (689, 8, 10, 2, 3, 1, 4, 4, 138, 1000),
        (690, 6, 12, 3, 5, 4, 6, 5, 138, 1000),
        (691, 20, 30, 1, 3, 3, 6, 1, 139, 1000),
        (692, 8, 12, 2, 3, 1, 4, 2, 139, 1000),
        (693, 8, 12, 2, 3, 1, 1, 3, 139, 1000),
        (694, 8, 10, 2, 3, 1, 3, 4, 139, 1000),
        (695, 3, 6, 3, 6, 3, 4, 5, 139, 30),
        (696, 20, 30, 1, 3, 3, 6, 1, 140, 1000),
        (697, 8, 12, 2, 3, 1, 4, 2, 140, 1000),
        (698, 8, 12, 2, 3, 1, 1, 3, 140, 1000),
        (699, 8, 10, 2, 3, 1, 3, 4, 140, 1000),
        (700, 3, 6, 3, 6, 3, 4, 5, 140, 30),
        (701, 20, 30, 1, 3, 3, 6, 1, 141, 1000),
        (702, 8, 12, 2, 3, 1, 4, 2, 141, 1000),
        (703, 8, 12, 2, 3, 1, 1, 3, 141, 1000),
        (704, 8, 10, 2, 3, 1, 3, 4, 141, 1000),
        (705, 3, 6, 3, 6, 3, 4, 5, 141, 30),
        (706, 20, 30, 1, 3, 3, 6, 1, 142, 1000),
        (707, 8, 12, 2, 3, 1, 4, 2, 142, 1000),
        (708, 8, 12, 2, 3, 1, 1, 3, 142, 1000),
        (709, 8, 10, 2, 3, 1, 3, 4, 142, 1000),
        (710, 3, 6, 3, 6, 3, 4, 5, 142, 30),
        (711, 20, 30, 1, 3, 3, 6, 1, 143, 1000),
        (712, 8, 12, 2, 3, 1, 4, 2, 143, 1000),
        (713, 8, 12, 2, 3, 1, 1, 3, 143, 1000),
        (714, 8, 10, 2, 3, 1, 3, 4, 143, 1000),
        (715, 3, 6, 3, 6, 3, 4, 5, 143, 30),
        (716, 20, 30, 1, 3, 3, 6, 1, 144, 1000),
        (717, 8, 12, 2, 3, 1, 4, 2, 144, 1000),
        (718, 8, 12, 2, 3, 1, 1, 3, 144, 1000),
        (719, 8, 10, 2, 3, 1, 3, 4, 144, 1000),
        (720, 3, 6, 3, 6, 3, 4, 5, 144, 30),
        (721, 20, 30, 1, 3, 3, 6, 1, 145, 1000),
        (722, 8, 12, 2, 3, 1, 2, 2, 145, 1000),
        (723, 8, 12, 2, 3, 1, 1, 3, 145, 1000),
        (724, 8, 12, 2, 3, 1, 2, 4, 145, 1000),
        (725, 8, 10, 3, 6, 6, 8, 5, 145, 48),
        (726, 20, 30, 1, 3, 3, 6, 1, 146, 1000),
        (727, 8, 12, 2, 3, 1, 2, 2, 146, 1000),
        (728, 8, 12, 2, 3, 1, 1, 3, 146, 1000),
        (729, 8, 12, 2, 3, 1, 2, 4, 146, 1000),
        (730, 8, 10, 3, 6, 6, 8, 5, 146, 48),
        (731, 20, 30, 1, 3, 3, 6, 1, 147, 1000),
        (732, 8, 12, 2, 3, 1, 2, 2, 147, 1000),
        (733, 8, 12, 2, 3, 1, 1, 3, 147, 1000),
        (734, 8, 12, 2, 3, 1, 2, 4, 147, 1000),
        (735, 8, 10, 3, 6, 6, 8, 5, 147, 48),
        (736, 20, 30, 1, 3, 3, 6, 1, 148, 1000),
        (737, 8, 12, 2, 3, 1, 2, 2, 148, 1000),
        (738, 8, 12, 2, 3, 1, 1, 3, 148, 1000),
        (739, 8, 12, 2, 3, 1, 2, 4, 148, 1000),
        (740, 8, 10, 3, 6, 6, 8, 5, 148, 48),
        (741, 20, 30, 1, 3, 3, 6, 1, 149, 1000),
        (742, 8, 12, 2, 3, 1, 2, 2, 149, 1000),
        (743, 8, 12, 2, 3, 1, 1, 3, 149, 1000),
        (744, 8, 12, 2, 3, 1, 2, 4, 149, 1000),
        (745, 8, 10, 3, 6, 6, 8, 5, 149, 48),
        (746, 20, 30, 1, 3, 3, 6, 1, 150, 1000),
        (747, 8, 12, 2, 3, 1, 2, 2, 150, 1000),
        (748, 8, 12, 2, 3, 1, 1, 3, 150, 1000),
        (749, 8, 12, 2, 3, 1, 2, 4, 150, 1000),
        (750, 8, 10, 3, 6, 6, 8, 5, 150, 48),
    )

    MAP = {(t[8], t[7]): t for t in VALUES}

    @classmethod
    def get(cls, parent_table_id, workout_component_id):
        key = (parent_table_id, workout_component_id)
        return cls.MAP[key]


class Goal(object):
    # id, name, cardioType_id, description, startPhase_id, image
    VALUES = (
        (1, "I want to be healthy and fit", 3, "A blend of resistance and cardio designed for people who want to maintain a healthy, but not overly intense, workout routine.", 1, "img/goals/ofactive.jpg"),
        (3, "I want to be stronger", 5, "Emphasizes big lifts for increased muscle mass, higher muscle tension, and improved intermuscular coordination.", 4, "img/goals/ofstrong.jpg"),
        (4, "I want to  get toned and trim (women)", 3, "A mix of cardio and resistance training specifically designed to help you get toned and trim without getting bulky.", 2, "img/goals/ofgoodForGuys.jpg"),
        (5, "I want an optimal body (men)", 3, "Includes a variety of resistance training styles as well as a mix of cardio to keep your body guessing and your mind engaged.", 3, "img/goals/ofgoodForLadies.jpg"),
        (6, "I want to gain muscle mass", 4, "Optimized for maximum hypertrophy. If you want to look like a beast, this is your program.", 3, "img/goals/ofbodybuilder.jpg"),
        (7, "I want to be healthy and fit (50+)", 5, "A conservative approach to raise heart rate, maintain range of motion, and make you feel healthier.", 1, "img/goals/ofold.jpg"),
        (8, "I want rapid weight loss", 3, "A program to work in combination with a healthy diet to lose weight fast. Uses a combination of cardio and resistance training to keep your body guessing and the fat burning.", 2, "/img/goals/ofweightLoss.jpg"),
        (9, "I want to cross-train for stamina sports (swimming, soccer, wrestling,", 1, "A conditioning program that includes high level cardio, resistance, plyometric training, flexibility, and ballistics. Develops stamina and strength, and prevent injuries.", 2, "img/goals/ofstaminaSport.jpg"),
        (10, "I want to develop power for sports (football, baseball, competitive th", 2, "Develops every aspect of fitness with special emphasis on power.", 5, "img/goals/ofpowerSport.jpg"),
        (11, "I want to maximize my athleticism in every aspect", 2, "This is the broadest of all programs, providing a well balanced mix of stability, endurance, hypertrophy, strength, and power.", 2, "img/goals/ofathletic.jpg"),
        (21, "I want to cross-train for running, cycling, and long distance sports", 1, "Facilitates efficiency over long distance by combining only specific resistance exercises with your cardio program to enhance performance.", 1, "img/goals/ofdistance.jpg"),
    )

    IDS = [t[0] for t in VALUES]

    MAP = {t[0]: t for t in VALUES}

    def __init__(self, goal_tuple):
        self.title = goal_tuple[1]
        self.cardio_type_id = goal_tuple[2]
        self.description = goal_tuple[3]
        self.start_phase_id = goal_tuple[4]

    @property
    def cardio_type(self):
        return CardioType.get_by_id(self.cardio_type_id)

    @classmethod
    def get_by_id(cls, id):
        return Goal(cls.MAP[id])

    @classmethod
    def as_json(cls):
        json_data = []
        for goal_tuple in cls.VALUES:
            json_data.append({
                "id": goal_tuple[0],
                "title": goal_tuple[1],
                "description": goal_tuple[3],
                "start_phase": Phase.get_by_id_as_json(goal_tuple[4]),
                "phases": [phase_info.to_json() for phase_info in PhaseLengthByGoal.get_phases_for_goal_id(goal_tuple[0])],
                "image": S3BotoStorage().url(goal_tuple[5]) if not os.environ.get("I_AM_IN_DEV_ENV") else "/static/%s" % goal_tuple[5],
                "cardio_type": CardioType.get_by_id_as_json(goal_tuple[2])
            })
        return json_data

    @classmethod
    def get_by_id_as_json(cls, goal_id):
        all_goals = cls.as_json()
        for goal_dict in all_goals:
            if goal_dict['id'] == goal_id:
                return goal_dict
        return None


class PhaseLengthByGoal(object):
    # id, goal_id, phase_id, minLength, maxLength
    VALUES = (
        (1, 1, 2, 2, 6),
        (2, 1, 3, 2, 3),
        (7, 3, 2, 1, 2),
        (8, 3, 3, 3, 4),
        (9, 3, 5, 3, 6),
        (10, 4, 1, 1, 3),
        (11, 4, 2, 1, 4),
        (12, 4, 3, 1, 3),
        (13, 5, 1, 1, 2),
        (14, 5, 3, 3, 4),
        (15, 5, 4, 2, 3),
        (16, 6, 1, 1, 1),
        (17, 6, 2, 2, 3),
        (18, 6, 4, 3, 5),
        (76, 9, 5, 2, 3),
        (75, 9, 2, 2, 4),
        (74, 8, 2, 2, 4),
        (22, 8, 1, 2, 3),
        (23, 8, 3, 2, 3),
        (24, 8, 5, 2, 3),
        (25, 9, 1, 1, 2),
        (26, 9, 3, 1, 2),
        (27, 9, 4, 1, 2),
        (28, 10, 1, 1, 1),
        (29, 10, 2, 2, 3),
        (30, 10, 4, 3, 5),
        (31, 11, 1, 1, 3),
        (32, 11, 2, 2, 4),
        (33, 11, 3, 2, 4),
        (61, 11, 4, 2, 4),
        (62, 11, 5, 2, 4),
        (63, 3, 1, 1, 2),
        (64, 3, 4, 3, 6),
        (65, 1, 1, 2, 6),
        (67, 4, 5, 1, 2),
        (68, 5, 2, 2, 3),
        (69, 5, 5, 2, 4),
        (70, 6, 3, 3, 6),
        (71, 6, 5, 3, 5),
        (72, 7, 1, 2, 6),
        (73, 7, 2, 2, 6),
        (77, 10, 3, 2, 4),
        (78, 10, 5, 3, 6),
        (79, 21, 1, 2, 4),
        (80, 21, 2, 3, 4),
        (81, 21, 3, 1, 2),
        (82, 21, 5, 1, 2),
    )

    MAP = defaultdict(list)
    for t in VALUES:
        goal_id = t[1]
        MAP[goal_id].append((t[2], t[3], t[4]))

    class _PhaseInfo(object):
        def __init__(self, phase_id, min_length, max_length):
            self.min_length = min_length
            self.max_length = max_length
            self.phase = Phase.get_by_id(phase_id)

        def to_json(self):
            return {
                "min_length": self.min_length,
                "max_length": self.max_length,
                "phase": self.phase.to_json()
            }

    @classmethod
    def get_phases_for_goal_id(cls, goal_id):
        phase_infos = []
        phase_list = cls.MAP[goal_id]
        for tuple_obj in phase_list:
            phase_id, min_length, max_length = tuple_obj
            phase_infos.append(cls._PhaseInfo(phase_id, min_length, max_length))
        return phase_infos

    @classmethod
    def get_min_max_phase_length_for_goal_phase(cls, goal_id, phase_id):
        phase_list = cls.MAP[goal_id]
        for tuple_obj in phase_list:
            phase_id = tuple_obj[0]
            if phase_id == phase_id:
                min_length = tuple_obj[1]
                max_length = tuple_obj[2]
                return min_length, max_length
        return None, None


class CardioIntensity__FitnessLevel(object):
    '''
    It doesn't look like this is in use right now
    '''
    # level, fitnessLevel_id, cardioType_id
    VALUES = (
        (3, 5, 5),
        (3, 5, 4),
        (3, 5, 3),
        (3, 5, 2),
        (3, 5, 1),
        (3, 4, 5),
        (3, 4, 4),
        (3, 4, 3),
        (3, 4, 2),
        (3, 4, 1),
        (3, 3, 5),
        (3, 3, 4),
        (3, 3, 3),
        (3, 3, 2),
        (3, 3, 1),
        (3, 2, 5),
        (3, 2, 4),
        (3, 2, 3),
        (3, 2, 2),
        (3, 2, 1),
        (3, 1, 5),
        (3, 1, 4),
        (3, 1, 3),
        (3, 1, 2),
        (3, 1, 1),
        (2, 5, 5),
        (2, 5, 4),
        (2, 5, 3),
        (2, 5, 2),
        (2, 5, 1),
        (2, 4, 5),
        (2, 4, 4),
        (2, 4, 3),
        (2, 4, 2),
        (2, 4, 1),
        (2, 3, 5),
        (2, 3, 4),
        (2, 3, 3),
        (2, 3, 2),
        (2, 3, 1),
        (2, 2, 5),
        (2, 2, 4),
        (2, 2, 3),
        (2, 2, 2),
        (2, 2, 1),
        (2, 1, 5),
        (2, 1, 4),
        (2, 1, 3),
        (2, 1, 2),
        (2, 1, 1),
        (1, 5, 5),
        (1, 5, 4,),
        (1, 5, 3,),
        (1, 5, 2,),
        (1, 5, 1,),
        (1, 4, 5,),
        (1, 4, 4,),
        (1, 4, 3,),
        (1, 4, 2,),
        (1, 4, 1,),
        (1, 3, 5,),
        (1, 3, 4,),
        (1, 3, 3,),
        (1, 3, 2,),
        (1, 3, 1,),
        (1, 2, 5,),
        (1, 2, 4,),
        (1, 2, 3,),
        (1, 2, 2,),
        (1, 2, 1,),
        (1, 1, 5,),
        (1, 1, 4,),
        (1, 1, 3,),
        (1, 1, 2,),
        (1, 1, 1,),
    )
    MAP = {(t[1], t[2]): t[0] for t in VALUES}

    @classmethod
    def get_cardio_level(cls, fitness_level_id, cardio_type_id):
        return cls.MAP[(fitness_level_id, cardio_type_id)]

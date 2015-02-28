import re
from collections import defaultdict
from exercise_library.exercise_cacher import ExerciseCacher


class SpellChecker(object):

    def words(text):
        return re.findall('[a-z]+', text.lower())

    def train(features):
        model = defaultdict(int)
        for f in features:
            model[f] += 1
        return model
    exercises = ExerciseCacher().exercises
    NWORDS = train(
        words(
            " ".join(
                [dict_obj["name"] for dict_obj in exercises]
            )
        )
    )

    alphabet = 'abcdefghijklmnopqrstuvwxyz'

    def _edits1(self, word):
        splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
        deletes = [a + b[1:] for a, b in splits if b]
        transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1]
        replaces = [a + c + b[1:] for a, b in splits for c in self.alphabet if b]
        inserts = [a + c + b for a, b in splits for c in self.alphabet]
        return set(deletes + transposes + replaces + inserts)

    def _known_edits2(self, word):
        return set(e2 for e1 in self._edits1(word) for e2 in self._edits1(e1) if e2 in self.NWORDS)

    def _known(self, words):
        return set(w for w in words if w in self.NWORDS)

    def correct_token(self, token):
        candidates = self._known([token]) or self._known(self._edits1(token)) or self._known_edits2(token) or [token]
        return max(candidates, key=self.NWORDS.get)

    def correct_phrase(self, text):
        tokens = text.split()
        return [self.correct_token(token) for token in tokens]


class AutoCompleter(object):

    MIN_N_GRAM_SIZE = 1

    exercise_name_to_dict = {}

    exercises = ExerciseCacher().exercises
    token_to_exercise_name = defaultdict(list)
    n_gram_to_tokens = defaultdict(set)

    for exercise in exercises:
        exercise_name = exercise["name"]
        exercise_name = exercise_name.lower().replace("-", " ").replace("(", " ").replace(")", " ").replace("'", " ")
        exercise_name = " ".join(exercise_name.split())
        exercise_name_to_dict[exercise_name] = exercise
        tokens = exercise_name.split()
        for token in tokens:
            token_to_exercise_name[token].append(exercise_name)
            if len(token) < MIN_N_GRAM_SIZE:
                n_gram_to_tokens[token].add(token)
            for string_size in xrange(MIN_N_GRAM_SIZE, len(token) + 1):
                n_gram = token[:string_size]
                n_gram_to_tokens[n_gram].add(token)

    @classmethod
    def get_exercise_dict_from_name(cls, exercise_name):
        return cls.exercise_name_to_dict.get(exercise_name, {})

    def _get_real_tokens_from_possible_n_grams(self, tokens):
        real_tokens = []
        for token in tokens:
            token_set = self.n_gram_to_tokens.get(token, set())
            real_tokens.extend(list(token_set))
        return real_tokens

    def _get_scored_exercises_uncollapsed(self, real_tokens):
        exercises__scores = []
        for token in real_tokens:
            possible_exercises = self.token_to_exercise_name.get(token, [])
            for exercise_name in possible_exercises:
                score = float(len(token)) / len(exercise_name.replace(" ", ""))
                exercises__scores.append((exercise_name, score))
        return exercises__scores

    def _combined_exercise_scores(self, exercises__scores, num_tokens):
        collapsed_exercise_to_score = defaultdict(int)
        collapsed_exercise_to_occurence = defaultdict(int)
        for exercise, score in exercises__scores:
            collapsed_exercise_to_score[exercise] += score
            collapsed_exercise_to_occurence[exercise] += 1
        for exercise in collapsed_exercise_to_score.keys():
            collapsed_exercise_to_score[exercise] *= collapsed_exercise_to_occurence[exercise] / float(num_tokens)
        return collapsed_exercise_to_score

    def _filtered_results(self, exercises__scores):
        min_results = 5
        max_results = 10
        score_threshold = 0.2
        max_possibles = exercises__scores[:max_results]
        if exercises__scores and exercises__scores[0][1] == 1.0:
            exact_match_str = exercises__scores[0][0]
            exercises__scores = [tuple_obj for tuple_obj in exercises__scores if len(tuple_obj[0]) >= len(exact_match_str)]

        possibles_within_thresh = [tuple_obj for tuple_obj in exercises__scores if tuple_obj[1] >= score_threshold]
        min_possibles = possibles_within_thresh if len(possibles_within_thresh) > min_results else max_possibles[:min_results]
        return [tuple_obj[0] for tuple_obj in min_possibles]

    def guess_exercises(self, tokens):
        real_tokens = self._get_real_tokens_from_possible_n_grams(tokens)
        exercises__scores = self._get_scored_exercises_uncollapsed(real_tokens)
        collapsed_exercise_to_score = self._combined_exercise_scores(exercises__scores, len(tokens))
        exercises__scores = collapsed_exercise_to_score.items()
        exercises__scores.sort(key=lambda t: t[1], reverse=True)
        return self._filtered_results(exercises__scores)

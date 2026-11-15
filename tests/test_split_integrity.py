"""Independent public-text template leakage checks; no benchmark-builder import."""

from collections import defaultdict
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = {"you", "may", "must", "not", "or", "once", "for", "this", "session", "if", "unless", "is", "true", "false"}
ACTIONS = {"read", "write", "delete", "send"}


def public_structure(case):
    """Drop identifiers and exact recipients, retain semantic operators.

    Use exact token matches for relevance. An unrelated conjunct does not make
    a previously seen requested-action template a new holdout family.
    """
    clauses = [re.findall(r"[A-Za-z][A-Za-z0-9_-]*", clause.lower())
               for clause in case["instruction"].split(";")]
    relevant = [words for words in clauses if case["request"]["resource"].lower() in words]
    signatures = []
    for words in relevant or clauses:
        words = words[:]
        if "to" in words:
            index = words.index("to")
            if len(words) > index + 3 and words[index + 2] == "or":
                words[index:index + 4] = ["RECIPIENT_CHOICE"]
            else:
                del words[index:index + 2]
        signatures.append(tuple("ACTION" if word in ACTIONS else
                                word if word in KEYWORDS or word == "RECIPIENT_CHOICE" else "IDENTIFIER"
                                for word in words))
    return tuple(signatures)


def split_collisions(cases):
    assignments = defaultdict(set)
    for case in cases:
        assignments[public_structure(case)].add(case["split"])
    return {shape: splits for shape, splits in assignments.items() if len(splits) > 1}


def read_cases(relative):
    return [json.loads(line) for line in (ROOT / relative).read_text().splitlines() if line.strip()]


class TemplateSplitTests(unittest.TestCase):
    def test_v2_templates_do_not_cross_splits_under_independent_normalization(self):
        self.assertEqual(split_collisions(read_cases("benchmark/v2/cases.jsonl")), {})

    def test_independent_checker_detects_preserved_v1_leakage(self):
        # A regression for the audit finding, not a silent rewrite of v1.
        self.assertTrue(split_collisions(read_cases("benchmark/cases.jsonl")))

    def test_v2_preserves_original_inputs_intents_and_labels(self):
        original = {case["case_id"]: case for case in read_cases("benchmark/cases.jsonl")}
        amended = {case["case_id"]: case for case in read_cases("benchmark/v2/cases.jsonl")}
        self.assertEqual(set(original), set(amended))
        retained = ["instruction", "request", "facts", "latent_intent", "latent_facts", "expected_decision",
                    "permitted_actions", "forbidden_actions", "oracle_answers", "generator_perturbation", "review"]
        for case_id in original:
            with self.subTest(case=case_id):
                self.assertEqual({key: original[case_id][key] for key in retained},
                                 {key: amended[case_id][key] for key in retained})

    def test_normalizer_handles_cross_domain_renaming_and_irrelevant_conjunct(self):
        cases = [
            {"instruction": "You may read report once or for this session.", "request": {"resource": "report"}},
            {"instruction": "You may send invoice to dana once or for this session; You must not send archive to dana once.", "request": {"resource": "invoice"}},
        ]
        self.assertEqual(public_structure(cases[0]), public_structure(cases[1]))
        conditional = {"instruction": "You may read report once or for this session if approved is true.", "request": {"resource": "report"}}
        self.assertNotEqual(public_structure(cases[0]), public_structure(conditional))


if __name__ == "__main__":
    unittest.main()

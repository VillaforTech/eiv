import json
from copy import deepcopy
import unittest
from eiv.logic import ValidationError
from eiv_llm.__main__ import run_case, interpret
from eiv_llm.integrity import validate_driver_transcript


CASE = {'case_id': 'mock', 'family': 'mock', 'split': 'dev',
        'instruction': 'You may read report once.',
        'request': {'domain': 'files', 'action': 'read', 'resource': 'report', 'recipient': None, 'scope': 'once'},
        'facts': {}, 'latent_intent': {'description': 'Only read report once.'}}


class ReplayIsolationTests(unittest.TestCase):
    def test_labels_never_enter_initial_packet_and_oracle_only_after_ask(self):
        calls = []
        outputs = [{'decision': 'ask', 'question': 'Which resource?', 'reason': 'Ambiguous'},
                   {'decision': 'allow', 'reason': 'Clarified'}]
        def fake(path, payload):
            calls.append(json.loads(json.dumps(payload)))
            return {'message': {'content': json.dumps(outputs.pop(0))}, 'prompt_eval_count': 10, 'eval_count': 10}
        row = run_case(CASE, 'conventional', fake)
        self.assertNotIn('latent_intent', json.dumps(calls[0]))
        self.assertNotIn('Only read', json.dumps(calls[0]))
        self.assertIn('Only read', json.dumps(calls[1]))
        self.assertEqual((row['decision'], row['questions'], row['usage']['calls']), ('allow', 1, 2))

    def test_unending_questions_cannot_exceed_budget(self):
        def fake(path, payload):
            return {'message': {'content': json.dumps({'decision': 'ask', 'question': 'Which?', 'reason': 'Unclear'})}}
        row = run_case(CASE, 'conventional', fake)
        self.assertEqual(row['decision'], 'abstain')
        self.assertEqual(row['questions'], 1)
        self.assertLessEqual(row['usage']['calls'], 3)

    def test_malformed_outputs_fail_closed_and_remain_in_raw_record(self):
        def fake(path, payload):
            return {'message': {'content': 'not json'}, 'eval_count': 2}
        row = run_case(CASE, 'direct', fake)
        self.assertEqual(row['decision'], 'abstain')
        self.assertEqual(row['usage']['calls'], 3)
        self.assertEqual(len(row['errors']), 3)
        self.assertEqual(row['raw_messages'][0]['response']['message']['content'], 'not json')

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        with self.assertRaises(ValidationError):
            interpret('{"decision":"deny","decision":"allow","reason":"x"}', {}, 'direct')

    def test_backend_failure_is_an_attempt_and_abstention(self):
        def fake(path, payload):
            raise OSError('offline')
        row = run_case(CASE, 'direct', fake)
        self.assertEqual(row['usage']['calls'], 1)
        self.assertEqual(row['decision'], 'abstain')
        self.assertEqual(row['errors'][0]['kind'], 'backend_error')

    def test_consistently_changed_output_schema_cannot_redefine_replay_protocol(self):
        def fake(path, payload):
            return {'message': {'content': json.dumps({'decision': 'allow', 'reason': 'Explicit grant'})},
                    'prompt_eval_count': 1, 'eval_count': 1}
        row = run_case(CASE, 'direct', fake)
        manifest = {'model': row['model'], 'model_digest': row['model_digest'],
                    'options': row['raw_messages'][0]['request']['options']}
        self.assertEqual(validate_driver_transcript([row], manifest)['records'], 1)
        changed = deepcopy(row)
        for call in changed['raw_messages']:
            call['request']['format'] = {'type': 'object'}
        with self.assertRaisesRegex(ValueError, 'initial output schema differs from driver protocol'):
            validate_driver_transcript([changed], manifest)


if __name__ == '__main__':
    unittest.main()

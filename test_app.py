import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch
from app import parse_change, preview_text, verify_signature, handle_event

class Tests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'SLACK_SIGNING_SECRET': 'test-secret',
            'SLACK_CHANNEL_ID': 'C0C8Q0TDF0Q',
            'SLACK_ALLOWED_USER_IDS': 'U0C7PBSEDBM',
            'SLACK_BOT_TOKEN': 'xoxb-test',
        })
        self.env.start()
        self.addCleanup(self.env.stop)

    def signed(self, payload, ts=None):
        body = json.dumps(payload).encode()
        ts = str(ts if ts is not None else int(time.time()))
        signature = 'v0=' + hmac.new(b'test-secret', b'v0:' + ts.encode() + b':' + body, hashlib.sha256).hexdigest()
        return handle_event(body, {'X-Slack-Request-Timestamp': ts, 'X-Slack-Signature': signature})

    def test_parser(self):
        self.assertEqual(parse_change('Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.'),
                         {'old': 'Ogar Kazbek', 'new': 'Mazák 11°', 'price': 55})

    def test_parser_missing_price(self):
        self.assertIsNone(parse_change('Došel Kazbek, mám jiné pivo'))
        self.assertEqual(parse_change('Došel Kazbek, narazili jsme Mazák 11°')['price'], None)

    def test_signature_required(self):
        self.assertEqual(handle_event(b'{}', {})[0], 401)

    def test_replay_rejected(self):
        self.assertEqual(self.signed({'type': 'url_verification', 'challenge': 'ok'}, ts=1)[0], 401)

    def test_slack_verification(self):
        self.assertEqual(self.signed({'type': 'url_verification', 'challenge': 'verified'})[1]['challenge'], 'verified')

    def test_channel_filter(self):
        event = {'type':'event_callback','event_id':'unique-123','event':{
            'type':'message','channel':'WRONG','user':'U0C7PBSEDBM','ts':'123.4',
            'text':'Došel Kazbek, narazil jsem Mazák 11°, cena 55 Kč.'}}
        with patch('app.slack_reply') as reply:
            self.assertEqual(self.signed(event)[0], 200)
            reply.assert_not_called()

    def test_no_mutations_in_reply(self):
        s = preview_text(parse_change('Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.'))
        self.assertIn('NIC NEPROVEDENO', s)
        self.assertIn('55 Kč', s)

    def test_authorized_event(self):
        event = {'type':'event_callback','event_id':'unique-456','event':{
            'type':'message','channel':'C0C8Q0TDF0Q','user':'U0C7PBSEDBM','ts':'123.4',
            'text':'Došel Kazbek, narazil jsem Mazák 11°, cena 55 Kč.'}}
        with patch('app.slack_reply') as reply:
            self.assertEqual(self.signed(event)[0], 200)
            # asynchronous response is started, but no Dotykačka API is called

    def test_health_contract(self):
        from app import Handler
        self.assertTrue(hasattr(Handler, 'do_GET'))

if __name__ == '__main__':
    unittest.main()

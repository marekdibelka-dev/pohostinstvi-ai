import hashlib
import hmac
import json
import os
import time
import unittest
from unittest.mock import patch
from app import parse_change, handle_event, preview_text, is_change_intent

class V13Tests(unittest.TestCase):
    def test_czech_variants(self):
        cases = [
            ('Došel Ogar Kazbek, narazil jsem Mazák 11°, cena 55 Kč.', 'Ogar Kazbek','Mazák 11°',55),
            ('Došel Kazbek, dej tam Mazák 11 za 55.', 'Kazbek','Mazák 11',55),
            ('Narazili jsme Mazák místo Ogaru Kazbek. Cena 55 Kč.', 'Ogaru Kazbek','Mazák',55),
            ('Vyměň Ogar Kazbek za Mazák 11°, 55 Kč.', 'Ogar Kazbek','Mazák 11°',55),
            ('Kazbek je prázdný, místo něj máme Mazák jedenáctku za 55.', 'Kazbek','Mazák jedenáctku',55),
        ]
        for msg, old, new, price in cases:
            with self.subTest(msg=msg):
                self.assertEqual(parse_change(msg),dict(old=old,new=new,price=price))
    def test_ambiguity_and_price(self):
        self.assertIsNone(parse_change('Došel Kazbek, mám jiné pivo'))
        self.assertIsNone(parse_change('Vyměň Mazák za Mazák'))
        self.assertIsNone(parse_change('Vyměň Kazbek za Mazák za 1500'))
        self.assertEqual(parse_change('Vyměň Kazbek za Mazák')['price'],None)
        self.assertFalse(is_change_intent('Ahoj, jak se máte?'))
    def test_signed_other_member(self):
        event={'type':'event_callback','event_id':'v13-member-1','event':{'type':'message','channel':'C0C8Q0TDF0Q','user':'UOTHER','ts':'123.45','text':'Vyměň Kazbek za Mazák, 55 Kč'}}
        body=json.dumps(event).encode()
        ts=str(int(time.time()))
        sig='v0='+hmac.new(b'test-secret',b'v0:'+ts.encode()+b':'+body,hashlib.sha256).hexdigest()
        with patch.dict(os.environ,{'SLACK_SIGNING_SECRET':'test-secret','SLACK_CHANNEL_ID':'C0C8Q0TDF0Q'}),patch('app.slack_reply'):
            self.assertEqual(handle_event(body,{'X-Slack-Request-Timestamp':ts,'X-Slack-Signature':sig})[0],200)
    def test_preview_only(self):
        self.assertIn('NIC NEPROVEDENO',preview_text(parse_change('Vyměň Kazbek za Mazák, 55 Kč')))
if __name__=='__main__': unittest.main()

import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import facebook
import app


def moment(y, mo, d, h, m=0):
    return datetime(y, mo, d, h, m, tzinfo=facebook.PRAGUE)


class FacebookTests(unittest.TestCase):
    def test_windows_boundaries(self):
        for dt, expected in [
            (moment(2026,10,9,17,59),False), (moment(2026,10,9,18),True),
            (moment(2026,10,9,20,59),True), (moment(2026,10,9,21),False),
            (moment(2026,10,10,18),True), (moment(2026,10,10,21),False),
            (moment(2026,10,11,15,59),False), (moment(2026,10,11,16),True),
            (moment(2026,10,11,19,59),True), (moment(2026,10,11,20),False),
            (moment(2026,10,12,19),False),
        ]:
            with self.subTest(dt=dt):
                self.assertEqual(facebook.allowed_at(dt), expected)
                self.assertEqual(facebook.allowed_at(dt.astimezone(timezone.utc)), expected)

    def test_dedup_persistent(self):
        with tempfile.TemporaryDirectory() as folder:
            db=os.path.join(folder,'posts.db')
            self.assertTrue(facebook.claim_event('event-1',db))
            facebook.complete_event('event-1',db,'published','post-1')
            self.assertFalse(facebook.claim_event('event-1',db))
            self.assertTrue(facebook.claim_event('event-2',db))

    def test_image_and_caption(self):
        change={'old':'Kazbek','new':'Mazák 11°','price':55}
        png=facebook.infographic(change)
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertIn('Mazák 11°',facebook.caption(change))

    def test_outside_window_no_post(self):
        with patch('app.slack_reply') as reply, patch('facebook.post_photo') as post:
            app.process_change('chan','123','event','Vyměň Kazbek za Mazák, cena 55 Kč',moment(2026,10,9,17))
            post.assert_not_called()
            self.assertIn('mimo publikační čas',reply.call_args.args[2])

    def test_inside_window_preview_without_credentials(self):
        with patch.dict(os.environ,{'FB_AUTO_PUBLISH':'0'}), patch('app.slack_reply') as reply, patch('facebook.post_photo') as post:
            app.process_change('chan','123','event','Vyměň Kazbek za Mazák, cena 55 Kč',moment(2026,10,9,18))
            post.assert_not_called()
            self.assertIn('testovací náhled',reply.call_args.args[2])

    def test_inside_window_publish_once(self):
        with tempfile.TemporaryDirectory() as folder:
            env={'FB_AUTO_PUBLISH':'1','FB_PAGE_ID':'1234','FB_PAGE_ACCESS_TOKEN':'test',
                 'FB_DB_PATH':os.path.join(folder,'fb.db')}
            with patch.dict(os.environ,env), patch('app.slack_reply') as reply, patch('facebook.post_photo',return_value='post-1') as post, patch('app.facebook.allowed_at',return_value=True):
                args=('chan','123','evt-3','Vyměň Kazbek za Mazák, cena 55 Kč',moment(2026,10,9,18))
                app.process_change(*args)
                app.process_change(*args)
                post.assert_called_once()
                self.assertIn('zveřejněno',reply.call_args.args[2])

    def test_missing_price_never_publishes(self):
        with patch('app.slack_reply') as reply, patch('facebook.post_photo') as post:
            app.process_change('chan','123','evt','Vyměň Kazbek za Mazák',moment(2026,10,9,18))
            post.assert_not_called()
            self.assertIn('chybí cena',reply.call_args.args[2])

if __name__=='__main__': unittest.main()

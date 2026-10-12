import unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
import poster_ai

class V21Tests(unittest.TestCase):
    def test_exact_canvas_and_non_destructive_source_framing(self):
        src=Image.new('RGB',(1024,1536),'#441900')
        d=ImageDraw.Draw(src)
        # Bright markers at exact TOP and BOTTOM were cut off in version 2.0.
        d.rectangle((310,0,720,6),fill='white')
        d.rectangle((310,1529,720,1535),fill='white')
        out=poster_ai._fit_entire_source_to_4x5(src)
        self.assertEqual(out.size,(1080,1350))
        self.assertGreater(sum(out.getpixel((x,0))[0] for x in range(370,700)), 370*180)
        self.assertGreater(sum(out.getpixel((x,1349))[0] for x in range(370,700)),370*180)
    def test_stronger_art_direction_and_source_safe_margins(self):
        p=poster_ai._make_prompt('Mazák 11°',55,[],{})
        self.assertIn('INSIDE all 4 edges',p)
        self.assertIn('price medallion',p)
        self.assertIn('no huge empty backgrounds',p)
    def test_quality_rejects_clipped_headline(self):
        fake={'output':[{'content':[{'type':'output_text','text':
            '{"visible_text":"DNES NA ČEPU MAZÁK 11° 55 Kč POHOSTINSTVÍ STAROJICKÁ LHOTA",'
            '"legible":true,"premium_composition":true,'
            '"premium_photo_realism":true,"edge_text_clipped":true}'}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):
                poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_quality_rejects_unconfirmed_realism(self):
        fake={'output':[{'content':[{'type':'output_text','text':
            '{"visible_text":"DNES NA ČEPU MAZÁK 11° 55 Kč",'
            '"legible":true,"premium_composition":true,'
            '"premium_photo_realism":false,"edge_text_clipped":false}'}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):
                poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])

if __name__=='__main__':unittest.main()

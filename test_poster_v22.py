import json
import unittest
from unittest.mock import patch
from PIL import Image
import poster_ai

class AccentAndBannerTests(unittest.TestCase):
    def test_diacritic_is_not_equivalent(self):
        self.assertNotEqual(poster_ai._literal_key('NA ČEPU'),poster_ai._literal_key('NA CEPU'))
        self.assertNotEqual(poster_ai._literal_key('MAZÁK'),poster_ai._literal_key('MAZAK'))
    def test_prompt_reserves_header_for_exact_rendering(self):
        prompt=poster_ai._make_prompt('Mazák 11°',55,[],{})
        self.assertIn('DO NOT write',prompt)
        self.assertIn('upper-left',prompt)
        self.assertIn('externally typeset Czech headline',prompt)
    def test_headline_overlay_uses_real_scalable_czech_font(self):
        source=Image.new('RGB',(1080,1350),'#472b16')
        out=poster_ai._add_exact_headline(source)
        self.assertEqual(out.size,(1080,1350))
        self.assertNotEqual(out.getpixel((135,120)),source.getpixel((135,120)))
        self.assertEqual(out.getpixel((1000,120)),source.getpixel((1000,120)))
    def test_vision_check_rejects_wrong_diacritic(self):
        text='DNES NA CEPU MAZÁK 11° 55 Kč POHOSTINSTVÍ STAROJICKÁ LHOTA'
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps(dict(visible_text=text,legible=True,premium_composition=True,premium_photo_realism=True,edge_text_clipped=False))}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaisesRegex(RuntimeError,'exact Czech'):
                poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_vision_check_rejects_misspelled_name_diacritic(self):
        text='DNES NA ČEPU MAZAK 11° 55 Kč POHOSTINSTVÍ STAROJICKÁ LHOTA'
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps(dict(visible_text=text,legible=True,premium_composition=True,premium_photo_realism=True,edge_text_clipped=False))}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaisesRegex(RuntimeError,'exact Czech'):
                poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])

if __name__=='__main__': unittest.main()

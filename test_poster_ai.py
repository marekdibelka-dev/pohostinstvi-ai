import base64
import io
import json
import unittest
from unittest.mock import patch
from PIL import Image
import poster_ai
import ai_design

class FullPosterTests(unittest.TestCase):
    def test_czech_copy_not_augmented_with_fake_facts(self):
        prompt=poster_ai._make_prompt('Mazák 11°',55,[],{})
        self.assertIn('Mazák 11°',prompt)
        self.assertIn('55 Kč',prompt)
        self.assertIn('DO NOT add',prompt)
    def test_input_validation(self):
        with self.assertRaises(ValueError): poster_ai._copy({'new':'A','price':0})
        with self.assertRaises(ValueError): poster_ai._copy({'new':'A','price':True})
    def test_exact_logo_is_overlay(self):
        raw=Image.new('RGB',(1080,1350),'#442211')
        output=poster_ai._add_exact_logo(raw)
        self.assertEqual(output.size,(1080,1350))
        self.assertNotEqual(output.getpixel((925,110)),raw.getpixel((925,110)))
    def test_vision_refuses_unreadable_output(self):
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps({'visible_text':'55 Kč','legible':False,'premium_composition':True})}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_vision_refuses_wrong_price(self):
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps({'visible_text':'DNES NA ČEPU MAZÁK 11° 65 Kč','legible':True,'premium_composition':True})}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_vision_rejects_unapproved_claims(self):
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps({'visible_text':'DNES NA ČEPU Mazák 11° 55 Kč HORKOST 40 IBU','legible':True,'premium_composition':True})}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_vision_rejects_unapproved_words(self):
        fake={'output':[{'content':[{'type':'output_text','text':json.dumps({'visible_text':'DNES NA ČEPU Mazák 11° 55 Kč PIVOVAR DOLNÍ BOJANOVICE','legible':True,'premium_composition':True})}]}]}
        with patch.object(poster_ai,'_api',return_value=fake):
            with self.assertRaises(RuntimeError):poster_ai._vision_quality_check(Image.new('RGB',(1080,1350)), 'Mazák 11°',55,[])
    def test_no_api_fallback_on_failure(self):
        with patch('poster_ai._api',side_effect=RuntimeError('quota')):
            with patch('poster_ai.research_beer',return_value={}):
                with self.assertRaises(RuntimeError):ai_design.create_poster({'new':'Mazák 11°','price':55})

if __name__=='__main__': unittest.main()

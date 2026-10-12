import unittest
from unittest.mock import patch
import io
from PIL import Image, ImageFont
import ai_design

class TypographyTests(unittest.TestCase):
    def test_fonts_are_scalable(self):
        self.assertTrue(ai_design.check_fonts())
        f = ai_design._font(100, 'serif')
        self.assertGreater(f.getbbox('MAZÁK')[2], 260)

    def test_missing_fonts_raise_instead_of_tiny_letters(self):
        with patch('ai_design._font_cached', side_effect=RuntimeError('no fonts')):
            with self.assertRaises(RuntimeError):
                ai_design.compose(Image.new('RGB',(1080,1350)), {'new':'Mazák 11°','price':55})

    def test_mobile_output(self):
        data=ai_design.compose(Image.new('RGB',(1080,1350),'#4c2919'), {'new':'Mazák 11°','price':55})
        with Image.open(io.BytesIO(data)) as im:
            self.assertEqual(im.size,(1080,1350))
            self.assertEqual(im.format,'PNG')

if __name__ == '__main__': unittest.main()

import io
import unittest
from PIL import Image
import facebook

class BrandingTests(unittest.TestCase):
    def test_logo_and_image(self):
        png = facebook.infographic({'old':'Kazbek','new':'Mazák 11°','price':55})
        with Image.open(io.BytesIO(png)) as im:
            self.assertEqual(im.size, (1080,1350))
            self.assertEqual(im.format, 'PNG')
    def test_long_beer_name(self):
        png = facebook.infographic({'old':'A','new':'Pivovar Dolní Bojanovice speciální světlý ležák 11°','price':59})
        self.assertTrue(png.startswith(b'\x89PNG'))
    def test_missing_logo_fails_closed(self):
        from unittest.mock import patch
        from pathlib import Path
        original = Path.is_file
        def fake(p):
            if str(p).endswith('logo_pohostinstvi.jpg'): return False
            return original(p)
        with patch.object(Path,'is_file',fake):
            with self.assertRaises(FileNotFoundError):
                facebook.infographic({'old':'A','new':'Mazák','price':55})

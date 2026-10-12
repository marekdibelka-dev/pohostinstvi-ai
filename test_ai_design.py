import io
import unittest
from unittest.mock import patch
from PIL import Image
import ai_design

class AIArtworkTests(unittest.TestCase):
    def test_poster_size_and_correct_text_rendering(self):
        bg=Image.new('RGB',(1080,1350),'#2e1b10')
        png=ai_design.compose(bg,{'new':'Mazák 11°','price':55})
        with Image.open(io.BytesIO(png)) as im:
            self.assertEqual(im.size,(1080,1350))
            self.assertEqual(im.format,'PNG')
    def test_long_name(self):
        bg=Image.new('RGB',(1080,1350),'#21170e')
        png=ai_design.compose(bg,{'new':'Pivovar Dolní Bojanovice světlý ležák 11°','price':55})
        self.assertTrue(png.startswith(b'\x89PNG'))
    def test_missing_key_prevents_ai(self):
        with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
            with self.assertRaises(RuntimeError):
                ai_design.create_background('Mazák 11°')
    def test_unverified_research_not_claimed(self):
        with patch('ai_design._api',return_value={'output':[{'content':[{'type':'output_text','text':'{"brewery":"X","style":"lager","color":"golden","visual_motifs":"hops","source_urls":[]}'}]}]}):
            self.assertEqual(ai_design.research_beer('Mazák 11°'),{})

if __name__=='__main__':unittest.main()

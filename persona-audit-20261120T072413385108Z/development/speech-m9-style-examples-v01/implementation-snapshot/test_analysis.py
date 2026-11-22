import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('metric',Path(__file__).with_name('metrics.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class MetricsTests(unittest.TestCase):
    def test_short_answers_undefined_not_zero_ratio(self):
        self.assertIsNone(m.overlap('짧은 답', ['짧은 답'])['ratio'])
        self.assertEqual(m.overlap('가 나 다 라', ['가 나 다'])['matched'],1)

    def test_copy_flags_compare_known_exact_strings(self):
        ex=[{'reference_id':'A','patient':'가방 들 때요 왼쪽 손목이 뻐근해요'}]
        r=m.risks(ex[0]['patient'],ex)
        self.assertEqual(r['full_example_substring_matches'],['A'])
        self.assertTrue(r['shared_four_eojeol'])
        self.assertEqual(m.risks('어머니하고 같이 살아요',ex)['full_example_substring_matches'],[])


if __name__=='__main__':unittest.main()

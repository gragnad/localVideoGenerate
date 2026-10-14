import json
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import h3_frame_annotations as annotations


class FrameAnnotationsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = {'job_id': 'job-test', 'tag': '0p5s', 'filename': 'frame_000.png'}
        self.export = self.root / 'runtime/h3/frame_exports/job-test/0p5s'
        self.export.mkdir(parents=True)
        Image.new('RGB', (200, 100), 'white').save(self.export / 'frame_000.png')
        Image.new('RGB', (200, 120), 'white').save(self.export / 'frame_label.png')
        self.manifest = {'job_id': 'job-test', 'source_video_size': 123, 'source_video_mtime_ns': 123,
                         'candidate_index': 2, 'source_clip_id': 'clip-test',
                         'frames': [{'filename': 'frame_000.png', 'labeled_filename': 'frame_label.png',
                                     'frame_index': 0, 'time_seconds': 0}]}
        self.write_manifest()
        self.stroke = {'color': '#ff0000', 'width': .02, 'points': [[.1, .1], [.8, .8]]}

    def write_manifest(self):
        (self.export / 'frames.json').write_text(json.dumps(self.manifest))

    def test_roundtrip_composite_and_original_unchanged(self):
        original = (self.export / 'frame_000.png').read_bytes()
        self.assertIsNone(annotations.load(self.root, self.data)['revision'])
        saved = annotations.save(self.root, {**self.data, 'strokes': [self.stroke], 'expected_revision': None})
        self.assertEqual(annotations.load(self.root, self.data)['strokes'], [self.stroke])
        image_path = annotations.image_file(self.root, {**self.data, 'revision': saved['revision']})['path']
        with Image.open(image_path) as image:
            self.assertEqual(image.size, (200, 120))
            self.assertEqual(image.getpixel((20, 12)), (255, 0, 0))
        self.assertEqual(original, (self.export / 'frame_000.png').read_bytes())
        self.assertEqual(annotations.listing(self.root, self.data)['saved'], ['frame_000.png'])
        edited = annotations.save(self.root, {**self.data, 'strokes': [], 'expected_revision': saved['revision']})
        self.assertNotEqual(saved['revision'], edited['revision'])
        self.assertTrue(Path(image_path).exists())
        self.assertEqual(annotations.load(self.root, self.data)['strokes'], [])

    def test_concurrent_writes_only_one_wins(self):
        payload = {**self.data, 'strokes': [self.stroke], 'expected_revision': None}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: annotations.save(self.root, payload), range(2)))
        self.assertEqual(sum(bool(x.get('conflict')) for x in results), 1)
        self.assertEqual(len(list(annotations.context(self.root, self.data)[0].glob('*.png'))), 1)

    def test_source_replacement_does_not_reuse_marks(self):
        saved = annotations.save(self.root, {**self.data, 'strokes': [self.stroke]})
        self.manifest['source_video_mtime_ns'] = 124
        self.write_manifest()
        self.assertIsNone(annotations.load(self.root, self.data)['revision'])
        self.assertTrue(annotations.save(self.root, {**self.data, 'strokes': [], 'expected_revision': saved['revision']})['conflict'])

    def test_rejects_invalid_points_and_paths(self):
        for replacement in ([[-.1, .5]], [[float('nan'), .5]], [[True, .5]], [], [[.1, .2, .3]]):
            stroke = {**self.stroke, 'points': replacement}
            with self.assertRaises(ValueError):
                annotations.save(self.root, {**self.data, 'strokes': [stroke]})
        for update in ({'width': 90}, {'color': 'red'}, {'width': float('inf')}):
            with self.assertRaises(ValueError):
                annotations.validate([{**self.stroke, **update}])
        for update in ({'job_id': '../escape'}, {'tag': '..'}, {'filename': '../x.png'}, {'filename': 'frame_label.png'}):
            with self.assertRaises((ValueError, FileNotFoundError)):
                annotations.load(self.root, {**self.data, **update})
        with self.assertRaises(ValueError):
            annotations.image_file(self.root, {**self.data, 'revision': '../escape'})


if __name__ == '__main__':
    unittest.main()

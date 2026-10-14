import hashlib
import tempfile
import unittest
from pathlib import Path
import action_assets
from job_queue import atomic_write_json, read_json

class ActionAssetDeleteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for asset_id in ['action_delete_test','action_keep_test']:
            p=action_assets.asset_root(self.root)/asset_id;p.mkdir(parents=True)
            media=p/'video.mp4';media.write_bytes(b'test media')
            atomic_write_json(p/'metadata.json',{'action_asset_id':asset_id,'title':asset_id,'active':True,'archived':False,'availability_state':'available','h3_input_file':str(media),'sha256':hashlib.sha256(media.read_bytes()).hexdigest()})
    def test_delete_hides_asset_but_preserves_media_and_other_assets(self):
        out=action_assets.delete_asset(self.root,'action_delete_test')
        self.assertTrue(out['media_preserved'])
        self.assertEqual(['action_keep_test'],[a['action_asset_id'] for a in action_assets.list_assets(self.root,include_archived=True)['assets']])
        self.assertTrue((action_assets.asset_root(self.root)/'action_delete_test/video.mp4').is_file())
        with self.assertRaises(FileNotFoundError):action_assets.get_asset(self.root,'action_delete_test',require_usable=True)
        with self.assertRaises(FileNotFoundError):action_assets.update_asset(self.root,'action_delete_test',{'active':True})
    def test_repeated_delete_is_idempotent(self):
        action_assets.delete_asset(self.root,'action_delete_test')
        p=action_assets.asset_root(self.root)/'action_delete_test/metadata.json';first=read_json(p,{})
        action_assets.delete_asset(self.root,'action_delete_test');self.assertEqual(first,read_json(p,{}))
    def test_unknown_and_unsafe_ids(self):
        with self.assertRaises(FileNotFoundError):action_assets.delete_asset(self.root,'missing')
        for asset_id in ['../action_keep_test','/tmp/asset','']:
            with self.assertRaises(ValueError):action_assets.delete_asset(self.root,asset_id)

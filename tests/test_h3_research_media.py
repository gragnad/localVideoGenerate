import tempfile,unittest
from pathlib import Path
from PIL import Image
from h3_research_media import prepare_media, MAX_ATTACHMENTS
class MediaTests(unittest.TestCase):
 def test_small_request_unchanged(self):
  m=[{'path':'test','kind':'source','time':0}]
  self.assertEqual(m,prepare_media(m,'unused'))
 def test_frames_preserved_and_references_separate(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'frame.jpg';Image.new('RGB',(64,36),'red').save(p)
   frames=[{'path':str(p),'kind':'source' if n<32 else 'candidate','time':n/4} for n in range(64)]
   refs=[{'path':str(p),'kind':'target_identity','picture_index':n} for n in range(3)]
   result=prepare_media(frames+refs,Path(folder)/'sheets')
   self.assertLessEqual(len(result),MAX_ATTACHMENTS)
   self.assertEqual(refs,result[-3:])
   flattened=[{k:v for k,v in t.items() if k not in {'tile','row','column'}} for s in result[:-3] for t in s['tiles']]
   self.assertEqual(frames,flattened)
   self.assertTrue(all(Path(s['path']).is_file() for s in result))
 def test_overfull_refs_rejected(self):
  with self.assertRaisesRegex(ValueError,'이미지 한도'):
   prepare_media([{'kind':'target_identity','path':'unused'}]*51,'unused')
 def test_huge_request_requires_time_split(self):
  with self.assertRaisesRegex(ValueError,'구간'):
   prepare_media([{'kind':'source','path':'unused'}]*321,'unused')
if __name__=='__main__':unittest.main()

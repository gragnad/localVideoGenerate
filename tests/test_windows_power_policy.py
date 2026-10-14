import tempfile,unittest
from pathlib import Path
from unittest import mock
import windows_power_policy as policy
import remote_render_power as power
import ui_backend

class WindowsAutoPowerTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def manager(self):
  cfg=power.Config(comfy_url='http://test',agent_url='http://test',agent_token='test',wol_mac='',wol_broadcast='',hibernate_idle_seconds=1)
  m=power.RemoteRenderPowerManager(cfg,root=self.root);m.hibernate_armed=True;m.last_activity=0
  m._comfy_busy=mock.Mock(return_value=False);m._agent_request=mock.Mock(return_value={'status':'hibernate_scheduled'});m._wait_for_agent_offline=mock.Mock()
  return m
 def test_default_and_persistence(self):
  self.assertTrue(policy.get_policy(self.root)['auto_hibernate_enabled'])
  policy.set_policy(self.root,False);self.assertFalse(policy.get_policy(self.root)['auto_hibernate_enabled'])
  policy.set_policy(self.root,True);self.assertTrue(policy.get_policy(self.root)['auto_hibernate_enabled'])
 def test_nonboolean_rejected(self):
  for v in ['false',0,1,None,{}]:
   with self.assertRaises(ValueError):policy.set_policy(self.root,v)
 def test_off_blocks_power_request_and_resets_idle(self):
  m=self.manager();policy.set_policy(self.root,False)
  self.assertFalse(m.maybe_hibernate());m._agent_request.assert_not_called();m._comfy_busy.assert_not_called();self.assertGreater(m.last_activity,0)
 def test_existing_manager_observes_on_off_changes(self):
  m=self.manager();policy.set_policy(self.root,False);self.assertFalse(m.maybe_hibernate())
  policy.set_policy(self.root,True);m.last_activity=0
  self.assertTrue(m.maybe_hibernate());m._agent_request.assert_called_once()
 def test_busy_still_blocks_when_enabled(self):
  m=self.manager();m._comfy_busy.return_value=True
  self.assertFalse(m.maybe_hibernate());m._agent_request.assert_not_called()
 def test_disable_during_busy_probe_blocks_request(self):
  m=self.manager()
  def probe():policy.set_policy(self.root,False);return False
  m._comfy_busy.side_effect=probe
  self.assertFalse(m.maybe_hibernate());m._agent_request.assert_not_called()
 def test_corrupt_policy_blocks_shutdown(self):
  p=self.root/'runtime/h3/windows_power_policy.json';p.parent.mkdir(parents=True);p.write_text('{')
  m=self.manager();self.assertFalse(m.maybe_hibernate());m._agent_request.assert_not_called()
 def test_api_uses_same_policy(self):
  with mock.patch.object(ui_backend,'ROOT',self.root):
   self.assertFalse(ui_backend.set_windows_power_policy({'auto_hibernate_enabled':False})['auto_hibernate_enabled'])
   self.assertEqual(ui_backend.get_windows_power_policy({}),policy.get_policy(self.root))
if __name__=='__main__':unittest.main()

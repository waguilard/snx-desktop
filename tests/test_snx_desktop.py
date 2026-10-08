import importlib.util,tempfile,os,unittest,json,stat
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('snx_app','app.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class Tests(unittest.TestCase):
 def test_invalid_input(self):
  for h,u,p in [('https://x','user','443'),('-g','user','443'),('vpn.x','u\npass','443'),('vpn.x','user','70000')]:
   with self.assertRaises(ValueError):a.validate(h,u,p)
 def test_private_profile(self):
  with tempfile.TemporaryDirectory() as d,patch.object(a,'CONFIG',Path(d)/'cfg/profile.json'):
   a.save_profile(dict(site='Test',host='vpn.example',user='user',port='443'))
   self.assertEqual(stat.S_IMODE(a.CONFIG.stat().st_mode),0o600)
   self.assertNotIn('password',a.CONFIG.read_text())
 def test_ui_connect_never_captures_password(self):
  with tempfile.TemporaryDirectory() as d,patch.object(a,'CONFIG',Path(d)/'profile.json'):
   app=a.App();app.withdraw();app.vars['user'].set('corporate-user');app.vars['host'].set('vpn.example')
   with patch.object(a,'local_state',return_value=('Desconectada','',False)),patch.object(a.subprocess,'Popen') as launch:
    app.connect();args=launch.call_args.args[0]
    self.assertIn('konsole',args);self.assertIn('corporate-user',args);self.assertNotIn('stdin',launch.call_args.kwargs)
   app.wizard();app.update();self.assertTrue(any(isinstance(w,a.tk.Toplevel) for w in app.winfo_children()));app.destroy()
 def test_unrelated_tunnel_not_vpn(self):
  from types import SimpleNamespace
  data=[{'ifname':'tailscale0','addr_info':[{'family':'inet','local':'100.1.1.1'}]}]
  with patch.object(a.subprocess,'run',side_effect=[SimpleNamespace(stdout=json.dumps(data)),SimpleNamespace(returncode=1)]):
   self.assertFalse(a.local_state()[2])
 def test_snx_interface(self):
  from types import SimpleNamespace
  data=[{'ifname':'tunsnx','addr_info':[{'family':'inet','local':'10.1.2.3'}]}]
  with patch.object(a.subprocess,'run',side_effect=[SimpleNamespace(stdout=json.dumps(data)),SimpleNamespace(returncode=0)]):
   self.assertEqual(a.local_state()[1],'10.1.2.3')
unittest.main()

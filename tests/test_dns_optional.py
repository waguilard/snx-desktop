import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('dns','dns/service.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
class OptionalDNS(unittest.TestCase):
 def test_empty_and_configured(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(d,'SETTINGS',Path(tmp)/'settings.json'):
   self.assertEqual(d.load_settings(),((),()))
   d.SETTINGS.write_text(json.dumps({'dns_suffixes':['corp.example'],'dns_routes':['app.example']}))
   self.assertEqual(d.load_settings(),(('corp.example',),('app.example',)))
 def test_reject_injection(self):
  for value in ['x.example\nserver=evil','/example','-x.example','example..com']:
   with self.assertRaises(ValueError):d.domain_list([value])
 def test_unconfigured_preserves_normal_dns(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);r=p/'resolv';baseline='nameserver 192.0.2.1\n';r.write_text(baseline)
   def stop(_):d.stopping=True
   with patch.object(d,'RESOLV',r),patch.object(d,'STATE',p/'state'),patch.object(d,'RUN',p/'run'),patch.object(d,'load_settings',return_value=((),())),patch.object(d,'connected',return_value=True),patch.object(d.time,'sleep',side_effect=stop),patch.object(d.signal,'signal'),patch.object(d.subprocess,'Popen') as launch:
    d.stopping=False;d.main();launch.assert_not_called()
   self.assertEqual(r.read_text(),baseline)
unittest.main()

import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
spec=importlib.util.spec_from_file_location('dns','dns/service.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.DOMAINS=('corp.example','internal.example');d.ROUTED_DOMAINS=d.DOMAINS
class Lifecycle(unittest.TestCase):
 def test_apply_restore(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);r=p/'resolv';normal='search lan\nnameserver 192.0.2.1\n';corp='nameserver 192.0.2.2\nnameserver 192.0.2.1\n';r.write_text(normal)
   tick=[0];observed=[];proc=Mock();proc.poll.return_value=None
   def sleep(seconds):
    if seconds<1:return
    observed.append(r.read_text());tick[0]+=1
    if tick[0]==1:r.write_text(corp)
    if tick[0]>=6:d.stopping=True
   with patch.object(d,'load_settings',return_value=(d.DOMAINS,())),patch.object(d,'RESOLV',r),patch.object(d,'STATE',p/'state'),patch.object(d,'RUN',p/'run'),patch.object(d,'connected',side_effect=lambda:1<=tick[0]<5),patch.object(d.time,'sleep',side_effect=sleep),patch.object(d.time,'monotonic',side_effect=lambda:tick[0]*3),patch.object(d.subprocess,'run'),patch.object(d.subprocess,'Popen',return_value=proc),patch.object(d.signal,'signal'):
    d.stopping=False;d.main()
   self.assertTrue(any(x.startswith(d.MARKER) for x in observed))
   self.assertEqual(r.read_text(),normal);proc.terminate.assert_called()
   conf=(p/'run/dnsmasq.conf').read_text()
   self.assertNotIn('server=/corp.example/192.0.2.1',conf)
   self.assertIn('server=/corp.example/192.0.2.2',conf)
unittest.main()

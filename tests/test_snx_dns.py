import importlib.util,unittest,tempfile,subprocess
from pathlib import Path
spec=importlib.util.spec_from_file_location('dns','dns/service.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.DOMAINS=('corp.example','internal.example');d.ROUTED_DOMAINS=d.DOMAINS
class Tests(unittest.TestCase):
 def test_routes_and_search(self):
  conf=d.make_config(['192.0.2.1'],['192.0.2.2','192.0.2.3'])
  self.assertIn('server=192.0.2.1\n',conf)
  for domain in d.DOMAINS:
   self.assertIn('server=/'+domain+'/192.0.2.2',conf)
  self.assertIn('no-resolv',conf);self.assertIn('listen-address=127.0.0.54',conf)
  text=d.replacement('search lan\nnameserver 192.0.2.1\n')
  self.assertIn('search corp.example internal.example lan',text)
 def test_validate_dns(self):
  self.assertEqual(d.parse_dns('nameserver bad\nnameserver 127.0.0.54\nnameserver 192.0.2.1\n'),['192.0.2.1'])
  with self.assertRaises(ValueError):d.make_config([],['192.0.2.1'])
 def test_dnsmasq_syntax(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'conf';p.write_text(d.make_config(['192.0.2.1'],['192.0.2.2']))
   r=subprocess.run(['/usr/sbin/dnsmasq','--test','--conf-file='+str(p)],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)
unittest.main()

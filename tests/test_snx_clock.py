import importlib.util,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('app','app.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class ClockTests(unittest.TestCase):
 def test_reopen_and_reconnect(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'clock.json';c=a.SessionClock(p)
   c.update(False,None,None,100);c.update(True,'one',90,110)
   self.assertEqual(c.label(175),'Tiempo: 00:01:05')
   reopened=a.SessionClock(p);reopened.update(True,'one',90,180)
   self.assertEqual(reopened.label(180),'Tiempo: 00:01:10')
   reopened.update(False,None,None,190);self.assertFalse(p.exists())
   reopened.update(True,'two',195,200)
   self.assertEqual(reopened.label(205),'Tiempo: 00:00:05')
 def test_existing_session_is_approximate(self):
  with tempfile.TemporaryDirectory() as d:
   c=a.SessionClock(Path(d)/'clock.json');c.update(True,'existing',100,200)
   self.assertEqual(c.label(3700),'Tiempo aprox.: 01:00:00')
 def test_durations(self):
  self.assertEqual(a.format_duration(90061),'25:01:01')
  self.assertEqual(a.format_duration(-2),'00:00:00')
unittest.main()

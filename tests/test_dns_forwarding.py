import importlib.util,subprocess,tempfile,socket,struct,threading,time
from pathlib import Path
spec=importlib.util.spec_from_file_location('dns','dns/service.py');d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)
d.DOMAINS=('corp.example','internal.example');d.ROUTED_DOMAINS=d.DOMAINS
seen={'normal':[],'corp':[]};listeners=[];stop=threading.Event()
def serve(sock,label):
 sock.settimeout(.1)
 while not stop.is_set():
  try:data,addr=sock.recvfrom(4096)
  except socket.timeout:continue
  except OSError:return
  seen[label].append(data)
  reply=data[:2]+struct.pack('!HHHHH',0x8183,1,0,0,0)+data[12:]
  sock.sendto(reply,addr)
for label in seen:
 s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.bind(('127.0.0.1',0));listeners.append(s)
 threading.Thread(target=serve,args=(s,label),daemon=True).start()
with tempfile.TemporaryDirectory() as folder:
 config=d.make_config(['192.0.2.1'],['192.0.2.2']).replace('listen-address=127.0.0.54','listen-address=127.0.0.1').replace('port=53','port=0')
 # Select a high available local DNS port and avoid any real upstream.
 sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
 config=config.replace('port=0',f'port={port}').replace('user=dnsmasq','user='+__import__('getpass').getuser()).replace('group=nogroup','group='+__import__('grp').getgrgid(__import__('os').getgid()).gr_name)
 config=config.replace('192.0.2.1',f'127.0.0.1#{listeners[0].getsockname()[1]}').replace('192.0.2.2',f'127.0.0.1#{listeners[1].getsockname()[1]}')
 p=Path(folder)/'conf';p.write_text(config)
 proc=subprocess.Popen(['/usr/sbin/dnsmasq','--keep-in-foreground','--conf-file='+str(p)],stderr=subprocess.PIPE)
 try:
  time.sleep(.15);assert proc.poll() is None
  def query(name):
   q=struct.pack('!HHHHHH',123,0x100,1,0,0,0)+b''.join(bytes([len(part)])+part.encode() for part in name.split('.'))+b'\x00'+struct.pack('!HH',1,1)
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:s.settimeout(2);s.sendto(q,('127.0.0.1',port));s.recvfrom(4096)
  query('test.corp.example');query('test.internal.example');query('test.example')
  assert len(seen['corp'])==2 and len(seen['normal'])==1,seen
  print('DNS dividido verificado con servidores simulados exclusivamente en loopback')
 finally:proc.terminate();proc.wait(timeout=3)
stop.set()
for s in listeners:s.close()

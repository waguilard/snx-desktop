#!/usr/bin/python3
"""Scoped SNX DNS integration. Uses only resolver addresses supplied during VPN."""
import ipaddress,json,os,signal,subprocess,time,re,sys
from pathlib import Path
DOMAINS=()
ROUTED_DOMAINS=()
SETTINGS=Path('/var/lib/snx-desktop-dns/settings.json')

def domain_list(values):
    if not isinstance(values,list) or len(values)>20:raise ValueError('Lista de dominios inválida')
    result=[]
    for value in values:
        if not isinstance(value,str):raise ValueError('Dominio inválido')
        value=value.strip().lower().rstrip('.')
        if len(value)>253 or '.' not in value or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in value.split('.')):raise ValueError('Dominio inválido: '+value)
        if value not in result:result.append(value)
    return result

def load_settings():
    try:
        obj=json.loads(SETTINGS.read_text())
        return tuple(domain_list(obj.get('dns_suffixes',[]))),tuple(domain_list(obj.get('dns_routes',[])))
    except (OSError,ValueError,TypeError):return (),()

def configure(profile):
    """Copy validated domain lists into root-owned settings; ignore all other keys."""
    if os.geteuid()!=0:raise ValueError('Se requieren privilegios para configurar DNS')
    obj=json.loads(Path(profile).read_text())
    settings={key:domain_list(obj.get(key,[])) for key in ('dns_suffixes','dns_routes')}
    SETTINGS.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    tmp=SETTINGS.with_suffix('.tmp');tmp.write_text(json.dumps(settings));os.chmod(tmp,0o600);os.replace(tmp,SETTINGS)

MARKER='# SNX Desktop split DNS\n'
ADDRESS='127.0.0.54'
RESOLV=Path('/etc/resolv.conf');STATE=Path('/var/lib/snx-desktop-dns');RUN=Path('/run/snx-desktop-dns')
stopping=False

def parse_dns(text):
    ips=[]
    for line in text.splitlines():
        p=line.split()
        if len(p)>=2 and p[0]=='nameserver':
            try:ip=ipaddress.ip_address(p[1])
            except ValueError:continue
            if not ip.is_loopback and not ip.is_unspecified:ips.append(str(ip))
    return list(dict.fromkeys(ips))

def searches(text):
    for line in text.splitlines():
        p=line.split()
        if p and p[0] in ('search','domain'):return p[1:]
    return []

def make_config(normal,corporate):
    """Send ordinary DNS to baseline servers; route only configured domains to SNX."""
    if not normal or not corporate:raise ValueError('Faltan DNS locales o de SNX')
    lines=['no-resolv','bind-interfaces',f'listen-address={ADDRESS}','port=53','user=dnsmasq','group=nogroup','cache-size=150','no-hosts','pid-file=','log-facility=-']
    for ip in normal:lines.append('server='+str(ipaddress.ip_address(ip)))
    for domain in ROUTED_DOMAINS:
        for ip in corporate:lines.append(f'server=/{domain}/'+str(ipaddress.ip_address(ip)))
    return '\n'.join(lines)+'\n'

def replacement(baseline):
    domains=list(dict.fromkeys([*DOMAINS,*searches(baseline)]))[:6]
    options=[l for l in baseline.splitlines() if l.startswith('options ')]
    return MARKER+'search '+' '.join(domains)+'\n'+'nameserver '+ADDRESS+'\n'+'\n'.join(options)+'\n'

def write_resolver(text):
    # Preserve NetworkManager's existing inode/mode; refuse unexpected symlinks.
    if RESOLV.is_symlink():raise RuntimeError('resolv.conf cambió a enlace simbólico')
    with RESOLV.open('w') as f:f.write(text);f.flush();os.fsync(f.fileno())

def status(text):
    tmp=RUN/'status.tmp';tmp.write_text(json.dumps({'message':text,'domains':DOMAINS}));os.chmod(tmp,0o644);os.replace(tmp,RUN/'status.json')

def connected():
    return any(p.name.lower().startswith(('tunsnx','snx')) for p in Path('/sys/class/net').iterdir())

def tunnel_key():
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    tunnels=[p for p in Path('/sys/class/net').iterdir() if p.name.lower().startswith(('tunsnx','snx'))]
    return boot+':'+','.join(sorted((p/'ifindex').read_text().strip() for p in tunnels))

def remembered_dns():
    try:
        saved=json.loads((STATE/'session.json').read_text())
        if saved.get('key')==tunnel_key():return [str(ipaddress.ip_address(i)) for i in saved['dns']]
    except (OSError,ValueError,KeyError,TypeError):pass
    return []

def main():
    global stopping,DOMAINS,ROUTED_DOMAINS
    DOMAINS,routes=load_settings();ROUTED_DOMAINS=tuple(dict.fromkeys((*DOMAINS,*routes)))
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700);RUN.mkdir(parents=True,exist_ok=True,mode=0o755)
    signal.signal(signal.SIGTERM,lambda *_:stop());signal.signal(signal.SIGINT,lambda *_:stop())
    backup=STATE/'resolv.before';baseline=backup.read_text() if backup.exists() else ''
    current=RESOLV.read_text()
    if current.startswith(MARKER):
        if not baseline:raise RuntimeError('Falta el respaldo DNS para recuperar')
        write_resolver(baseline)
    proxy=None;applied=None;was_active=False;stable=None;stable_at=0
    try:
        while not stopping:
            active=connected();current=RESOLV.read_text()
            suffixes,routes=load_settings();routed=tuple(dict.fromkeys((*suffixes,*routes)))
            if suffixes!=DOMAINS or routed!=ROUTED_DOMAINS:
                if applied and current==applied:write_resolver(baseline);current=baseline
                if proxy:proxy.terminate();proxy.wait(timeout=5);proxy=None
                applied=None;stable=None;DOMAINS=suffixes;ROUTED_DOMAINS=routed
            if not ROUTED_DOMAINS:
                status('DNS: No configurado');time.sleep(1);continue
            if not active:
                if applied and current==applied:write_resolver(baseline);current=baseline
                if proxy:proxy.terminate();proxy.wait(timeout=5);proxy=None
                applied=None;stable=None;was_active=False
                if not current.startswith(MARKER):
                    baseline=current;backup.write_text(baseline);os.chmod(backup,0o600)
                (STATE/'session.json').unlink(missing_ok=True)
                status('DNS corporativo en espera de VPN')
            elif applied:
                if proxy.poll() is not None:
                    if current==applied:write_resolver(baseline)
                    applied=None;proxy=None;status('Error: el resolvedor local se detuvo')
                elif current!=applied:
                    # Never overwrite a concurrent NetworkManager/SNX change blindly.
                    proxy.terminate();proxy.wait(timeout=5);proxy=None;applied=None
                    stable=None;status('DNS cambió; revisando configuración de SNX')
                else:status('DNS dividido y sufijos activos')
            else:
                normal=parse_dns(baseline)
                corp=[ip for ip in parse_dns(current) if ip not in normal]
                if not corp:corp=remembered_dns()
                if not baseline or not normal or not corp or corp==normal or current.startswith(MARKER):
                    status('VPN presente; esperando DNS proporcionados por SNX')
                elif current!=stable:stable=current;stable_at=time.monotonic()
                elif time.monotonic()-stable_at>=2:
                    conf=RUN/'dnsmasq.conf';conf.write_text(make_config(normal,corp));os.chmod(conf,0o600)
                    subprocess.run(['/usr/sbin/dnsmasq','--test','--conf-file='+str(conf)],check=True,capture_output=True,timeout=5)
                    proxy=subprocess.Popen(['/usr/sbin/dnsmasq','--keep-in-foreground','--conf-file='+str(conf)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    time.sleep(.3)
                    if proxy.poll() is not None:proxy=None;status('Error: no se pudo iniciar DNS local');stable_at=time.monotonic()
                    elif RESOLV.read_text()!=current or not connected():
                        proxy.terminate();proxy.wait(timeout=5);proxy=None;stable=None
                    else:
                        saved=STATE/'session.json'
                        saved.write_text(json.dumps({'key':tunnel_key(),'dns':corp}));os.chmod(saved,0o600)
                        applied=replacement(baseline);write_resolver(applied)
                        status('DNS dividido y sufijos activos')
            time.sleep(1)
    finally:
        if applied and RESOLV.read_text()==applied:write_resolver(baseline)
        if proxy and proxy.poll() is None:proxy.terminate();proxy.wait(timeout=5)
        status('Integración DNS detenida')

def stop():
    global stopping
    stopping=True
if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--configure':configure(sys.argv[2])
    else:main()

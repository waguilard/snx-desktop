#!/usr/bin/python3
"""Local SNX front-end. Credentials remain in SNX's interactive terminal."""
import json, os, re, shutil, subprocess, sys, threading, time, socket, fcntl, tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
BASE=Path(__file__).resolve().parent
CONFIG=Path(os.environ.get('SNX_DESKTOP_CONFIG',Path.home()/'.config/snx-desktop/profile.json'))
DNS_SERVICE=Path('/usr/local/libexec/snx-desktop-dns.py')

def domains(text):
    values=[]
    for value in re.split(r'[\s,;]+',text.strip()):
        if not value:continue
        value=value.lower().rstrip('.')
        if len(value)>253 or '.' not in value or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',part) for part in value.split('.')):raise ValueError('Dominio inválido: '+value)
        if value not in values:values.append(value)
    if len(values)>20:raise ValueError('Máximo 20 dominios.')
    return values

def apply_dns():
    if not DNS_SERVICE.exists():return
    env=dict(os.environ,SUDO_ASKPASS='/usr/bin/ksshaskpass')
    result=subprocess.run(['sudo','-A','/usr/bin/python3',str(DNS_SERVICE),'--configure',str(CONFIG)],env=env,capture_output=True,text=True)
    if result.returncode:raise OSError('No se pudo aplicar la configuración DNS. El perfil local está guardado; vuelve a intentarlo desde Configurar.')

BG='#f5f7fb';BLUE='#345fc8';INK='#20314b'

def validate(host,user,port):
    if not host or host.startswith('-') or not re.fullmatch(r'[A-Za-z0-9._:\-]+',host):
        raise ValueError('Introduce un servidor válido, sin https:// ni rutas.')
    if not user or user.startswith('-') or len(user)>160 or any(c.isspace() or ord(c)<32 for c in user):
        raise ValueError('Introduce tu usuario corporativo sin espacios.')
    if not str(port).isdigit() or not 1<=int(port)<=65535:
        raise ValueError('El puerto debe estar entre 1 y 65535.')

def save_profile(p):
    """Write only user configuration, atomically, with owner-only permissions."""
    validate(p['host'],p['user'],p['port'])
    CONFIG.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(CONFIG.parent,0o700)
    tmp=CONFIG.with_suffix('.tmp')
    fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:json.dump(p,f,indent=2)
    os.replace(tmp,CONFIG);os.chmod(CONFIG,0o600)

def read_profile():
    """A fresh install starts with no server, user, or DNS domains."""
    try:
        p=json.loads(CONFIG.read_text());return {**{k:str(p[k]) for k in ('site','host','user','port')},'dns_suffixes':domains(' '.join(p.get('dns_suffixes',[]))),'dns_routes':domains(' '.join(p.get('dns_routes',[])))}
    except (OSError,ValueError,KeyError,TypeError):
        return dict(site='VPN corporativa',host='',user='',port='443',dns_suffixes=[],dns_routes=[])

def local_state():
    try:
        interfaces=json.loads(subprocess.run(['ip','-j','addr'],capture_output=True,text=True,timeout=3).stdout)
        active=subprocess.run(['pgrep','-x','snx'],capture_output=True,timeout=3).returncode==0
        # Recognize only SNX's own interface; Tailscale/other tunnels are excluded.
        snx=[i for i in interfaces if i['ifname'].lower().startswith(('tunsnx','snx'))]
        ips=[a['local'] for i in snx for a in i.get('addr_info',[]) if a['family']=='inet']
        if ips:return 'Túnel SNX presente',', '.join(ips),True
        if active:return 'SNX activo; túnel no confirmado','Sin IP SNX identificada',True
        return 'Desconectada','Sin sesión SNX detectada',False
    except (OSError,ValueError,subprocess.TimeoutExpired):return 'Estado no disponible','Revisa las herramientas locales',False

def session_identity():
    """Stable identity and approximate start of the SNX process, across UI restarts."""
    try:
        boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        ticks=os.sysconf('SC_CLK_TCK')
        uptime=float(Path('/proc/uptime').read_text().split()[0])
        candidates=[]
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:
                raw=(proc/'stat').read_text()
                name=raw[raw.index('(')+1:raw.rindex(')')]
                if name!='snx':continue
                fields=raw[raw.rindex(')')+2:].split()
                start=int(fields[19])/ticks
                candidates.append((fields[1]=='1',start,proc.name))
            except (OSError,ValueError,IndexError):continue
        if not candidates:return None,None
        _,start,pid=max(candidates)
        return f'{boot}:{pid}:{start}',time.time()-max(0,uptime-start)
    except (OSError,ValueError):return None,None

def format_duration(seconds):
    seconds=max(0,int(seconds));hours,rem=divmod(seconds,3600);minutes,sec=divmod(rem,60)
    return f'{hours:02d}:{minutes:02d}:{sec:02d}'

class SessionClock:
    def __init__(self,path):
        self.path=path;self.start=None;self.key=None;self.approx=False;self.observed_disconnected=False
    def update(self,connected,key,estimated,now=None):
        now=time.time() if now is None else now
        if not connected:
            self.start=None;self.key=None;self.approx=False;self.observed_disconnected=True
            try:self.path.unlink(missing_ok=True)
            except OSError:pass
            return
        key=key or 'observed-session'
        if key==self.key and self.start is not None:return
        saved={}
        try:saved=json.loads(self.path.read_text())
        except (OSError,ValueError):pass
        if not isinstance(saved,dict):saved={}
        if key!='observed-session' and saved.get('key')==key and isinstance(saved.get('start'),(int,float)):
            self.start=min(now,float(saved['start']));self.approx=bool(saved.get('approx',False))
        else:
            self.start=now if self.observed_disconnected or estimated is None else min(now,estimated)
            self.approx=not self.observed_disconnected
        self.key=key
        try:
            self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            fd=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
            with os.fdopen(fd,'w') as f:json.dump(dict(key=key,start=self.start,approx=self.approx),f)
        except OSError:pass
    def label(self,now=None):
        if self.start is None:return 'Tiempo: --:--:--'
        value=format_duration((time.time() if now is None else now)-self.start)
        return ('Tiempo aprox.: ' if self.approx else 'Tiempo: ')+value

class App(tk.Tk):
    def __init__(self):
        super().__init__();self.title('SNX Desktop - VPN');self.geometry('630x448');self.minsize(630,448)
        self.configure(bg=BG);self.profile=read_profile();self.busy=False
        self.clock=SessionClock(CONFIG.parent/'session-clock.json');self.duration=tk.StringVar(value='Tiempo: --:--:--')
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('TFrame',background=BG);style.configure('TLabel',background=BG,foreground=INK,font=('DejaVu Sans',8))
        style.configure('TButton',font=('DejaVu Sans',8),padding=(11,7))
        style.configure('Primary.TButton',background=BLUE,foreground='white')
        style.map('Primary.TButton',background=[('active','#244dae'),('disabled','#aab6cc')])
        style.configure('TEntry',padding=5,font=('DejaVu Sans',8));style.configure('TCombobox',padding=5)
        banner=tk.Canvas(self,height=80,highlightthickness=0,bg=BLUE);banner.pack(fill='x')
        for x in range(630):
            c=int(73+x/630*45);banner.create_line(x,0,x,80,fill=f'#{35:02x}{c:02x}{190:02x}')
        banner.create_text(22,26,text='SNX Desktop',anchor='w',fill='white',font=('DejaVu Sans',18,'bold'))
        banner.create_text(23,54,text='Acceso remoto · Check Point SNX',anchor='w',fill='#e4ecff',font=('DejaVu Sans',9))
        banner.create_text(600,35,text='VPN',anchor='e',fill='white',font=('DejaVu Sans',18,'bold'))
        body=ttk.Frame(self,padding=14);body.pack(fill='both',expand=True)
        left=ttk.Frame(body);left.grid(row=0,column=0,sticky='nsew');body.columnconfigure(0,weight=1)
        self.vars={k:tk.StringVar(value=self.profile[k]) for k in ('site','host','user','port')}
        for row,(key,label) in enumerate([('site','Sitio'),('host','Servidor VPN')]):
            ttk.Label(left,text=label).grid(row=row,column=0,sticky='w',pady=3,padx=(0,12))
            ttk.Entry(left,textvariable=self.vars[key],width=29).grid(row=row,column=1,sticky='ew',pady=3)
        ttk.Separator(left).grid(row=3,columnspan=2,sticky='ew',pady=7)
        ttk.Label(left,text='Autenticación',foreground=BLUE,font=('DejaVu Sans',10,'bold')).grid(row=4,columnspan=2,sticky='w')
        ttk.Label(left,text='Usuario corporativo').grid(row=5,column=0,sticky='w',pady=6,padx=(0,12))
        ttk.Entry(left,textvariable=self.vars['user'],width=29).grid(row=5,column=1,sticky='ew')
        ttk.Label(left,text='La contraseña y el certificado se gestionan en Konsole.\nLa app no guarda contraseñas.',font=('DejaVu Sans',8),foreground='#5c6b80').grid(row=6,columnspan=2,sticky='w',pady=3)
        art=tk.Canvas(body,width=144,height=158,bg=BG,highlightthickness=0);art.grid(row=0,column=1,padx=(17,0),sticky='n')
        art.create_arc(50,25,155,155,start=0,extent=180,style='arc',width=18,outline='#ddb343')
        art.create_rectangle(43,87,165,193,fill='#e9c665',outline='#c69e36',width=2)
        art.create_oval(95,123,113,141,fill='#806422',outline='');art.create_polygon(102,134,98,160,110,160,106,134,fill='#806422')
        art.create_oval(135,145,194,204,fill='#5489d2',outline='#3571bb',width=2)
        art.create_arc(137,148,192,201,start=0,extent=359,style='arc',outline='#a5c4ee',width=2)
        art.scale('all',0,0,0.7,0.7)
        ttk.Separator(body).grid(row=1,columnspan=2,sticky='ew',pady=7)
        self.status=tk.StringVar(value='Comprobando estado local…');self.ip=tk.StringVar()
        ttk.Label(body,textvariable=self.status,font=('DejaVu Sans',9,'bold')).grid(row=2,columnspan=2,sticky='w')
        session_row=ttk.Frame(body);session_row.grid(row=3,columnspan=2,sticky='ew',pady=(4,14))
        ttk.Label(session_row,textvariable=self.ip,foreground='#5c6b80').pack(side='left')
        ttk.Label(session_row,textvariable=self.duration,foreground='#5c6b80').pack(side='right')
        self.dns_status=tk.StringVar(value='DNS corporativo: comprobando…')
        ttk.Label(body,textvariable=self.dns_status,foreground='#5c6b80',font=('DejaVu Sans',7)).grid(row=4,columnspan=2,sticky='w',pady=(0,8))
        actions=ttk.Frame(body);actions.grid(row=5,columnspan=2,sticky='ew')
        self.connect_btn=ttk.Button(actions,text='Conectar',style='Primary.TButton',command=self.connect);self.connect_btn.pack(side='left')
        self.disconnect_btn=ttk.Button(actions,text='Desconectar',command=self.disconnect);self.disconnect_btn.pack(side='left',padx=10)
        ttk.Button(actions,text='Configurar',command=self.wizard).pack(side='right')
        ttk.Button(actions,text='Ayuda',command=self.help).pack(side='right',padx=10)
        ttk.Label(self,text='Cliente local independiente · No es una aplicación oficial de Check Point',font=('DejaVu Sans',7),foreground='#66768c',padding=(20,6)).pack(fill='x',side='bottom')
        self.setup_tray()
        self.after(200,self.poll);self.after(1000,self.tick);self.protocol('WM_DELETE_WINDOW',self.close)
        if not CONFIG.exists():self.after(500,self.wizard)
    def values(self):return {**self.profile,**{k:v.get().strip() for k,v in self.vars.items()}}
    def connect(self):
        try:
            p=self.values();save_profile(p)
            if not shutil.which('konsole') or not os.access('/usr/bin/snx',os.X_OK):raise ValueError('Falta Konsole o SNX. Abre Configurar para revisar requisitos.')
            if local_state()[2]:raise ValueError('SNX ya está activo. Desconecta la sesión antes de iniciar otra.')
            subprocess.Popen(['konsole','--separate','-e','/usr/bin/python3',str(BASE/'terminal_session.py'),p['host'],p['user'],p['port']],start_new_session=True)
            self.status.set('Autenticación abierta en Konsole');self.connect_btn.state(['disabled']);self.after(2500,lambda:self.connect_btn.state(['!disabled']))
        except (ValueError,OSError) as e:messagebox.showerror('Conexión',str(e),parent=self)
    def disconnect(self):
        if self.busy:return
        self.busy=True;self.disconnect_btn.state(['disabled']);self.status.set('Desconectando…')
        def work():
            try:r=subprocess.run(['/usr/bin/snx','-d'],capture_output=True,text=True,timeout=20);result=(r.returncode,r.stdout+r.stderr)
            except (OSError,subprocess.TimeoutExpired) as e:result=(1,str(e))
            self.after(0,lambda:self.disconnected(result))
        threading.Thread(target=work,daemon=True).start()
    def disconnected(self,r):
        self.busy=False;self.disconnect_btn.state(['!disabled'])
        if r[0]:messagebox.showerror('Desconexión',r[1].strip() or 'SNX informó un error.',parent=self)
        self.refresh()
    def refresh(self):
        """Poll local process/interface state; never probe the VPN gateway."""
        if not self.busy:
            state,ip,active=local_state();self.status.set(state);self.ip.set(ip)
            if state!='Estado no disponible':
                key,estimated=session_identity() if state=='Túnel SNX presente' else (None,None)
                self.clock.update(state=='Túnel SNX presente',key,estimated)
            self.duration.set(self.clock.label())
            try:
                dns=json.loads(Path('/run/snx-desktop-dns/status.json').read_text())
                self.dns_status.set('DNS: No configurado' if not self.profile.get('dns_suffixes') and not self.profile.get('dns_routes') else dns['message'])
            except (OSError,ValueError,KeyError):self.dns_status.set('DNS: No configurado' if not self.profile.get('dns_suffixes') and not self.profile.get('dns_routes') else 'DNS: integración no disponible')
            self.disconnect_btn.state(['!disabled'] if active else ['disabled'])
            self.connect_btn.state(['disabled'] if active else ['!disabled'])
    def tick(self):
        self.duration.set(self.clock.label());self.after(1000,self.tick)
    def poll(self):self.refresh();self.after(3000,self.poll)
    def setup_tray(self):
        self.tray_process=None;self.tray_ready=False;self.control=None
        try:
            CONFIG.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            self.control_path=CONFIG.parent/'control.sock'
            self.control_path.unlink(missing_ok=True)
            self.control=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)
            self.control.bind(str(self.control_path));os.chmod(self.control_path,0o600)
            self.control.setblocking(False)
            self.tray_process=subprocess.Popen(['/usr/bin/python3',str(BASE/'tray.py'),str(self.control_path),str(os.getpid())],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            os.set_blocking(self.tray_process.stdout.fileno(),False)
            self.after(100,self.tray_poll)
        except OSError:self.tray_ready=False
    def tray_poll(self):
        if self.tray_process:
            try:
                data=os.read(self.tray_process.stdout.fileno(),4096)
                if b'READY' in data:self.tray_ready=True
                if self.tray_process.poll() is not None:self.tray_ready=False
            except (BlockingIOError,OSError):pass
        if self.control:
            try:
                while True:
                    command=self.control.recv(128).decode()
                    if command=='show':self.deiconify();self.lift()
                    elif command=='connect':self.deiconify();self.lift();self.connect()
                    elif command=='disconnect':self.disconnect()
                    elif command=='quit':self.quit_app();return
            except BlockingIOError:pass
        # If KDE's tray disappears, recover the hidden window.
        if not self.tray_ready and self.state()=='withdrawn':self.deiconify()
        self.after(200,self.tray_poll)
    def close(self):
        if self.tray_ready:self.withdraw()
        else:self.quit_app()
    def quit_app(self):
        if local_state()[2] and not messagebox.askyesno('Salir','La VPN seguirá conectada.\n¿Salir solo de la app?',parent=self):return
        if self.tray_process and self.tray_process.poll() is None:self.tray_process.terminate()
        if self.control:self.control.close()
        if hasattr(self,'control_path'):
            try:self.control_path.unlink(missing_ok=True)
            except OSError:pass
        self.destroy()
    def help(self):
        doc=BASE/'docs/GUIA.md'
        if doc.exists():subprocess.Popen(['xdg-open',str(doc)])
        else:messagebox.showinfo('Ayuda','Conectar abre Konsole. Desconectar ejecuta snx -d.\nCerrar la ventana no desconecta la VPN.\nComprueba IPs con ip -br addr.',parent=self)
    def wizard(self):
        """Collect connection and optional DNS settings without handling passwords."""
        win=tk.Toplevel(self);win.title('Asistente de instalación y configuración');win.geometry('660x490');win.configure(bg=BG);win.transient(self);win.grab_set()
        frame=ttk.Frame(win,padding=26);frame.pack(fill='both',expand=True)
        heading=ttk.Label(frame,font=('DejaVu Sans',12,'bold'),foreground=BLUE);heading.pack(anchor='w',pady=(0,16))
        content=ttk.Frame(frame);content.pack(fill='both',expand=True)
        buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=15);step=[0]
        draft={k:tk.StringVar(value=v.get()) for k,v in self.vars.items()}
        use_dns=tk.BooleanVar(value=bool(self.profile.get('dns_suffixes')))
        suffix=tk.StringVar(value=' '.join(self.profile.get('dns_suffixes',[])))
        routes=tk.StringVar(value=' '.join(self.profile.get('dns_routes',[])))
        def render():
            for c in content.winfo_children():c.destroy()
            prev.state(['disabled'] if step[0]==0 else ['!disabled']);nxt.configure(text='Guardar y finalizar' if step[0]==3 else 'Siguiente')
            if step[0]==0:
                heading.configure(text='1 / 4 · Comprobar instalación')
                rows=[('Python y Tk','Disponible'),('Konsole','Disponible' if shutil.which('konsole') else 'Falta'),('Check Point SNX','Instalado' if os.access('/usr/bin/snx',os.X_OK) else 'Falta'),('Autenticación','Interactiva; sin guardar contraseña')]
                for a,b in rows:ttk.Label(content,text=f'{a}: {b}').pack(anchor='w',pady=3)
                ttk.Label(content,text='La app reutiliza la instalación SNX existente.\nSi falta SNX, sigue la KDB antes de configurar.\nEl asistente no descarga software ni contacta al gateway.',wraplength=590,foreground='#5c6b80').pack(anchor='w',pady=6)
                nxt.state(['!disabled'] if os.access('/usr/bin/snx',os.X_OK) and shutil.which('konsole') else ['disabled'])
            elif step[0]==1:
                heading.configure(text='2 / 4 · Configurar el sitio')
                for i,(k,label) in enumerate([('site','Nombre del sitio'),('host','Servidor VPN'),('user','Usuario corporativo')]):
                    ttk.Label(content,text=label).grid(row=i,column=0,sticky='w',pady=10,padx=(0,14));ttk.Entry(content,textvariable=draft[k],width=36).grid(row=i,column=1,pady=10)
            elif step[0]==2:
                heading.configure(text='3 / 4 · DNS opcional')
                ttk.Checkbutton(content,text='¿Deseas especificar sufijos DNS?',variable=use_dns).pack(anchor='w',pady=8)
                ttk.Label(content,text='Sufijos DNS (separados por espacios):').pack(anchor='w')
                entry=ttk.Entry(content,textvariable=suffix,width=55);entry.pack(fill='x',pady=8)
                def toggle(*_):entry.state(['!disabled'] if use_dns.get() else ['disabled'])
                use_dns.trace_add('write',toggle);toggle()
                ttk.Label(content,text='Nombres o dominios adicionales que deben usar DNS de la VPN:').pack(anchor='w')
                ttk.Entry(content,textvariable=routes,width=55).pack(fill='x',pady=8)
                ttk.Label(content,text='Opcional. Internet conserva el DNS de tu red habitual.\nEstos datos se guardan únicamente en este equipo.\nAplicar cambios DNS requiere autorización gráfica de KDE.',wraplength=590).pack(anchor='w',pady=8)
            else:
                heading.configure(text='4 / 4 · Revisar configuración')
                for k,label in [('site','Sitio'),('host','Servidor'),('user','Usuario')]:ttk.Label(content,text=f'{label}: {draft[k].get()}').pack(anchor='w',pady=7)
                ttk.Label(content,text='Sufijos DNS: '+(suffix.get() if use_dns.get() and suffix.get().strip() else 'No configurado')).pack(anchor='w')
                ttk.Label(content,text='Se guardará un perfil privado en tu cuenta local.\nLa contraseña se introduce en Konsole en cada conexión.\nLa aceptación del certificado queda bajo tu control.\nGuardar no inicia la VPN.',foreground='#5c6b80').pack(anchor='w',pady=7)
        def advance():
            if step[0]>=1:
                try:validate(draft['host'].get().strip(),draft['user'].get().strip(),draft['port'].get().strip())
                except ValueError as e:messagebox.showerror('Configuración',str(e),parent=win);return
            if step[0]==3:
                p={k:v.get().strip() for k,v in draft.items()}
                try:
                    p['dns_suffixes']=domains(suffix.get()) if use_dns.get() else []
                    p['dns_routes']=domains(routes.get())
                    save_profile(p);apply_dns()
                except (OSError,ValueError) as e:messagebox.showerror('Guardar',str(e),parent=win);return
                self.profile=p
                for k in self.vars:self.vars[k].set(p[k])
                self.refresh()
                win.destroy();return
            step[0]+=1;render()
        def back():step[0]=max(0,step[0]-1);render()
        ttk.Button(buttons,text='Cancelar',command=win.destroy).pack(side='left')
        nxt=ttk.Button(buttons,text='Siguiente',style='Primary.TButton',command=advance);nxt.pack(side='right')
        prev=ttk.Button(buttons,text='Atrás',command=back);prev.pack(side='right',padx=10);render()

def run_single_instance():
    CONFIG.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    lock=open(CONFIG.parent/'app.lock','a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as control:
                control.sendto(b'show',str(CONFIG.parent/'control.sock'))
        except OSError:pass
        return
    App().mainloop()
if __name__=='__main__':run_single_instance()

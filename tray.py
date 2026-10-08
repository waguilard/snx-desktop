#!/usr/bin/python3
"""KDE StatusNotifier-compatible tray, no credential handling."""
import socket,sys,os,json
from pathlib import Path
from PyQt6.QtWidgets import QApplication,QSystemTrayIcon,QMenu
from PyQt6.QtGui import QIcon,QAction,QPixmap,QPainter,QColor,QPen
from PyQt6.QtCore import QTimer,Qt

def main():
    control=Path(sys.argv[1]);owner=int(sys.argv[2])
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():print('UNAVAILABLE',flush=True);return 1
    pix=QPixmap(64,64);pix.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pix);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor('#345fc8'));painter.setPen(Qt.PenStyle.NoPen);painter.drawRoundedRect(3,3,58,58,13,13)
    painter.setPen(QPen(QColor('white'),5));painter.setBrush(Qt.BrushStyle.NoBrush);painter.drawArc(20,12,24,28,0,180*16)
    painter.setPen(Qt.PenStyle.NoPen);painter.setBrush(QColor('white'));painter.drawRoundedRect(16,28,32,24,4,4)
    painter.setBrush(QColor('#345fc8'));painter.drawEllipse(29,35,6,6);painter.drawRect(31,39,2,6);painter.end()
    tray=QSystemTrayIcon(QIcon(pix),app);tray.setToolTip('SNX Desktop · VPN')
    menu=QMenu()
    def send(command):
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as s:s.sendto(command.encode(),str(control))
        except OSError:app.quit()
    for label,cmd in [('Abrir ventana','show'),('Conectar','connect'),('Desconectar','disconnect')]:
        action=menu.addAction(label);action.triggered.connect(lambda checked=False,c=cmd:send(c))
    menu.addSeparator();menu.addAction('Salir de la app').triggered.connect(lambda:send('quit'))
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason:send('show') if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick) else None)
    tray.show();print('READY',flush=True)
    def check_owner():
        try:os.kill(owner,0)
        except OSError:app.quit()
    timer=QTimer();timer.timeout.connect(check_owner);timer.start(2000)
    return app.exec()
if __name__=='__main__':sys.exit(main())

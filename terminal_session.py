#!/usr/bin/python3
import subprocess,sys
from app import validate

def main():
    if len(sys.argv)!=4:return 2
    host,user,port=sys.argv[1:];validate(host,user,port)
    print('SNX Desktop - Autenticación interactiva\n')
    print('Introduce la contraseña directamente en SNX.\nVerifica con TI cualquier certificado antes de aceptarlo.\n')
    # No pipe, capture, password field, or stdin forwarding: SNX owns the terminal.
    result=subprocess.run(['/usr/bin/snx','-s',host,'-u',user,'-p',port])
    print('\nSNX finalizó con código',result.returncode)
    print('Revisa el mensaje de SNX; el código por sí solo no confirma conexión.')
    input('\nPulsa Enter para cerrar esta terminal…')
    return result.returncode
if __name__=='__main__':sys.exit(main())

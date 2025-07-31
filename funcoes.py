import re
from datetime import datetime

def formatar_telefone(numero):
    # Remove tudo que não for número
    digitos = re.sub(r'\D', '', numero)

    # Remove o +55 se já estiver incluído
    if digitos.startswith('55'):
        digitos = digitos[2:]

    # Verifica se tem DDD e número
    if len(digitos) == 10:
        # Formato fixo: (XX) XXXX-XXXX
        return f'+55 ({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}'
    elif len(digitos) == 11:
        # Formato celular: (XX) XXXXX-XXXX
        return f'+55 ({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}'
    else:
        return 'Número inválido'


def dataAtual(t1=0, t2=1):
    data_agora = datetime.now()
    return data_agora.strftime("%d/%m/%Y  |  %H:%M:%S")
   

def ano_atual():
    ano_agora = datetime.now()
    return ano_agora.strftime("%Y")


import random
import string

def gerar_token_secreto():
    """Gera um token de 6 dígitos contendo letras maiúsculas e números."""
    caracteres = string.ascii_uppercase + string.digits  # Letras maiúsculas e números (0-9)
    token = ''.join(random.choice(caracteres) for i in range(6))
    return token





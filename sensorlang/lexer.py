"""
Analizador Léxico (Lexer) para SensorLang.

Convierte el código fuente en una secuencia de tokens tipados con información
de posición exacta (número de línea y columna) para diagnóstico de errores.
"""

import re
from typing import NamedTuple, Iterable, List


class Token(NamedTuple):
    type: str
    value: str
    linea: int = 1
    columna: int = 1

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r}, L{self.linea}:C{self.columna})"


class LexerError(Exception):
    """Excepción generada ante caracteres o secuencias inválidas en el código fuente."""
    def __init__(self, mensaje: str, linea: int, columna: int):
        super().__init__(f"Error léxico [Línea {linea}, Columna {columna}]: {mensaje}")
        self.linea = linea
        self.columna = columna


PALABRAS_RESERVADAS = {
    'pin': 'PIN_DECL',
    'leer': 'LEER',
    'leer_analogo': 'LEER_ANALOGO',
    'leer_digital': 'LEER_DIGITAL',
    'encender': 'ENCENDER',
    'apagar': 'APAGAR',
    'mostrar': 'MOSTRAR',
    'alerta': 'ALERTA',
    'esperar': 'ESPERAR',
    'si': 'SI',
    'sino': 'SINO',
}

REGLAS = [
    ('COMENTARIO_BLOQUE', r'/\*[\s\S]*?\*/'),
    ('COMENTARIO_LINEA',  r'(//|#)[^\n]*'),
    ('CADENA',            r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''),
    ('NUMERO',            r'\d+(?:\.\d+)?'),
    ('OP_COMP',           r'==|!=|<=|>=|<|>'),
    ('ASIGNAR',           r'='),
    ('OP_ARIT',           r'[\+\-\*/%]'),
    ('LPAREN',            r'\('),
    ('RPAREN',            r'\)'),
    ('LLAVE_I',           r'\{'),
    ('LLAVE_D',           r'\}'),
    ('PUNTOCOMA',         r';'),
    ('COMA',              r','),
    ('ID',                r'[A-Za-z_][A-Za-z0-9_]*'),
    ('SALTO_LINEA',       r'\n'),
    ('ESPACIOS',          r'[ \t\r]+'),
    ('MISMATCH',          r'.'),
]

REGEX_TOKENS = '|'.join(f'(?P<{nombre}>{patron})' for nombre, patron in REGLAS)


def lexer(codigo: str) -> Iterable[Token]:
    """
    Genera un flujo de tokens a partir de una cadena de código fuente en SensorLang.
    Ignora espacios en blanco y comentarios, actualizando la línea y columna correspondientes.
    """
    linea = 1
    inicio_linea = 0

    for match in re.finditer(REGEX_TOKENS, codigo):
        tipo = match.lastgroup
        valor = match.group()
        columna = match.start() - inicio_linea + 1

        if tipo == 'SALTO_LINEA':
            linea += 1
            inicio_linea = match.end()
            continue
        elif tipo in ('ESPACIOS', 'COMENTARIO_LINEA'):
            continue
        elif tipo == 'COMENTARIO_BLOQUE':
            lineas_extra = valor.count('\n')
            if lineas_extra > 0:
                linea += lineas_extra
                inicio_linea = match.end() - (len(valor) - valor.rfind('\n') - 1)
            continue
        elif tipo == 'MISMATCH':
            raise LexerError(f"Carácter inesperado '{valor}'", linea, columna)

        if tipo == 'ID' and valor in PALABRAS_RESERVADAS:
            tipo = PALABRAS_RESERVADAS[valor]

        yield Token(tipo, valor, linea, columna)

"""
Analizador Sintáctico (Parser) para SensorLang.

Construye un Árbol de Sintaxis Abstracta (AST) a partir del flujo de tokens generado por el Lexer.
Valida la gramática del lenguaje e identifica errores de estructura con número de línea y columna.
"""

from typing import List, Dict, Any, Optional
from .lexer import Token


class ParserError(Exception):
    """Excepción generada ante violaciones sintácticas en el código fuente."""
    def __init__(self, mensaje: str, token: Optional[Token] = None):
        if token:
            super().__init__(f"Error sintáctico [Línea {token.linea}, Columna {token.columna}]: {mensaje} (cerca de '{token.value}')")
        else:
            super().__init__(f"Error sintáctico: {mensaje}")
        self.token = token


class Parser:
    """Implementa un analizador sintáctico descendente recursivo con búsqueda hacia adelante."""

    def __init__(self, tokens: List[Token]):
        self.tokens = list(tokens)
        self.pos = 0

    @property
    def token_actual(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def avanzar(self) -> Optional[Token]:
        actual = self.token_actual
        self.pos += 1
        return actual

    def coincide(self, *tipos: str) -> bool:
        actual = self.token_actual
        return bool(actual and actual.type in tipos)

    def consumir(self, tipo_esperado: str, mensaje_error: str = "") -> Token:
        actual = self.token_actual
        if actual is None:
            raise ParserError(f"Se esperaba '{tipo_esperado}' pero se llegó al final del archivo", None)
        if actual.type != tipo_esperado:
            msg = mensaje_error or f"Se esperaba '{tipo_esperado}' pero se encontró '{actual.value}'"
            raise ParserError(msg, actual)
        return self.avanzar()

    def parsear(self) -> List[Dict[str, Any]]:
        """Recorre todos los tokens y retorna la lista de nodos AST principales."""
        ast = []
        while self.token_actual is not None:
            stmt = self.declaracion_o_instruccion()
            if stmt:
                ast.append(stmt)
        return ast

    def declaracion_o_instruccion(self) -> Optional[Dict[str, Any]]:
        actual = self.token_actual
        if actual is None:
            return None

        # 1. Declaración de pin: 'pin led = 2;' o 'pin sensor = A1;'
        if self.coincide('PIN_DECL'):
            tok_pin = self.consumir('PIN_DECL')
            tok_nombre = self.consumir('ID', "Se esperaba el identificador de la variable del pin")
            self.consumir('ASIGNAR', "Se esperaba '=' en la asignación del pin")

            if self.coincide('ID', 'NUMERO'):
                tok_val = self.avanzar()
            else:
                raise ParserError("Se esperaba un número de pin o alias válido (ej. 2, A0, A1)", self.token_actual)

            if self.coincide('PUNTOCOMA'):
                self.consumir('PUNTOCOMA')

            return {
                'tipo': 'declaracion_pin',
                'var': tok_nombre.value,
                'pin': tok_val.value,
                'linea': tok_pin.linea
            }

        # 2. Identificador: Asignación o función de lectura ('temp = leer_analogo(s);')
        if self.coincide('ID'):
            siguiente = self.tokens[self.pos + 1] if self.pos + 1 < len(self.tokens) else None
            if siguiente and siguiente.type == 'ASIGNAR':
                tok_nombre = self.consumir('ID')
                self.consumir('ASIGNAR')

                # Lectura de sensor: 'var = leer(pin)' o 'var = leer_analogo(pin)' / 'leer_digital(pin)'
                if self.coincide('LEER', 'LEER_ANALOGO', 'LEER_DIGITAL'):
                    tok_leer = self.avanzar()
                    modo = 'digital' if tok_leer.type == 'LEER_DIGITAL' else 'analogo'
                    self.consumir('LPAREN', "Se esperaba '(' tras la función de lectura")

                    if self.coincide('ID', 'NUMERO'):
                        tok_sensor = self.avanzar()
                    else:
                        raise ParserError("Se esperaba el pin o variable del sensor en la función leer()", self.token_actual)

                    self.consumir('RPAREN', "Se esperaba ')' para cerrar la función leer()")
                    if self.coincide('PUNTOCOMA'):
                        self.consumir('PUNTOCOMA')

                    return {
                        'tipo': 'lectura',
                        'var': tok_nombre.value,
                        'sensor': tok_sensor.value,
                        'modo': modo,
                        'linea': tok_nombre.linea
                    }
                else:
                    # Asignación de expresión o valor numérico directo
                    expr_tokens = []
                    while self.token_actual and self.token_actual.type not in ('PUNTOCOMA', 'SALTO_LINEA'):
                        expr_tokens.append(self.avanzar().value)

                    if self.coincide('PUNTOCOMA'):
                        self.consumir('PUNTOCOMA')

                    expr_str = " ".join(expr_tokens) if expr_tokens else "0"
                    return {
                        'tipo': 'asignacion',
                        'var': tok_nombre.value,
                        'valor': expr_str,
                        'linea': tok_nombre.linea
                    }

        # 3. Mostrar por telemetría: 'mostrar(valor);'
        if self.coincide('MOSTRAR'):
            tok_mostrar = self.consumir('MOSTRAR')
            self.consumir('LPAREN', "Se esperaba '(' después de 'mostrar'")

            expr_tokens = []
            while self.token_actual and self.token_actual.type != 'RPAREN':
                expr_tokens.append(self.avanzar().value)

            self.consumir('RPAREN', "Se esperaba ')' tras el argumento de 'mostrar'")
            if self.coincide('PUNTOCOMA'):
                self.consumir('PUNTOCOMA')

            return {
                'tipo': 'mostrar',
                'var': " ".join(expr_tokens),
                'linea': tok_mostrar.linea
            }

        # 4. Mensaje de alerta: 'alerta("mensaje");'
        if self.coincide('ALERTA'):
            tok_alerta = self.consumir('ALERTA')
            self.consumir('LPAREN', "Se esperaba '(' después de 'alerta'")

            if self.coincide('CADENA', 'ID', 'NUMERO'):
                tok_msg = self.avanzar()
            else:
                raise ParserError("Se esperaba un texto entre comillas o una variable en alerta()", self.token_actual)

            self.consumir('RPAREN', "Se esperaba ')' tras el argumento de 'alerta'")
            if self.coincide('PUNTOCOMA'):
                self.consumir('PUNTOCOMA')

            return {
                'tipo': 'alerta',
                'mensaje': tok_msg.value,
                'linea': tok_alerta.linea
            }

        # 5. Control de salida digital: 'encender(pin);' o 'apagar(pin);'
        if self.coincide('ENCENDER', 'APAGAR'):
            tok_cmd = self.avanzar()
            comando = 'encender' if tok_cmd.type == 'ENCENDER' else 'apagar'
            self.consumir('LPAREN', f"Se esperaba '(' después de '{comando}'")

            if self.coincide('ID', 'NUMERO'):
                tok_pin = self.avanzar()
            else:
                raise ParserError(f"Se esperaba el identificador del pin en '{comando}()'", self.token_actual)

            self.consumir('RPAREN', "Se esperaba ')'")
            if self.coincide('PUNTOCOMA'):
                self.consumir('PUNTOCOMA')

            return {
                'tipo': 'accion',
                'comando': comando,
                'pin': tok_pin.value,
                'linea': tok_cmd.linea
            }

        # 6. Retardo temporal: 'esperar(milisegundos);'
        if self.coincide('ESPERAR'):
            tok_esp = self.consumir('ESPERAR')
            self.consumir('LPAREN', "Se esperaba '(' después de 'esperar'")
            tok_tiempo = self.consumir('NUMERO', "Se esperaba la cantidad de milisegundos")
            self.consumir('RPAREN', "Se esperaba ')'")
            if self.coincide('PUNTOCOMA'):
                self.consumir('PUNTOCOMA')

            return {
                'tipo': 'esperar',
                'tiempo': tok_tiempo.value,
                'linea': tok_esp.linea
            }

        # 7. Condicional: 'si (condicion) { ... } sino { ... }'
        if self.coincide('SI'):
            tok_si = self.consumir('SI')
            self.consumir('LPAREN', "Se esperaba '(' después de 'si'")

            cond_tokens = []
            while self.token_actual and self.token_actual.type != 'RPAREN':
                cond_tokens.append(self.avanzar().value)

            self.consumir('RPAREN', "Se esperaba ')' al finalizar la condición del 'si'")
            self.consumir('LLAVE_I', "Se esperaba '{' para iniciar el bloque del 'si'")

            bloque_si = []
            while self.token_actual and not self.coincide('LLAVE_D'):
                inst = self.declaracion_o_instruccion()
                if inst:
                    bloque_si.append(inst)

            self.consumir('LLAVE_D', "Se esperaba '}' para cerrar el bloque del 'si'")

            bloque_sino = []
            if self.coincide('SINO'):
                self.consumir('SINO')
                self.consumir('LLAVE_I', "Se esperaba '{' para iniciar el bloque del 'sino'")
                while self.token_actual and not self.coincide('LLAVE_D'):
                    inst = self.declaracion_o_instruccion()
                    if inst:
                        bloque_sino.append(inst)
                self.consumir('LLAVE_D', "Se esperaba '}' para cerrar el bloque del 'sino'")

            var_cond = cond_tokens[0] if len(cond_tokens) > 0 else "0"
            op = cond_tokens[1] if len(cond_tokens) > 1 else "=="
            limite = " ".join(cond_tokens[2:]) if len(cond_tokens) > 2 else "0"

            return {
                'tipo': 'si',
                'var': var_cond,
                'op': op,
                'limite': limite,
                'condicion': " ".join(cond_tokens),
                'bloque_si': bloque_si,
                'bloque_sino': bloque_sino,
                'linea': tok_si.linea
            }

        tok_desconocido = self.avanzar()
        raise ParserError(f"Instrucción no reconocida o fuera de contexto", tok_desconocido)


def parsear(tokens) -> List[Dict[str, Any]]:
    """Función de entrada principal que construye y evalúa el árbol AST."""
    parser = Parser(list(tokens))
    return parser.parsear()

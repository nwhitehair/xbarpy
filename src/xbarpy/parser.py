from lark import Lark, Transformer

from .xx import XP, get_xx

bracket_grammar = r"""
    start: constituent

    constituent: "[" NAME arguments "]" -> constituent
    arguments: (argument)*
    lexeme: "\"" LEX "\"" -> lexeme

    ?argument: constituent
             | lexeme

    NAME: /[A-Z][a-zA-Z]*/
    LEX: /[a-zA-Z][a-zA-Z]*/
    TRACE: /t/

    %import common.WS
    %ignore WS
"""

class BracketPhraseTransformer(Transformer):
    def start(self, args):
        return args[0]

    def lexeme(self, args):
        return args[0].value
    
    def constituent(self, args):
        obj = get_xx(args[0].value)

        children = args[1].children
        if issubclass(obj, XP):
            children = children[::-1]
        return_obj = obj(*children)
        return return_obj

_bracket_parser = Lark(bracket_grammar, start='constituent', ambiguity='resolve')
_bracket_transformer = BracketPhraseTransformer()

def parse_bracket_string(bracket_string: str) -> XP:
    return _bracket_transformer.transform(_bracket_parser.parse(bracket_string))

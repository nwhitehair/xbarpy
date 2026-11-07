from lark import Lark, Transformer
from .language_parameters import LanguageParameters

from .xx import XBar, XP, get_xx

bracket_grammar = r"""
    start: constituent

    constituent: "[" NAME [properties] arguments "]" -> constituent
    properties: "{" property ("," property)* "}" -> properties
    property: PROPNAME ["=" PROPVAL]
    arguments: (argument)*
    lexeme: "\"" LEX "\"" -> lexeme

    ?argument: constituent
             | lexeme

    NAME: /[A-Z][a-zA-Z]*/
    PROPNAME: /(?:[\+\-])?[A-Za-z][a-z_]*/
    PROPVAL: /[a-zA-Z0-9][a-zA-Z0-9_]*/
    LEX: /[a-zA-Z][a-zA-Z]*/
    TRACE: /t/

    %import common.WS
    %ignore WS
"""

class BracketPhraseTransformer(Transformer):
    def __init__(self, language_parameters: LanguageParameters):
        self._language_parameters = language_parameters

    def start(self, args):
        return args[0]

    def lexeme(self, args):
        return args[0].value
    
    def properties(self, args):
        properties = {}
        for arg in args:
            children = arg.children
            raw_propname = children[0].value
            if raw_propname[0] in ('-', '+'):
                # Special case: properties having names beginning with a sign are boolean features
                # where + indicates True (presence) and - indicates False (absence).
                propname = children[0].value[1:]
                val = children[0].value[0] == '+'
            else:
                propname = children[0].value
                val = children[1].value
            properties[propname] = val
        return properties
    
    def constituent(self, args):
        xx_object = get_xx(args[0].value)
        properties = args[1] or {}
        children = args[2].children
        is_reversed = False

        xp_type = xx_object.get_xp_type()
        xbar_type = xx_object.get_xbar_type()
        x_type = xx_object.get_x_type()
        if issubclass(xx_object, XP):
            if len(children) == 2:
                # The object is an XP with two arguments, so one of the arguments is a specifier.
                # We'll find the specifier by first finding the XBar, then assuming the other arg
                # is the specifier.
                if not isinstance(children[0], xbar_type) ^ isinstance(children[1], xbar_type):
                    type1 = type(children[0])
                    type2 = type(children[1])
                    raise TypeError(f"Exactly one child of {xx_object.__name__} must be {xbar_type.__name__} (got {type1.__name__}, {type2.__name__}).")
                bar_idx = 0 if isinstance(children[0], xbar_type) else 1
                spec_idx = 1 - bar_idx
                specifier = children[spec_idx]
                print(xx_object, spec_idx, bar_idx)
                bar = children[bar_idx]
                args = [bar, specifier]
                specifier_initial = self._language_parameters.specifier_initial
                is_reversed = (specifier_initial and spec_idx == 1) or (not specifier_initial and spec_idx == 0)
            else:
                # The object is an XP with one argument, so the only argument should be an
                # appropriate XBar.
                args = children
        elif issubclass(xx_object, XBar):
            if len(children) == 2:
                # The object is an XBar with two arguments, so one of the arguments is a either a
                # complement or an adjunct. We'll determine which by finding the child that is
                # either the XBar or X (head) corresponding to this XBar type and deducing the
                # role of the other child.
                if isinstance(children[0], x_type) or isinstance(children[1], x_type):
                    has_complement = True
                    has_adjunct = False
                elif isinstance(children[0], xbar_type) or isinstance(children[1], xbar_type):
                    has_complement = False
                    has_adjunct = True
                primary_idx = 0 if isinstance(children[0], (x_type, xbar_type)) else 1
                associated_idx = 1 - primary_idx
                args = [children[primary_idx], children[associated_idx]]
                
                head_initial = self._language_parameters.head_initial
                specifier_initial = self._language_parameters.specifier_initial
                if has_complement:
                    if (associated_idx == 0 and head_initial) or (associated_idx == 1 and not head_initial):
                        is_reversed = True
                elif has_adjunct:
                    if (associated_idx == 1 and specifier_initial) or (associated_idx == 0 and not specifier_initial):
                        is_reversed = True
            else:
                args = children
        else:
            args = children
        
        return_obj = xx_object(*args)

        # Parse any properties for this object
        for propname, propval in properties.items():
            prop_def = return_obj._valid_properties[propname]
            prop_type = prop_def['type']
            prop_parser = prop_def.get('parser', prop_type)
            if prop_def.get('requires_ref', False):
                args = [propval, return_obj]
            else:
                args = [propval,]
            propval = prop_parser(*args)
            # Special check: if the 'reversed' property is explicitly set, make sure it's
            # consistent with what we inferred from checking the argument order.
            if propname == 'reversed':
                if propval != is_reversed:
                    raise RuntimeError("The 'reversed' propety does not match the actual inferred structure.")
            return_obj.set_property(propname, propval)
        if return_obj.get_property('reversed') != is_reversed:
            return_obj.set_property('reversed', is_reversed)
        return return_obj

_bracket_parser = Lark(bracket_grammar, start='constituent', ambiguity='resolve')

def parse_bracket_string(bracket_string: str, language_parameters: LanguageParameters) -> XP:
    _bracket_transformer = BracketPhraseTransformer(language_parameters=language_parameters)
    return _bracket_transformer.transform(_bracket_parser.parse(bracket_string))

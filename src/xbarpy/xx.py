from __future__ import annotations

from typing import Optional, Union

from ._psdef import _phrase_structure_definitions
from .constituent import Constituent


class XX(Constituent):
    """
    The base class for all XP, X-bar, and X objects.
    """
    _linked_objects = {}  # noqa: RUF012
    _constraints = {} # noqa: RUF012
    _overrides = {} # noqa: RUF012

    def __init__(self, primary_node: Optional[Constituent] = None,
                 associated_node: Optional[Constituent] = None,
                 parent: Optional[Constituent] = None, reference: Optional[Constituent] = None,
                 is_reversed: bool = False):
        super().__init__(primary_node=primary_node, associated_node=associated_node, parent=parent,
                         reference=reference, is_reversed=is_reversed)


    @property
    def XP_type(self) -> type:
        return self._linked_objects['XP']

    @property
    def XBar_type(self) -> type:
        return self._linked_objects['XBar']

    @property
    def X_type(self) -> type:
        return self._linked_objects['X']

    def __init_subclass__(cls):
        # Whenever a subclass is created, give it its own constraints dictionary and label.
        # Also, add it to the global set of all constituents; we'll potentially use this to
        # help when parsing bracket strings.
        cls._constraints = {}
        cls._overrides = {}
        cls._linked_objects = {}

    def get_parameter(self, parameter_name: str):
        if self.sentence is None:
            raise RuntimeError("No Sentence has been linked to this Constituent, hence no language " \
            "parameters are available.")
        language_parameter = self.sentence._language_parameters.get_parameter_by_name(
            parameter_name=parameter_name
            )
        return self._overrides.get(parameter_name, language_parameter)


class XP(XX):
    """
    The base class for all XP objects.
    """
    _label = "XP"
    def __init__(self, xbar_node, specifier: Optional[Constituent],
                 parent: Optional[Constituent] = None, reference: Optional[Constituent] = None):
        super().__init__(primary_node=xbar_node, associated_node=specifier, parent=parent,
                         reference=reference)

    @property
    def specifier(self) -> XP:
        return self.associated_node

    @property
    def xbar(self) -> XP:
        return self.primary_node

    def phrase_governs(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        g_restriction = lambda g: isinstance(g, XP)  # pylint: disable=unnecessary-lambda-assignment
        return self.governs(constituent=constituent, include_moved=include_moved,
                            follow_traces=follow_traces, g_restriction=g_restriction)

    def to_string(self) -> str:
        nodes = list(filter(lambda x: not x is None, [self.specifier, self.xbar]))
        if not self.get_parameter("specifier_initial"):
            nodes = nodes[::-1]
        if self.is_reversed:
            nodes = nodes[::-1]
        return " ".join([node.to_string() for node in nodes])

class XBar(XX):
    """
    The base class for all X' objects.
    """
    _label = "X'"
    def __init__(self, primary: Union[XBar, X], complement_or_adjunct: XP = None,
                 parent: Optional[Union[XBar, XP]] = None, reference: Optional[Constituent] = None,
                 is_reversed: bool = False):
        super().__init__(primary_node=primary, associated_node=complement_or_adjunct,
                         parent=parent, reference=reference, is_reversed=is_reversed)
        if not isinstance(primary, (XBar, X)):
            raise TypeError(f"XBar subclasses must be initialized with an XBar or X instance as \
                            the primary node (got {type(primary).__name__}).")
        if not isinstance(primary, (self.XBar_type, self.X_type)):
            raise TypeError(f"{type(self).__name__} must have {self.XBar_type.__name__} or \
                            {self.X_type.__name__} as its primary child node \
                                (got {type(primary).__name__}).")
        if complement_or_adjunct is not None and not isinstance(complement_or_adjunct, XP):
            raise TypeError(f"XBar subclasses must be initialized with an XP instance as the \
                            associated node (got {type(primary).__name__}).")

    @property
    def has_adjunct(self) -> bool:
        return self.associated_node is not None and isinstance(self.primary_node, self.XBar_type)

    @property
    def has_complement(self) -> bool:
        return self.associated_node is not None and isinstance(self.primary_node, self.X_type)

    @property
    def has_head(self) -> bool:
        return self.has_complement or not self.has_adjunct

    @property
    def adjunct(self) -> Optional[Constituent]:
        return self.associated_node if self.has_adjunct else None

    @property
    def complement(self) -> Optional[Constituent]:
        return self.associated_node if self.has_complement else None

    def to_string(self) -> str:
        nodes = list(filter(lambda x: not x is None, [self.primary_node, self.associated_node]))
        if self.has_head and not self.get_parameter("head_initial"):
            nodes = nodes[::-1]
        if self.has_adjunct and not self.get_parameter("adjunct_initial"):
            nodes = nodes[::-1]
        if self.is_reversed:
            nodes = nodes[::-1]
        return " ".join([node.to_string() for node in nodes])

class X(XX):
    """
    The base class for all X (head) objects.
    """
    _label = "X"
    _valid_parameters = set() # noqa: RUF012
    def __init__(self, text: str = "", **parameters):
        super().__init__()
        self._parameters = {}
        for parameter_name, parameter_value in parameters.items():
            if parameter_name not in self._valid_parameters:
                raise AttributeError(f"Parameter '{parameter_name:s}' is not valid for heads of \
                                     type {type(self).__name__}.")
            self._parameters[parameter_name] = parameter_value
        self._text = text

    def head_governs(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        g_restriction = lambda g: isinstance(g, X)  # pylint: disable=unnecessary-lambda-assignment
        return self.governs(constituent=constituent, include_moved=include_moved,
                            follow_traces=follow_traces, g_restriction=g_restriction)

    def to_string(self) -> str:
        return self._text

XX._linked_objects = ({'XP': (XP,), 'XBar': (XBar,), 'X': (X,)})

def _build_phrase_classes(ps_def) -> type:
    head = type(ps_def['head'], (X,), {})
    head._constraints.update(ps_def.get("head_constraints", {}))
    head._overrides.update(ps_def.get("head_overrides", {}))
    head._label = ps_def.get("head_label", ps_def["head"][0])

    p = type(ps_def['p'], (XP,), {})
    p._constraints.update(ps_def.get("p_constraints", {}))
    p._overrides.update(ps_def.get("p_overrides", {}))

    bar = type(ps_def['bar'], (XBar,), {})
    bar._constraints.update(ps_def.get("bar_constraints", {}))
    bar._overrides.update(ps_def.get("bar_overrides", {}))
    bar._label = ps_def.get("bar_label", ps_def['bar'].replace('Bar', '\''))
    
    linked_objects = {'XP': (p,), 'XBar': (bar,), 'X': (head,)}
    head._linked_objects.update(linked_objects)
    p._linked_objects.update(linked_objects)
    bar._linked_objects.update(linked_objects)
    return head, p, bar

for definition in _phrase_structure_definitions:
    objects = _build_phrase_classes(definition)
    for obj in objects:
        globals()[obj.__name__] = obj

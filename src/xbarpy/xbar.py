"""
Defines general X-bar structures and behaviours. Specific phrase types (e.g., NP) are implemented
dynamically at runtime using definitions in _psdef.py.
"""

from __future__ import annotations

from typing import Optional, Sequence, Set, Union

from ._psdef import _phrase_structure_definitions
from .language_parameters import LanguageParameters

all_phrase_structures = set()
all_constituent_classes = set()
constituent_classes_by_label = {}

class Constituent:
    """
    The base class for all elements in the X-Bar schema, including phrases, lexemes, and traces.
    """
    _constraints = {} # noqa: RUF012
    def __init__(self, *children: Sequence[Optional[Constituent]]):
        self._children = set()
        for child in children:
            if child is None:
                continue
            child.set_parent(self)
            self._children.add(child)
            # Note: child nodes are stored in a set, so there is no order here. It is up to
            # specific Constituent subclasses to handle how their arguments are ordered in
            # consideration of the general schema, principles, and language-specific
            # parameters; we only use the set to keep track of which nodes belong to which
            # parent (for, e.g., checking c-command relationships).
        self._trace = None
        self._parent = None

    def __init_subclass__(cls):
        # Whenever a subclass is created, give it its own constraints dictionary and label.
        # Also, add it to the global set of all constituents; we'll potentially use this to
        # help when parsing bracket strings.
        cls._constraints = {}
        cls._label = cls.__name__
        all_constituent_classes.add(cls)

    @classmethod
    def get_label(cls) -> str:
        """Returns a label suitable for bracket-style strings."""
        return cls._label

    @classmethod
    def get_constraint(cls, name: str, default=None):
        """Obtains the specified constraint (if any) for this constituent class."""
        return cls._constraints.get(name, default)

    def set_parent(self, parent: Constituent):
        """Sets the parent constituent of this constituent."""
        self._parent = parent

    @property
    def parent(self) -> Constituent:
        """Returns this constituent's parent constituent."""
        return self._parent

    def get_children(self, include_moved: bool = False, follow_traces: bool = True) -> \
        Set[Constituent]:
        """
        Returns a set of this constituent's immediate children.
        
        Arguments:
            include_moved: bool
                Whether moved constituents are included. I.e., if the phrase has been transformed
                by a movement rule to move a constituent into a child position under this
                constituent, it will be skipped unless `include_moved=True`.
            follow_traces: bool
                Whether traces left behind by moved constituents are included. I.e., if one of the
                children of this constituent is a trace (t), the original (moved) constituent that
                was replaced by the trace will be included if `follow_traces=True`.
        """
        full_set = self._children.copy()
        returned_set = set()
        for child in full_set:
            if child.is_moved and not include_moved:
                continue
            if isinstance(child, Trace):
                if not follow_traces:
                    continue
                child = child.moved_constituent
            returned_set.add(child)
        return returned_set

    def get_descendants(self, include_moved: bool = False, follow_traces: bool = True) -> \
        Set[Constituent]:
        """
        Recursively obtains and then returns a set of this constituent's descendants (children,
        grandchildren, great-grandchildren ...).
        
        Arguments:
            include_moved: bool
                Whether moved constituents are included. I.e., if the phrase has been transformed
                by a movement rule to move a constituent into a descendant position under this
                constituent, it will be skipped unless `include_moved=True`.
            follow_traces: bool
                Whether traces left behind by moved constituents are included. I.e., if one of the
                descendants of this constituent is a trace (t), the original (moved) constituent
                that was replaced by the trace will be included if `follow_traces=True`.
        """
        descendants = set()
        for child in self.get_children():
            if child.is_moved and not include_moved:
                continue
            if isinstance(child, Trace):
                if not follow_traces:
                    continue
                child = child.moved_constituent
            descendants.add(child)
            for descendant in child.get_descendants(
                include_moved=include_moved,
                follow_traces=follow_traces
                ):
                descendants.add(descendant)
        return descendants

    def has_descendant(self, constituent: Constituent, include_moved: bool = False,
                       follow_traces: bool = True):
        """
        Returns True if this constituent has the specified constituent as a descendant.
        
        Arguments:
            include_moved: bool
                Whether moved constituents are considered descendants when they have been moved to
                a descendant position.
            follow_traces: bool
                Whether moved constituents are considered descendants when they have been moved
                from a descendant position (leaving behind a trace).
        """
        return constituent in self.get_descendants(include_moved=include_moved,
                                                   follow_traces=follow_traces)

    def is_descendant_of(self, constituent: Constituent, use_source_position: bool = True):
        """
        Returns True if this constituent is a descendant of the specified constituent.
        
        Arguments:
            include_moved: bool
                Whether moved constituents are considered descendants when they have been moved to
                a descendant position.
            follow_traces: bool
                Whether moved constituents are considered descendants when they have been moved
                from a descendant position (leaving behind a trace).
        """
        if use_source_position and self.is_moved:
            target = self._trace
        else:
            target = self
        return constituent.has_descendant(target)

    def is_moved(self):
        """
        Returns True if this constituent was moved (leaving behind a trace).
        """
        return self._trace is not None

    def create_trace(self) -> Trace:
        """
        Creates and returns a trace, then causes this constituent to return True when `is_true()`
        is called. This should be invoked when building a structure that represents the result of
        evaluating a movement rule.
        """
        if self._trace is not None:
            raise RuntimeError("Attempted to create a trace for a Constituent with a pre-existing" \
            "trace.")
        trace = Trace(moved_constituent=self)
        return trace

    def c_commands(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        """
        Returns True if this constituent c-commands the specified constituent.
        
        Arguments:
            include_moved: bool
                Whether moved constituents are considered descendants when they have been moved to
                a descendant position.
            follow_traces: bool
                Whether moved constituents are considered descendants when they have been moved
                from a descendant position (leaving behind a trace).
        """
        siblings = self.get_siblings(include_moved=include_moved, follow_traces=follow_traces)
        if constituent in siblings:
            return True
        for sibling in siblings:
            descendants = sibling.get_descendants(
                include_moved=include_moved,
                follow_traces=follow_traces
                )
            if constituent == sibling or constituent in descendants:
                return True
        return False

    def get_siblings(self, include_moved: bool = False, follow_traces: bool = True) -> \
        Set[Constituent]:
        """
        Returns the set of constituents that share a parent with this constituent.
        
        Arguments:
            include_moved: bool
                Whether moved constituents are considered descendants when they have been moved to
                a descendant position.
            follow_traces: bool
                Whether moved constituents are considered descendants when they have been moved
                from a descendant position (leaving behind a trace).
        """
        if self.parent is None:
            return set()
        siblings = self.parent.get_children(
            include_moved=include_moved,
            follow_traces=follow_traces
            )
        siblings.remove(self)
        return siblings

class Trace(Constituent):
    """
    A special object that serves as a placeholder for a Constituent that has been moved according
    to some rule.
    The Trace occupies the original position of the moved Constituent.
    """
    def __init__(self, moved_constituent: Constituent):
        super().__init__()
        self._moved_constituent = moved_constituent

    @property
    def moved_constituent(self) -> Constituent:
        """Returns the constituent that occupied the position currently occupied by this trace."""
        return self._moved_constituent

    def to_string(self, parameters: LanguageParameters, natural: bool = True) -> str: # pylint: disable=unused-argument
        """
        Converts the Trace to a string.

        Arguments:
            parameters: LanguageParameters
                Ignored for this particular class, but should generally be passed
            natural: bool
                Whether to produce a string of natural-looking text (as opposed to bracketed text).
                When True, a Trace will return an empty string, since natural text does not contain
                traces.
        """
        return "" if natural else "t"

class Lexeme(Constituent):
    """
    Base class representing a terminal node, usually with some lexical representation.
    (Exceptions are traces and certain derivational morphemes.)
    """

    def __init__(self, text: str):
        super().__init__()
        self._text = text

    @property
    def text(self) -> str:
        """The textual representation of this lexeme."""
        return self._text

    def to_string(self, parameters: LanguageParameters, natural: bool = True) -> str: # pylint: disable=unused-argument
        """
        Converts the Lexeme to a string.

        Arguments:
            parameters: LanguageParameters
                Language-specific parameters that influence how the linear text is realized (unused
                here).
            natural: bool
                Whether to produce a string of natural-looking text (as opposed to bracketed text).
        """
        return self.text if natural else f"[{self.get_label()} {self.text}]"

class XP(Constituent):
    """
    The base class for all phrase objects.
    """
    def __init__(self, x_bar: XBar, specifier: XP = None):
        super().__init__(x_bar, specifier)
        self._x_bar = x_bar
        self._specifier = specifier

    def __init_subclass__(cls):
        all_phrase_structures.add(cls)
        return super().__init_subclass__()

    def to_string(self, parameters: LanguageParameters, natural: bool = True) -> str:
        """
        Converts the XP structure (including all descendants) to a string.

        Arguments:
            parameters: LanguageParameters
                Language-specific parameters that influence how the linear text is realized.
            natural: bool
                Whether to produce a string of natural-looking text (as opposed to bracketed text).
        """
        specifier_first = parameters.specifier_initial
        strs = [self._x_bar.to_string(parameters=parameters, natural=natural),]
        if self._specifier is not None:
            strs.append(self._specifier.to_string(parameters=parameters, natural=natural))
            if specifier_first:
                strs = strs[::-1]
        raw_str = " ".join(strs)
        return raw_str if natural else f"[{self.get_label()} {raw_str}]"

class XBar(Constituent):
    """
    The base class for all X' objects.
    """
    def __init__(self, head: Union[XBar, Lexeme], complement: XP = None, left_adjunct: XP = None,
                 right_adjunct: XP = None):
        super().__init__(head, complement, left_adjunct, right_adjunct)
        if not isinstance(head, (XBar, Lexeme)):
            raise TypeError(f"XBar head must be either a Lexeme or an XBar (got {type})")
        num_arguments = 0
        if complement is not None:
            num_arguments += 1
        if left_adjunct is not None:
            num_arguments += 1
        if right_adjunct is not None:
            num_arguments += 1
        if num_arguments > 1:
            raise RuntimeError("XBar can have at most one argument (complement, left adjunct, or" \
            "right adjunct).")
        has_adjunct = left_adjunct is not None or right_adjunct is not None
        if isinstance(head, Lexeme) and has_adjunct:
            raise RuntimeError("An XBar with a terminal head must not have an adjunct.")
        self._head = head
        self._left_adjunct = left_adjunct
        self._right_adjunct = right_adjunct
        self._complement = complement

    def to_string(self, parameters: LanguageParameters, natural: bool = True) -> str:
        """
        Converts the XBar structure (including all descendants) to a string.

        Arguments:
            parameters: LanguageParameters
                Language-specific parameters that influence how the linear text is realized.
            natural: bool
                Whether to produce a string of natural-looking text (as opposed to bracketed text).
        """
        adjunct_first = self._left_adjunct is not None
        complement_first = not parameters.head_initial
        strs = [self._head.to_string(parameters=parameters, natural=natural),]

        adjunct = self._left_adjunct or self._right_adjunct
        if adjunct is not None:
            strs.append(adjunct.to_string(parameters=parameters, natural=natural))
            if adjunct_first:
                strs = strs[::-1]
        if self._complement is not None:
            strs.append(self._complement.to_string(parameters=parameters, natural=natural))
            if complement_first:
                strs = strs[::-1]
        raw_str = " ".join(strs)
        return raw_str if natural else f"[{self.get_label()} {raw_str}]"

def _build_phrase_classes(ps_def) -> type:
    head = type(ps_def['head'], (Lexeme,), {})
    head._constraints.update(ps_def.get("head_constraints", {}))
    head._label = ps_def.get("head_label", ps_def["head"][0])

    p = type(ps_def['p'], (XP,), {})
    p._constraints.update(ps_def.get("p_constraints", {}))

    bar = type(ps_def['bar'], (XBar,), {})
    bar._constraints.update(ps_def.get("bar_constraints", {}))
    bar._label = ps_def.get("bar_label", ps_def['bar'].replace('Bar', '\''))
    return head, p, bar

for definition in _phrase_structure_definitions:
    objects = _build_phrase_classes(definition)
    for obj in objects:
        globals()[obj.__name__] = obj

for _cls in all_constituent_classes:
    constituent_classes_by_label[_cls.get_label()] = _cls

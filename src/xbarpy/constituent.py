from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional, Set, Tuple, cast

from .node import BranchingNode

if TYPE_CHECKING:
    from .sentence import Sentence

class Constituent(BranchingNode):
    def __init__(self, primary_node: Optional[Constituent] = None,
                 associated_node: Optional[Constituent] = None,
                 parent: Optional[Constituent] = None,
                 reference: Optional[Constituent] = None,
                 is_reversed: bool = False):
        super().__init__(parent=parent)
        self.set_child(primary_node, index=0)
        self.set_child(associated_node, index=1)
        self.set_reversed(is_reversed)
        self._trace = None
        self._reference = reference
        self._sentence = None

    @property
    def primary_node(self) -> Optional[Constituent]:
        return self.children[0]

    @property
    def associated_node(self) -> Optional[Constituent]:
        return self.children[1]

    def link_to_sentence(self, sentence: Sentence):
        if self._sentence is not None and self._sentence != sentence:
            raise RuntimeError("Constituent has already been linked to a Sentence.")
        self._sentence = sentence

    @property
    def sentence(self) -> Optional[Sentence]:
        return self._sentence

    def set_reversed(self, is_reversed: bool = False):
        self._is_reversed = is_reversed

    def move(self, new_parent: Constituent):
        trace = Trace(parent=self.parent, reference=self)
        self._set_parent(parent=new_parent)
        self._trace = trace
        return trace

    @property
    def is_moved(self) -> bool:
        return self._trace is not None

    @property
    def is_reversed(self) -> bool:
        return self._is_reversed

    @property
    def children(self) -> Tuple[Constituent, ...]:
        return cast(Tuple['Constituent', ...], super().children)

    @property
    def reference(self) -> Optional[Constituent]:
        return self._reference

    def get_children(self, follow_traces: bool = True, include_moved: bool = False) \
        -> Set[Constituent]:
        children = set()
        for child in self.children:
            if child is None:
                continue
            is_trace = isinstance(child, Trace)
            if is_trace and follow_traces:
                child = child.reference
            elif not is_trace and child.is_moved and not include_moved:
                continue
            children.add(child)
        return children

    def get_siblings(self, follow_traces: bool = True, include_moved: bool = False) \
        -> Set[Constituent]:
        siblings = set()
        if self.is_root:
            return siblings
        parent = cast(Constituent, self.parent)
        siblings |= parent.get_children(follow_traces=follow_traces, include_moved=include_moved)
        siblings.remove(self)
        return siblings

    def get_all_relatives(self) -> Set[Constituent]:
        '''Returns the set of all Constituents sharing a root with this Constituent (including the \
            root but excluding the Constituent itself).'''
        start_node = self
        while not start_node.is_root:
            start_node = start_node.parent
        relatives = set()
        relatives.add(start_node)
        relatives |= start_node.get_descendants()
        return relatives

    def get_descendants(self, follow_traces: bool = True, include_moved: bool = False) \
        -> Set[Constituent]:
        descendants = set()
        children: Set[Constituent] = self.get_children(follow_traces=follow_traces,
                                                       include_moved=include_moved)
        for child in children:
            descendants.add(child)
            descendants |= child.get_descendants(follow_traces=follow_traces,
                                                 include_moved=include_moved)
        return descendants

    def c_commands(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True, include_asymmetric: bool = True,
                   include_symmetric: bool = True) -> bool:
        siblings = self.get_siblings(include_moved=include_moved, follow_traces=follow_traces)
        if constituent in siblings:
            return include_symmetric
        if include_asymmetric:
            for sibling in siblings:
                if constituent in sibling.get_descendants(
                    include_moved=include_moved,
                    follow_traces=follow_traces
                    ):
                    return True
        return False

    def get_c_commanded(self, include_moved: bool = False,
                   follow_traces: bool = True, include_asymmetric: bool = True,
                   include_symmetric: bool = True) -> Set[Constituent]:
        '''Returns all Constituents that are c-commanded by this Constituent.'''
        results = set()
        siblings = self.get_siblings(follow_traces=follow_traces, include_moved=include_moved)
        for sibling in siblings:
            if include_symmetric:
                results.add(sibling)
            if include_asymmetric:
                results |= sibling.get_descendants(follow_traces=follow_traces,
                                                   include_moved=include_moved)
        return results

    def governs(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True, g_restriction: Optional[Callable] = None) \
                    -> bool:
        if not self.c_commands(constituent=constituent, include_moved=include_moved,
                               follow_traces=follow_traces):
            return False
        if g_restriction is None:
            g_restriction = lambda g: True # pylint: disable=unnecessary-lambda-assignment
        g_restriction = cast(callable, g_restriction)
        for g in self.get_c_commanded(include_moved=include_moved, follow_traces=follow_traces):
            if not g_restriction(g):
                continue
            if g.c_commands(constituent=constituent, include_moved=include_moved,
                            follow_traces=follow_traces, include_symmetric=False):
                return False
        return True

    def phrase_governs(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        # This will be defined by the XP (phrase) subclass; all other objects return False.
        return False

    def head_governs(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        # This will be defined by the X (head) subclass; all other objects return False.
        return False

    def immediately_dominates(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        return constituent in self.get_children(include_moved=include_moved,
                                                follow_traces=follow_traces)

    def dominates(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        return constituent in self.get_descendants(follow_traces=follow_traces,
                                                   include_moved=include_moved)

    def coindexed_with(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        '''
        Returns True when both Constituents refer (either directly or indirectly) to the same
        entity.
        '''
        primary = self
        if isinstance(primary, Trace) and follow_traces:
            primary = self.reference
        if isinstance(constituent, Trace) and follow_traces:
            constituent = constituent.reference
        reference_a = primary.reference or primary
        reference_b = constituent.reference or constituent
        conditions = [
            primary in (constituent, reference_b),
            constituent in (primary, reference_a),
            reference_a is not None and reference_a is reference_b
        ]
        return (not self is constituent) and any(conditions)

    def binds(self, constituent: Constituent, include_moved: bool = False,
                   follow_traces: bool = True) -> bool:
        is_coindexed = self.coindexed_with(constituent=constituent, follow_traces=follow_traces,
                                           include_moved=include_moved)
        c_commands = self.c_commands(constituent=constituent, include_moved=include_moved,
                                     follow_traces=follow_traces)
        return is_coindexed and c_commands

    def get_bound(self, include_moved: bool = False,
                   follow_traces: bool = True) -> Set[Constituent]:
        bound_constituents = set()
        for candidate in self.get_c_commanded(include_moved=include_moved,
                                              follow_traces=follow_traces):
            if self.coindexed_with(constituent=candidate, follow_traces=follow_traces,
                                   include_moved=include_moved):
                bound_constituents.add(candidate)
        return bound_constituents

    def to_string(self) -> str:
        raise NotImplementedError

    def __repr__(self) -> str:
        return self.to_string()

class Trace(Constituent):
    def __init__(self, parent: Constituent, reference: Constituent):
        super().__init__(parent=parent, reference=reference)

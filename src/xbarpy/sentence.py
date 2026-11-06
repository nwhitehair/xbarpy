from __future__ import annotations

from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from .constituent import Constituent
    from .language_parameters import LanguageParameters
    from .xx import XP

class Sentence:
    def __init__(self, root: XP, language_parameters: LanguageParameters):
        self._root = root
        self._language_parameters = language_parameters

    def get_all_constituents(self) -> Set[Constituent]:
        return_set = set()
        return_set.add(self._root)
        return_set |= self._root.get_descendants()
        return return_set

    def link(self):
        for constituent in self.get_all_constituents():
            constituent.link_to_sentence(self)

    def to_string(self) -> str:
        return self._root.to_string()

from dataclasses import dataclass


@dataclass
class LanguageParameters:
    head_initial: bool = True
    head_movement: bool = True
    specifier_initial: bool = True
from dataclasses import dataclass


@dataclass
class LanguageParameters:
    head_initial: bool = True # Whether the head precedes the complement
    specifier_initial: bool = True # Whether the specifier precedes X'
    adjunct_initial: bool = False # Whether the adjunct precedes X'
    head_movement: bool = True

    def get_parameter_by_name(self, parameter_name: str) -> bool:
        try:
            return self.__dict__[parameter_name]
        except KeyError:
            raise AttributeError("Invalid parameter name:", parameter_name)

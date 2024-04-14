import os
import re


class MakefileParser:
    def __init__(self, makefile_paths):
        self.makefile_paths = makefile_paths
        self.macros = {}
        self.load_macros()


    def load_macros(self):
        """ Load macro definitions from Makefiles into a dictionary. """
        for path in self.makefile_paths:
            if not os.path.isfile(path):
                print(f"Warning: '{path}' is not a valid file and will be ignored.")
                continue
            with open(path, 'r') as file:
                for line in file:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        self.macros[key.strip()] = value.strip()
                        try:
                            self.check_for_mixed_parentheses(value)
                        except ValueError as e:
                            raise ValueError(f"Error in macro {key}: {e}")


    def check_for_mixed_parentheses(self, value):
        """ Check for mixed parentheses in macro definitions and raise an exception if found. """
        mixed_parentheses_patterns = [
            re.compile(r'\$\{[^{}]*\$\([^)]*\)[^{}]*\}'),  # ${...$(...)...}
            re.compile(r'\$\([^()]*\$\{[^}]*\}[^()]*\)')   # $(...${...}...)
        ]

        for pattern in mixed_parentheses_patterns:
            if pattern.search(value):
                raise ValueError(
                    "Mixed parentheses in macro definitions are not allowed. "
                    "Please use consistent macro delimiters."
                )


    def resolve_macro(self, value):
        """ Recursively resolve macros using macro definitions and environment variables. """
        # capture the deepest nested macro first
        pattern = re.compile(r'\$\(([^()]+)\)|\$\{([^{}]+)\}')

        def replace_macro(match):
            macro_name = match.group(1) or match.group(2)
            if macro_name in self.macros:
                return self.resolve_macro(self.macros[macro_name])
            else:
                replacement = os.getenv(macro_name)
                if replacement is None:
                    raise ValueError(f"Unresolved macro or environment variable: '{macro_name}'")
                return replacement

        # continuously resolve inner macros until no more replacements are found
        while True:
            new_value = pattern.sub(replace_macro, value)
            if new_value == value:  # No more replacements needed
                break
            value = new_value

        return value


    def expand_macro(self, target_macro):
        """ Expand a specific macro from the Makefile using macro definitions and environment variables. """
        if target_macro in self.macros:
            return self.resolve_macro(self.macros[target_macro])
        else:
            raise ValueError(f"Macro {target_macro} not found in self.makefile_paths")


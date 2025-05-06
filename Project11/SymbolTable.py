class SymbolTable:
    """
    Manages a symbol table with two scopes:
      - class scope: for 'static' and 'field' declarations
      - subroutine scope: for 'arg' and 'var' declarations
    Provides indices, types, and kinds for named identifiers.
    """

    def __init__(self):
        # class-level symbols
        self.class_scope = {}
        # subroutine-level symbols
        self.subroutine_scope = {}
        # running counts for each kind
        self.counts = {
            'static': 0,
            'field': 0,
            'arg': 0,
            'var': 0
        }

    def startSubroutine(self):
        """Resets the subroutine scope (for each new method/function/constructor)."""
        self.subroutine_scope.clear()
        self.counts['arg'] = 0
        self.counts['var'] = 0

    def define(self, name, type_, kind):
        """
        Defines a new identifier of the given name, type, and kind,
        and assigns it a running index.
        kind ∈ {'static', 'field', 'arg', 'var'}.
        """
        if kind in ('static', 'field'):
            idx = self.counts[kind]
            self.class_scope[name] = {'type': type_, 'kind': kind, 'index': idx}
            self.counts[kind] += 1
        elif kind in ('arg', 'var'):
            idx = self.counts[kind]
            self.subroutine_scope[name] = {'type': type_, 'kind': kind, 'index': idx}
            self.counts[kind] += 1
        else:
            raise ValueError(f"Invalid kind: {kind}")

    def varCount(self, kind):
        """Returns the number of variables of the given kind already defined."""
        return self.counts.get(kind, 0)

    def kindOf(self, name):
        """Returns the kind of the named identifier, or None if unknown."""
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]['kind']
        if name in self.class_scope:
            return self.class_scope[name]['kind']
        return None

    def typeOf(self, name):
        """Returns the type of the named identifier, or None if unknown."""
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]['type']
        if name in self.class_scope:
            return self.class_scope[name]['type']
        return None

    def indexOf(self, name):
        """Returns the index assigned to the named identifier, or None if unknown."""
        if name in self.subroutine_scope:
            return self.subroutine_scope[name]['index']
        if name in self.class_scope:
            return self.class_scope[name]['index']
        return None

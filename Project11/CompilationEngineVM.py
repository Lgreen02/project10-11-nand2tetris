class CompilationEngineVM:
    def __init__(self, tokenizer, writer, sym):
        self.tok        = tokenizer
        self.vm         = writer
        self.sym        = sym
        self.className  = ''
        self.labelCount = 0

    def compileClass(self):
        # 'class' className '{' classVarDec* subroutineDec* '}'
        self._eat('KEYWORD', 'class')
        self.className = self._eat('IDENTIFIER')
        self._eat('SYMBOL', '{')

        while self._check('KEYWORD', ('static', 'field')):
            self.compileClassVarDec()

        while self._check('KEYWORD', ('constructor', 'function', 'method')):
            self.compileSubroutine()

        self._eat('SYMBOL', '}')

    def compileClassVarDec(self):
        # ('static' | 'field') type varName (',' varName)* ';'
        kind = self._eat('KEYWORD')                          # static|field
        typ  = self._eat_any(('KEYWORD','IDENTIFIER'))       # int|char|boolean|ClassName
        name = self._eat('IDENTIFIER')
        self.sym.define(name, typ, kind)

        while self._check('SYMBOL', ','):
            self._eat('SYMBOL', ',')
            name = self._eat('IDENTIFIER')
            self.sym.define(name, typ, kind)

        self._eat('SYMBOL', ';')

    def compileSubroutine(self):
        # ('constructor' | 'function' | 'method') ('void' | type) subName
        # '(' parameterList ')' subroutineBody
        funcType = self._eat('KEYWORD')                      # constructor, function, or method
        self._eat_any(('KEYWORD','IDENTIFIER'))              # return type
        subName = self._eat('IDENTIFIER')
        fullName = f"{self.className}.{subName}"

        # reset subroutine scope
        self.sym.startSubroutine()

        # parameter list
        self._eat('SYMBOL', '(')
        self.compileParameterList()
        self._eat('SYMBOL', ')')

        # subroutine body
        self._eat('SYMBOL', '{')

        # compile all var declarations first
        while self._check('KEYWORD', 'var'):
            self.compileVarDec()

        # write function declaration with exact local count
        nLocals = self.sym.varCount('var')
        self.vm.writeFunction(fullName, nLocals)

        # constructor: allocate object and set this
        if funcType == 'constructor':
            nFields = self.sym.varCount('field')
            self.vm.writePush('constant', nFields)
            self.vm.writeCall('Memory.alloc', 1)
            self.vm.writePop('pointer', 0)

        # method: bind 'this' to argument 0
        elif funcType == 'method':
            self.vm.writePush('argument', 0)
            self.vm.writePop('pointer', 0)

        # compile statements
        self.compileStatements()
        self._eat('SYMBOL', '}')

    def compileParameterList(self):
        # ((type varName) (',' type varName)*)?
        if not self._check('SYMBOL', ')'):
            typ  = self._eat_any(('KEYWORD','IDENTIFIER'))
            name = self._eat('IDENTIFIER')
            self.sym.define(name, typ, 'arg')
            while self._check('SYMBOL', ','):
                self._eat('SYMBOL', ',')
                typ  = self._eat_any(('KEYWORD','IDENTIFIER'))
                name = self._eat('IDENTIFIER')
                self.sym.define(name, typ, 'arg')

    def compileVarDec(self):
        # 'var' type varName (',' varName)* ';'
        self._eat('KEYWORD', 'var')
        typ  = self._eat_any(('KEYWORD','IDENTIFIER'))
        name = self._eat('IDENTIFIER')
        self.sym.define(name, typ, 'var')
        while self._check('SYMBOL', ','):
            self._eat('SYMBOL', ',')
            name = self._eat('IDENTIFIER')
            self.sym.define(name, typ, 'var')
        self._eat('SYMBOL', ';')

    def compileStatements(self):
        # (let | if | while | do | return)*
        while self._check('KEYWORD', ('let','if','while','do','return')):
            kw = self.tok.peek()[1]
            getattr(self, f'compile{kw.capitalize()}')()

    def compileLet(self):
        # 'let' varName ('[' expression ']')? '=' expression ';'
        self._eat('KEYWORD', 'let')
        var = self._eat('IDENTIFIER')
        isArr = False

        if self._check('SYMBOL', '['):
            isArr = True
            self._eat('SYMBOL', '[')
            self.compileExpression()
            self._eat('SYMBOL', ']')
            seg = self._kindToSeg(self.sym.kindOf(var))
            idx = self.sym.indexOf(var)
            self.vm.writePush(seg, idx)
            self.vm.writeArithmetic('add')

        self._eat('SYMBOL', '=')
        self.compileExpression()
        self._eat('SYMBOL', ';')

        if isArr:
            self.vm.writePop('temp', 0)
            self.vm.writePop('pointer', 1)
            self.vm.writePush('temp', 0)
            self.vm.writePop('that', 0)
        else:
            seg = self._kindToSeg(self.sym.kindOf(var))
            idx = self.sym.indexOf(var)
            self.vm.writePop(seg, idx)

    def compileIf(self):
        # 'if' '(' expression ')' '{' statements '}' ('else' '{' statements '}')?
        self._eat('KEYWORD', 'if')
        self._eat('SYMBOL', '(')
        self.compileExpression()
        self._eat('SYMBOL', ')')

        labelTrue = f'IF_TRUE{self.labelCount}'
        labelEnd  = f'IF_END{self.labelCount}'
        self.labelCount += 1

        self.vm.writeIf(labelTrue)
        self.vm.writeGoto(labelEnd)
        self.vm.writeLabel(labelTrue)

        self._eat('SYMBOL', '{')
        self.compileStatements()
        self._eat('SYMBOL', '}')

        if self._check('KEYWORD', 'else'):
            self._eat('KEYWORD', 'else')
            self._eat('SYMBOL', '{')
            self.compileStatements()
            self._eat('SYMBOL', '}')

        self.vm.writeLabel(labelEnd)

    def compileWhile(self):
        # 'while' '(' expression ')' '{' statements '}'
        self._eat('KEYWORD', 'while')
        self._eat('SYMBOL', '(')

        startLabel = f'WHILE_EXP{self.labelCount}'
        endLabel   = f'WHILE_END{self.labelCount}'
        self.labelCount += 1

        self.vm.writeLabel(startLabel)
        self.compileExpression()
        self._eat('SYMBOL', ')')

        self.vm.writeArithmetic('not')
        self.vm.writeIf(endLabel)

        self._eat('SYMBOL', '{')
        self.compileStatements()
        self._eat('SYMBOL', '}')

        self.vm.writeGoto(startLabel)
        self.vm.writeLabel(endLabel)

    def compileDo(self):
        # 'do' subroutineCall ';'
        self._eat('KEYWORD', 'do')
        self.compileSubroutineCall()
        self.vm.writePop('temp', 0)
        self._eat('SYMBOL', ';')

    def compileReturn(self):
        # 'return' expression? ';'
        self._eat('KEYWORD', 'return')
        if not self._check('SYMBOL', ';'):
            self.compileExpression()
        else:
            self.vm.writePush('constant', 0)
        self.vm.writeReturn()
        self._eat('SYMBOL', ';')

    def compileExpression(self):
        # term (op term)*
        self.compileTerm()
        ops = {
            '+': 'add', '-': 'sub',
            '*': 'call Math.multiply 2', '/': 'call Math.divide 2',
            '&': 'and', '|': 'or',
            '<': 'lt', '>': 'gt', '=': 'eq'
        }
        while self._check('SYMBOL', tuple(ops.keys())):
            op = self._eat('SYMBOL')
            self.compileTerm()
            cmd = ops[op]
            if cmd.startswith('call'):
                _, name, n = cmd.split()
                self.vm.writeCall(name, int(n))
            else:
                self.vm.writeArithmetic(cmd)

    def compileTerm(self):
        # INT_CONST | STRING_CONST | keywordConstant | varName | varName '[' expr ']' |
        # subroutineCall | '(' expr ')' | unaryOp term
        k, v = self.tok.peek()

        if k == 'INT_CONST':
            val = int(self._eat('INT_CONST'))
            self.vm.writePush('constant', val)

        elif k == 'STRING_CONST':
            s = self._eat('STRING_CONST')[1:-1]
            self.vm.writePush('constant', len(s))
            self.vm.writeCall('String.new', 1)
            for c in s:
                self.vm.writePush('constant', ord(c))
                self.vm.writeCall('String.appendChar', 2)

        elif k == 'KEYWORD' and v in ('true', 'false', 'null', 'this'):
            word = self._eat('KEYWORD')
            if word == 'true':
                self.vm.writePush('constant', 0)
                self.vm.writeArithmetic('not')
            elif word == 'this':
                self.vm.writePush('pointer', 0)
            else:
                self.vm.writePush('constant', 0)

        elif k == 'IDENTIFIER':
            nxt = (self.tok.tokens[self.tok.current+1]
                   if self.tok.current+1 < len(self.tok.tokens) else (None, None))
            if nxt == ('SYMBOL', '['):
                var = self._eat('IDENTIFIER')
                self._eat('SYMBOL', '[')
                self.compileExpression()
                self._eat('SYMBOL', ']')
                seg = self._kindToSeg(self.sym.kindOf(var))
                idx = self.sym.indexOf(var)
                self.vm.writePush(seg, idx)
                self.vm.writeArithmetic('add')
                self.vm.writePop('pointer', 1)
                self.vm.writePush('that', 0)

            elif nxt[1] in ('.', '('):
                self.compileSubroutineCall()

            else:
                var = self._eat('IDENTIFIER')
                seg = self._kindToSeg(self.sym.kindOf(var))
                idx = self.sym.indexOf(var)
                self.vm.writePush(seg, idx)

        elif v == '(':
            self._eat('SYMBOL', '(')
            self.compileExpression()
            self._eat('SYMBOL', ')')

        elif v in ('-', '~'):
            op = self._eat('SYMBOL')
            self.compileTerm()
            self.vm.writeArithmetic('neg' if op == '-' else 'not')

    def compileExpressionList(self):
        # (expression (',' expression)*)?
        n = 0
        if not self._check('SYMBOL', ')'):
            self.compileExpression()
            n += 1
            while self._check('SYMBOL', ','):
                self._eat('SYMBOL', ',')
                self.compileExpression()
                n += 1
        return n

    def compileSubroutineCall(self):
        # subroutineName '(' expressionList ')' |
        # (className | varName) '.' subName '(' expressionList ')'
        name = self._eat('IDENTIFIER')
        extra = 0

        if self._check('SYMBOL', '.'):
            self._eat('SYMBOL', '.')
            cls    = name
            subName= self._eat('IDENTIFIER')
            kind   = self.sym.kindOf(cls)
            if kind is not None:
                # method call on an object
                seg = self._kindToSeg(kind)
                idx = self.sym.indexOf(cls)
                self.vm.writePush(seg, idx)
                name = f"{self.sym.typeOf(cls)}.{subName}"
                extra = 1
            else:
                # static call on a class
                name = f"{cls}.{subName}"
                extra = 0
        else:
            # implicit method call on this
            self.vm.writePush('pointer', 0)
            name = f"{self.className}.{name}"
            extra = 1

        self._eat('SYMBOL', '(')
        nArgs = self.compileExpressionList() + extra
        self._eat('SYMBOL', ')')
        self.vm.writeCall(name, nArgs)

    # ──────────────────── Helpers ────────────────────

    def _kindToSeg(self, kind):
        return {
            'static':  'static',
            'field':   'this',
            'arg':     'argument',
            'var':     'local'
        }[kind]

    def _check(self, kind, values):
        k, v = self.tok.peek()
        return (
            k == kind and
            (
                (v in values) if isinstance(values, tuple)
                else (values is None or v == values)
            )
        )

    def _eat(self, kind, value=None):
        k, v = self.tok.peek()
        assert k == kind and (value is None or v == value)
        self.tok.advance()
        return v

    def _eat_any(self, kinds):
        k, v = self.tok.peek()
        assert k in kinds
        self.tok.advance()
        return v

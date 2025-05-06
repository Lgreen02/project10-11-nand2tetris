import re

class JackTokenizer:
    token_specification = [
        ('COMMENT',      r'//.*|/\*[\s\S]*?\*/'),  # Skip both single-line and multi-line comments
        ('STRING_CONST', r'"[^"\n]*"'),
        ('INT_CONST',    r'\d+'),
        ('IDENTIFIER',   r'[A-Za-z_][A-Za-z0-9_]*'),
        ('SYMBOL',       r'[{}()\[\].,;\+\-\*/&|<>=~]'),
        ('SKIP',         r'\s+'),
        ('MISMATCH',     r'.'),
    ]

    keywords = {
        'class','constructor','function','method','field','static','var',
        'int','char','boolean','void','true','false','null','this',
        'let','do','if','else','while','return'
    }

    def __init__(self, input_text):
        tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.token_specification)
        self.tokens = []
        for mo in re.finditer(tok_regex, input_text):
            kind = mo.lastgroup
            value = mo.group()
            if kind in ('SKIP', 'COMMENT'):
                continue
            if kind == 'IDENTIFIER' and value in self.keywords:
                kind = 'KEYWORD'
            elif kind == 'MISMATCH':
                raise RuntimeError(f'Unexpected token: {value}')
            self.tokens.append((kind, value))
        self.current = 0

    def has_more_tokens(self):
        return self.current < len(self.tokens)

    def advance(self):
        if self.has_more_tokens():
            self.current += 1

    def peek(self):
        return self.tokens[self.current] if self.has_more_tokens() else (None, None)

    def token(self):
        return self.tokens[self.current] if self.has_more_tokens() else (None, None)

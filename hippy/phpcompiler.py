from hippy.lexer import Token, Lexer
from hippy.sourceparser import SourceParser, LexerWrapper, RULES
from hippy.astcompiler import compile_ast


class PHPLexerWrapper(LexerWrapper):
    def __init__(self, source):
        self.lexer = Lexer(RULES)
        self.source = source
        self.startlineno = 1
        self.startindex = 0

    def next(self):
        if self.startindex >= 0:
            # "literal" mode, i.e. outside "<?php ?>" tags: generates
            # one B_LITERAL_BLOCK until the next opening "<?php" tag
            source = self.source
            tagindex = source.find('<?', self.startindex)
            if tagindex == -1:
                tagindex = len(source)
            if tagindex > self.startindex:
                block_of_text = source[self.startindex:tagindex]
                tok = Token('B_LITERAL_BLOCK', block_of_text, self.startlineno)
                self.startlineno += block_of_text.count('\n')
            else:
                tok = None
            if source[tagindex:tagindex+5].lower() == '<?php':
                pos = tagindex + 5
            else:
                pos = tagindex + 2
            self.lexer.input(self.source, pos, self.startlineno)
            self.startindex = -1
            if tok is not None:
                return tok
        #
        while 1:
            tok = self.lexer.token()
            if tok is None:
                return None       # end of file
            elif tok.name == 'H_NEW_LINE':
                continue          # ignore these and continue
            elif tok.name == 'H_WHITESPACE':
                continue          # ignore these and continue
            elif tok.name == 'T_COMMENT':
                # look for "?>" inside single-line comments too
                if not tok.value.startswith('/*'):
                    i = tok.value.find('?>')
                    if i >= 0:
                        endpos = self.lexer.pos - len(tok.value) + i + 2
                        return self.end_current_block(tok, endpos)
                continue
            elif tok.name == 'B_END_OF_CODE_BLOCK':
                return self.end_current_block(tok, self.lexer.pos)
            else:
                return tok        # a normal php token

    def end_current_block(self, tok, endpos):
        # a "?>" marker that ends the current block of code
        # generates a ";" token followed by a B_LITERAL_BLOCK
        self.startlineno = tok.getsourcepos()
        self.startindex = endpos
        if (self.startindex < len(self.source) and
                self.source[self.startindex] == '\n'):
            self.startlineno += 1     # consume \n if immediately following
            self.startindex += 1
        return Token(";", ";", tok.getsourcepos())


def compile_php(filename, source, space):
    """Parse and compile a PHP file, starting in literal mode (i.e.
    dumping all input directly) until the first '<?' or '<?php'.
    Supports a mixture of blocks of code between the blocks of texts."""
    #
    phplexerwrapper = PHPLexerWrapper(source)
    parser = SourceParser(None)
    tokens = parser.parser.parse(phplexerwrapper, state=parser)
    bc = compile_ast(filename, source, tokens, space)
    return bc
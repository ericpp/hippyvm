from rply import Token
from pypy.rlib.rsre.rsre_re import compile

KEYWORDS = {
    "print": 'T_PRINT',
    "echo": 'T_ECHO',
    "instanceof": 'T_INSTANCEOF',
    "new": 'T_NEW',
    "clone": 'T_CLONE',
    "exit": 'T_EXIT',
    "if": 'T_IF',
    "elseif": 'T_ELSEIF',
    "else": 'T_ELSE',
    "endif": 'T_ENDIF',
    "array": 'T_ARRAY',
    "include": 'T_INCLUDE',
    "include_once": 'T_INCLUDE_ONCE',
    "eval": 'T_EVAL',
    "require": 'T_REQUIRE',
    "require_once": 'T_REQUIRE_ONCE',
    "or": 'T_LOGICAL_OR',
    "xor": 'T_LOGICAL_XOR',
    "and": 'T_LOGICAL_AND',
    "foreach": 'T_FOREACH',
    "endforeach": 'T_ENDFOREACH',
    "do": 'T_DO',
    "while": 'T_WHILE',
    "endwhile": 'T_ENDWHILE',
    "for": 'T_FOR',
    "endfor": 'T_ENDFOR',
    "declare": 'T_DECLARE',
    "enddeclare": 'T_ENDDECLARE',
    "as": 'T_AS',
    "switch": 'T_SWITCH',
    "endswitch": 'T_ENDSWITCH',
    "case": 'T_CASE',
    "default": 'T_DEFAULT',
    "break": 'T_BREAK',
    "continue": 'T_CONTINUE',
    "goto": 'T_GOTO',
    "function": 'T_FUNCTION',
    "const": 'T_CONST',
    "return": 'T_RETURN',
    "try": 'T_TRY',
    "catch": 'T_CATCH',
    "throw": 'T_THROW',
    "use": 'T_USE',
    "insteadof": 'T_INSTEADOF',
    "global": 'T_GLOBAL',
    "static": 'T_STATIC',
    "abstract": 'T_ABSTRACT',
    "final": 'T_FINAL',
    "private": 'T_PRIVATE',
    "protected": 'T_PROTECTED',
    "public": 'T_PUBLIC',
    "var": 'T_VAR',
    "unset": 'T_UNSET',
    "isset": 'T_ISSET',
    "empty": 'T_EMPTY',
    "class": 'T_CLASS',
    "trait": 'T_TRAIT',
    "interface": 'T_INTERFACE',
    "extends": 'T_EXTENDS',
    "implements": 'T_IMPLEMENTS',
    "list": 'T_LIST',
    "callable": 'T_CALLABLE',
    "null": 'T_NULL',
    "NULL": 'T_NULL',
    "true": 'T_TRUE',
    "TRUE": 'T_TRUE',
    "false": 'T_FALSE',
    "FALSE": 'T_FALSE',
   }

RULES = [
    ("[a-zA-Z_]+[0-9]*[a-zA-Z_]*", 'T_STRING'),
    ("\?\>", 'B_END_OF_CODE_BLOCK'),
    ("\x00", 'B_LITERAL_BLOCK'),

    # ("print", 'T_PRINT'),
    # ("echo", 'T_ECHO'),
    # ("instanceof", 'T_INSTANCEOF'),
    # ("new", 'T_NEW'),
    # ("clone", 'T_CLONE'),
    # ("exit", 'T_EXIT'),
    # ("if", 'T_IF'),
    # ("elseif", 'T_ELSEIF'),
    # ("else", 'T_ELSE'),
    # ("endif", 'T_ENDIF'),
    # ("array", 'T_ARRAY'),
    # ("include", 'T_INCLUDE'),
    # ("include_once", 'T_INCLUDE_ONCE'),
    # ("eval", 'T_EVAL'),
    # ("require", 'T_REQUIRE'),
    # ("require_once", 'T_REQUIRE_ONCE'),
    # ("or", 'T_LOGICAL_OR'),
    # ("xor", 'T_LOGICAL_XOR'),
    # ("and", 'T_LOGICAL_AND'),
    # ("foreach", 'T_FOREACH'),
    # ("endforeach", 'T_ENDFOREACH'),
    # ("do", 'T_DO'),
    # ("while", 'T_WHILE'),
    # ("endwhile", 'T_ENDWHILE'),
    # ("for", 'T_FOR'),
    # ("endfor", 'T_ENDFOR'),
    # ("declare", 'T_DECLARE'),
    # ("enddeclare", 'T_ENDDECLARE'),
    # ("as", 'T_AS'),
    # ("switch", 'T_SWITCH'),
    # ("endswitch", 'T_ENDSWITCH'),
    # ("case", 'T_CASE'),
    # ("default", 'T_DEFAULT'),
    # ("break", 'T_BREAK'),
    # ("continue", 'T_CONTINUE'),
    # ("goto", 'T_GOTO'),
    # ("function", 'T_FUNCTION'),
    # ("const", 'T_CONST'),
    # ("return", 'T_RETURN'),
    # ("try", 'T_TRY'),
    # ("catch", 'T_CATCH'),
    # ("throw", 'T_THROW'),
    # ("use", 'T_USE'),
    # ("insteadof", 'T_INSTEADOF'),
    # ("global", 'T_GLOBAL'),
    # ("static", 'T_STATIC'),
    # ("abstract", 'T_ABSTRACT'),
    # ("final", 'T_FINAL'),
    # ("private", 'T_PRIVATE'),
    # ("protected", 'T_PROTECTED'),
    # ("public", 'T_PUBLIC'),
    # ("var", 'T_VAR'),
    # ("unset", 'T_UNSET'),
    # ("isset", 'T_ISSET'),
    # ("empty", 'T_EMPTY'),
    # ("class", 'T_CLASS'),
    # ("trait", 'T_TRAIT'),
    # ("interface", 'T_INTERFACE'),
    # ("extends", 'T_EXTENDS'),
    # ("implements", 'T_IMPLEMENTS'),
    # ("list", 'T_LIST'),
    # ("callable", 'T_CALLABLE'),
    # ("null", 'T_NULL'),
    # ("NULL", 'T_NULL'),
    # ("true", 'T_TRUE'),
    # ("TRUE", 'T_TRUE'),
    # ("false", 'T_FALSE'),
    # ("FALSE", 'T_FALSE'),


    ("\+\=", 'T_PLUS_EQUAL'),
    ("\-\=", 'T_MINUS_EQUAL'),
    ("\*\=", 'T_MUL_EQUAL'),
    ("\/\=", 'T_DIV_EQUAL'),
    ("\.\=", 'T_CONCAT_EQUAL'),
    ("\%\=", 'T_MOD_EQUAL'),
    ("\&\=", 'T_AND_EQUAL'),
    ("\|\=", 'T_OR_EQUAL'),
    ("\^\=", 'T_XOR_EQUAL'),
    ("\<\<\=", 'T_SL_EQUAL'),
    ("\>\>\=", 'T_SR_EQUAL'),
    ("\|\|", 'T_BOOLEAN_OR'),
    ("\&\&", 'T_BOOLEAN_AND'),
    ("\=\=\=", 'T_IS_IDENTICAL'),
    ("\!\=\=", 'T_IS_NOT_IDENTICAL'),
    ("\=\=", 'T_IS_EQUAL'),
    ("\!\=", 'T_IS_NOT_EQUAL'),
    ("\<\=", 'T_IS_SMALLER_OR_EQUAL'),
    ("\>\=", 'T_IS_GREATER_OR_EQUAL'),
    ("\<\<", 'T_SL'),
    ("\>\>", 'T_SR'),
    ("\+\+", 'T_INC'),
    ("\-\-", 'T_DEC'),

    ("\((int|integer)\)", 'T_INT_CAST'),
    ("\((real|double|float)\)", 'T_DOUBLE_CAST'),
    ("\((string|binary)\)", 'T_STRING_CAST'),
    ("\(array\)", 'T_ARRAY_CAST'),
    ("\(object\)", 'T_OBJECT_CAST'),
    ("\((bool|boolean)\)", 'T_BOOL_CAST'),
    ("\(unset\)", 'T_UNSET_CAST'),
    ("\(unicode\)", 'T_UNICODE_CAST'),


    ("([0-9]*\.[0-9]*|[0-9][0-9]*)[eE](\+|\-)?[1-9][0-9]*", 'T_DNUMBER'),
    ("[0-9]+\.[0-9]+", 'T_DNUMBER'),
    ("\.[0-9]+", 'T_DNUMBER'),
    ("[0-9]+\.", 'T_DNUMBER'),
    ("0x([0-9]|[a-fA-F])*", 'T_LNUMBER'),
    ("0X([0-9]|[a-fA-F])*", 'T_LNUMBER'),
    ("[0-9]+", 'T_LNUMBER'),
    ("(\"[^\"]*\")|('[^']*')", 'T_CONSTANT_ENCAPSED_STRING'),

    ("\$[a-zA-Z_]+[0-9]*[a-zA-Z_]*", 'T_VARIABLE'),
    ("\$\{[a-zA-Z]*\}", 'T_STRING_VARNAME'),
    ("(//[^\n]*)|(#[^\n]*)|(/\*([^\*]|\*[^/])*\*/)", 'T_COMMENT'),

    ("\-\>", 'T_OBJECT_OPERATOR'),
    ("\=\>", 'T_DOUBLE_ARROW'),
    ("__CLASS__", 'T_CLASS_C'),
    ("__TRAIT__", 'T_TRAIT_C'),
    ("__METHOD__", 'T_METHOD_C'),
    ("__FUNCTION__", 'T_FUNC_C'),
    ("__LINE__", 'T_LINE'),
    ("__FILE__", 'T_FILE'),
    ("comment", 'T_COMMENT'),
    ("doc comment", 'T_DOC_COMMENT'),
    ("open tag", 'T_OPEN_TAG'),
    ("open tag with echo", 'T_OPEN_TAG_WITH_ECHO'),
    ("close tag", 'T_CLOSE_TAG'),
    ("whitespace", 'T_WHITESPACE'),
    ("heredoc start", 'T_START_HEREDOC'),
    ("heredoc end", 'T_END_HEREDOC'),
    #("\$\{", 'T_DOLLAR_OPEN_CURLY_BRACES'),
    # ("\{\$", 'T_CURLY_OPEN'),
    ("namespace", 'T_NAMESPACE'),
    ("__NAMESPACE__", 'T_NS_C'),
    ("__DIR__", 'T_DIR'),
    ("\\\\", 'T_NS_SEPARATOR'),
    ("\_\_halt_compiler", 'T_HALT_COMPILER'),


    ("\:\:", 'T_PAAMAYIM_NEKUDOTAYIM'),
    ("\&", '&'),
    ("\,", ','),
    ("\;", ';'),
    ("\:", ':'),
    ("\=", '='),
    ("\?", '?'),
    ("\|", '|'),
    ("\^", '^'),
    ("\<", '<'),
    ("\>", '>'),

    ("\+", '+'),
    ("\-", '-'),
    ("\.", '.'),
    ("\*", '*'),
    ("\/", '/'),
    ("\%", '%'),
    ("\!", '!'),
    ("\[", '['),
    ("\]", ']'),
    ('\(', '('),
    ('\)', ')'),
    ("\{", '{'),
    ("\}", '}'),
    ("\~", '~'),
    ("\@", '@'),
    ("\$", '$'),
    ("\"", '"'),
    ("\\n", 'H_NEW_LINE'),
    (" ", 'H_WHITESPACE'),

    ]

RULES = RULES  + KEYWORDS.items()

PRECEDENCES = [
    ("left", ["T_INCLUDE", "T_INCLUDE_ONCE", "T_EVAL", "T_REQUIRE", "T_REQUIRE_ONCE"]),
    ("left", [","]),
    ("left", ["T_LOGICAL_OR",]),
    ("left", ["T_LOGICAL_XOR",]),
    ("left", ["T_LOGICAL_AND",]),
    ("right", ["T_PRINT",]),
    #("right", ["T_YIELD",]),
    ("left", ['=', "T_PLUS_EQUAL", "T_MINUS_EQUAL", "T_MUL_EQUAL",
              "T_DIV_EQUAL", "T_CONCAT_EQUAL", "T_MOD_EQUAL",
              "T_AND_EQUAL", "T_OR_EQUAL", "T_XOR_EQUAL",
              "T_SL_EQUAL", "T_SR_EQUAL"]),
    ("left", ["?", ":"]),
    ("left", ["T_BOOLEAN_OR"]),
    ("left", ["T_BOOLEAN_AND"]),
    ("left", ["|"]),
    ("left", ["^"]),
    ("left", ["&"]),
    ("nonassoc", ["T_IS_EQUAL", "T_IS_NOT_EQUAL", "T_IS_IDENTICAL", "T_IS_NOT_IDENTICAL"]),
    ("nonassoc", ['<', "T_IS_SMALLER_OR_EQUAL", '>', "T_IS_GREATER_OR_EQUAL"]),
    ("left", ["T_SL", "T_SR"]),
    ("left", ["+", "-", "."]),
    ("left", ["*", "/", "%"]),
    ("nonassoc", ["T_INSTANCEOF"]),
    ("right", ['~', 'T_INC', 'T_DEC', 'T_INT_CAST', 'T_DOUBLE_CAST', 'T_STRING_CAST',
               'T_UNICODE_CAST', 'T_BINARY_CAST', 'T_ARRAY_CAST',
               'T_OBJECT_CAST', 'T_BOOL_CAST', 'T_UNSET_CAST', '@']),
    ("right", ["["]),
    ("nonassoc", ["T_NEW", "T_CLONE"]),
    # XXX TODO: find out why this doesnt work
    # ("left", ["T_ELSEIF"]),
    # ("left", ["T_ELSE"]),
    # ("left", ["T_ENDIF"]),
    ("right", ["T_STATIC", "T_ABSTRACT", "T_FINAL", "T_PRIVATE", "T_PROTECTED", "T_PUBLIC"]),

]


class LexerError(Exception):
    """ Lexer error exception.

        pos:
            Position in the input line where the error occurred.
    """
    def __init__(self, pos):
        self.pos = pos


class Lexer(object):
    """ A simple regex-based lexer/tokenizer.

        See below for an example of usage.
    """
    def __init__(self, rules, skip_whitespace=False):
        """ Create a lexer.

            rules:
                A list of rules. Each rule is a `regex, type`
                pair, where `regex` is the regular expression used
                to recognize the token and `type` is the type
                of the token to return when it's recognized.

            skip_whitespace:
                If True, whitespace (\s+) will be skipped and not
                reported by the lexer. Otherwise, you have to
                specify your rules for whitespace, or it will be
                flagged as an error.
        """
        self.rules = []
        for regex, type in rules:
            self.rules.append((compile(regex), type))

        self.skip_whitespace = skip_whitespace
        self.re_ws_skip = compile('\S')

    def input(self, buf, pos, lineno):
        """ Initialize the lexer with a buffer as input.
        """
        self.buf = buf
        self.pos = pos
        self.lineno = lineno

    def token(self):
        """ Return the next token (a Token object) found in the
            input buffer. None is returned if the end of the
            buffer was reached.
            In case of a lexing error (the current chunk of the
            buffer matches no rule), a LexerError is raised with
            the position of the error.
        """
        if self.pos >= len(self.buf):
            return None
        else:
            if self.skip_whitespace:
                m = self.re_ws_skip.search(self.buf[self.pos:])
                if m:
                    self.pos += m.start()
                else:
                    return None

            for token_regex, token_type in self.rules:
                m = token_regex.match(self.buf[self.pos:])
                if m:
                    if token_type == 'H_NEW_LINE':
                        self.lineno += 1
                    value = self.buf[self.pos + m.start():self.pos + m.end()]
                    if token_type == 'T_STRING':
                        keyword = KEYWORDS.get(value)
                        if keyword is not None:
                            token_type = keyword
                    tok = Token(token_type, value, self.lineno)
                    self.pos += m.end()
                    return tok

            # if we're here, no rule matched
            raise LexerError(self.pos)

    def tokens(self):
        """ Returns an iterator to the tokens found in the buffer.
        """
        while 1:
            tok = self.token()
            if tok is None:
                break
            while tok.name in ('H_NEW_LINE', 'H_WHITESPACE', 'T_COMMENT'):
                tok = self.token()
                if tok is None:
                    break
            yield tok

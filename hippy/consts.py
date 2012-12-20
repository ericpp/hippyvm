
""" Various important consts
"""

ARGVAL = 0xffff
ARGVAL1 = 0xfffe
ARGVAL2 = 0xfffc

# name, num_args, effect on stack
BYTECODES = [
    ('ILLEGAL', 0, 0),
    ('DISCARD_TOP', 0, -1),
    ('ROT_AND_DISCARD', 0, -1),
    ('STORE', 1, ARGVAL),
    ('STORE_FAST_REF', 1, 0),
    ('LOAD_CONST', 1, +1),
    ('LOAD_CONST_INTERPOLATE', 1, +1),
    ('LOAD_NAMED_CONSTANT', 1, +1),
    ('LOAD_NAME', 1, +1),
    ('LOAD_VAR_NAME', 1, +1),
    ('LOAD_FAST', 1, +1),
    ('LOAD_NULL', 0, +1),
    ('LOAD_NONE', 0, +1),
    ('BINARY_ADD', 0, -1),
    ('BINARY_OR_', 0, -1),
    ('BINARY_AND_', 0, -1),
    ('BINARY_SUB', 0, -1),
    ('BINARY_MUL', 0, -1),
    ('BINARY_DIV', 0, -1),
    ('BINARY_MOD', 0, -1),
    ('BINARY_CONCAT', 0, -1),
    ('BINARY_GT', 0, -1),
    ('BINARY_LT', 0, -1),
    ('BINARY_GE', 0, -1),
    ('BINARY_LE', 0, -1),
    ('BINARY_EQ', 0, -1),
    ('BINARY_IS', 0, -1),
    ('BINARY_ISNOT', 0, -1),
    ('BINARY_NE', 0, -1),
    ('BINARY_LSHIFT', 0, -1),
    ('BINARY_RSHIFT', 0, -1),
    ('SUFFIX_PLUSPLUS', 0, 0),
    ('SUFFIX_MINUSMINUS', 0, 0),
    ('PREFIX_PLUSPLUS', 0, 0),
    ('PREFIX_MINUSMINUS', 0, 0),
    ('UNARY_PLUS', 0, 0),
    ('UNARY_MINUS', 0, 0),
    ('UNARY_NOT', 0, 0),
    ('LOAD_VAR', 0, 0),
    ('IS_TRUE', 0, 0),
    ('ECHO', 1, ARGVAL),
    ('JUMP_IF_FALSE', 1, -1),
    ('JUMP_IF_FALSE_NO_POP', 1, 0),
    ('JUMP_IF_TRUE_NO_POP', 1, 0),
    ('JUMP_FORWARD', 1, 0),
    ('JUMP_BACKWARD', 1, 0),
    ('JUMP_BACK_IF_TRUE', 1, -1),
    ('JUMP_BACK_IF_NOT_DONE', 1, -1),
    ('RETURN', 0, -1),
    ('CALL', 1, ARGVAL1),
    ('GETITEM', 0, -1),
    ('FETCHITEM', 1, +1),
    ('STOREITEM', 1, -1),
    ('STOREITEM_REF', 1, 0),
    ('APPEND_INDEX', 1, 0),
    ('MAKE_REF', 1, 0),
    ('DUP_TOP_AND_NTH', 1, +2),
    ('POP_AND_POKE_NTH', 1, -1),
    ('DEREF', 0, 0),
    ('MAKE_ARRAY', 1, ARGVAL1),
    ('MAKE_HASH', 1, ARGVAL2),
    ('CREATE_ITER', 0, 0),
    ('NEXT_VALUE_ITER', 1, -1),
    ('NEXT_ITEM_ITER', 1, -2),
    ('DECLARE_GLOBAL', 1, 0),
    ('CAST_ARRAY', 0, 0),
]

BYTECODE_NUM_ARGS = []
BYTECODE_NAMES = []
BYTECODE_STACK_EFFECTS = []

BINOP_COMPARISON_LIST = ['le', 'ge', 'lt', 'gt', 'eq', 'ne']
BINOP_LIST = ['lshift', 'rshift', 'add', 'mul', 'sub', 'mod',
              'div', 'or_', 'and_'] + BINOP_COMPARISON_LIST

def _setup():
    for i, (bc, numargs, stack_effect) in enumerate(BYTECODES):
        globals()[bc] = i
        BYTECODE_NUM_ARGS.append(numargs)
        BYTECODE_NAMES.append(bc)
        BYTECODE_STACK_EFFECTS.append(stack_effect)
_setup()

BIN_OP_TO_BC = {'+': BINARY_ADD, '*': BINARY_MUL, '-': BINARY_SUB,
                '|': BINARY_OR_, '&': BINARY_AND_,
               '/': BINARY_DIV, '>': BINARY_GT, '<': BINARY_LT,
                '>=': BINARY_GE, '<=': BINARY_LE, '==': BINARY_EQ,
                '!=': BINARY_NE, '.': BINARY_CONCAT, '>>': BINARY_RSHIFT,
                '<<': BINARY_LSHIFT, '%': BINARY_MOD, '===': BINARY_IS,
                '!==': BINARY_ISNOT}
SUFFIX_OP_TO_BC = {'++': SUFFIX_PLUSPLUS, '--': SUFFIX_MINUSMINUS}
PREFIX_OP_TO_BC = {'++': PREFIX_PLUSPLUS, '--': PREFIX_MINUSMINUS,
                   '+': UNARY_PLUS, '-': UNARY_MINUS, '!': UNARY_NOT}
CAST_TO_BC = {'array': CAST_ARRAY}

ARG_ARGUMENT, ARG_REFERENCE, ARG_DEFAULT = range(3)

if __name__ == '__main__':
    for i, (bc, _, _) in enumerate(BYTECODES):
        print i, bc

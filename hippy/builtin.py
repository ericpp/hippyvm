import py
import math, time
from pypy.rlib import jit
from hippy.error import InterpreterError
from hippy.objects.base import W_Root
from hippy.objects.arrayobject import W_ArrayObject
from hippy.objects.reference import W_BaseContainerReference
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.streamio import open_file_as_stream

def create_function(signature, functocall):
    lines = ["def %s(space, frame, args_w):" % (functocall.func_name,)]
    inpi = 0
    for i, tp in enumerate(signature):
        if tp is int:
            lines.append('    arg%d = space.int_w(args_w[%d])' % (i, inpi))
            inpi += 1
        elif tp is bool:
            lines.append('    arg%d = space.is_true(args_w[%d])' % (i, inpi))
            inpi += 1
        elif tp == 'args_w':
            lines.append('    arg%d = [w_arg.deref() for w_arg in args_w]' % i)
        elif tp == 'args_w_unwrapped':
            lines.append('    arg%d = args_w' % i)
        elif tp == 'frame':
            lines.append('    arg%d = frame' % i)
        elif tp is float:
            lines.append('    arg%d = space.float_w(args_w[%d])' % (i, inpi))
            inpi += 1
        elif tp is str:
            lines.append('    arg%d = space.str_w(args_w[%d])' % (i, inpi))
            inpi += 1
        elif tp == 'space':
            lines.append('    arg%d = space' % i)
        elif tp is W_Root:
            lines.append('    arg%s = args_w[%s].deref()' % (i, inpi))
            inpi += 1
        elif tp == 'unwrapped':
            lines.append('    arg%s = args_w[%s]' % (i, inpi))
            inpi += 1
        else:
            raise Exception("Unknown signature %s" % tp)
    lines.append('    return orig_func(%s)' % ', '.join(['arg%d' % i
                                       for i in range(len(signature))]))
    source = '\n'.join(lines)
    d = {'orig_func': functocall}
    try:
        exec py.code.Source(source).compile() in d
    except:
        print source
        raise
    d[functocall.func_name]._jit_unroll_safe_ = True
    return d[functocall.func_name]

class ArgumentError(InterpreterError):
    """ An exception raised when function is called with a wrong
    number of args
    """

class AbstractFunction(object):
    def call(self, space, frame, args_w):
        raise NotImplementedError("abstract base class")

class BuiltinFunction(AbstractFunction):
    _immutable_fields_ = ['run']

    def __init__(self, signature, functocall):
        self.run = create_function(signature, functocall)

    def call(self, space, frame, args_w):
        return self.run(space, frame, args_w)

BUILTIN_FUNCTIONS = []

def wrap(signature, name=None, aliases=()):
    def inner(function):
        res = BuiltinFunction(signature, function)
        BUILTIN_FUNCTIONS.append((name or function.func_name, res))
        for alias in aliases:
            BUILTIN_FUNCTIONS.append((alias, res))
        return res
    return inner

@wrap(['space', float])
def cos(space, f):
    return space.wrap(math.cos(f))

@wrap(['space', float])
def sin(space, f):
    return space.wrap(math.sin(f))

@wrap(['space', float, float])
def pow(space, f, f2):
    return space.wrap(math.pow(f, f2))

@wrap(['space', W_Root], name="abs")
def _abs(space, obj):
    return space.wrap(space.abs(obj))

@wrap(['space', W_Root])
def strlen(space, w_obj):
    return space.wrap(space.strlen(space.as_string(w_obj)))

@wrap(['space', str, W_Root])
def define(space, name, w_obj):
    if name in space.ec.interpreter.constants:
        raise InterpreterError("constant already defined")
    space.ec.interpreter.constants[name.lower()] = w_obj
    return space.w_Null

# XXX unroll_iff probably
@jit.unroll_safe
@wrap(['space', 'args_w'])
def max(space, args_w):
    if len(args_w) == 1:
        raise InterpreterError("unimplemented one-arg max")
    cur_max_i = -1
    cur_max = 0.0
    for i, w_arg in enumerate(args_w):
        if w_arg is not space.w_Null:
            if cur_max_i != -1:
                v = space.float_w(w_arg)
                if v > cur_max:
                    cur_max = v
                    cur_max_i = i
            else:
                cur_max_i = i
                cur_max = space.float_w(w_arg)
    if cur_max_i == -1:
        return space.w_Null
    return args_w[cur_max_i]

@wrap(['space', 'frame', 'args_w_unwrapped'])
@jit.unroll_safe
def unset(space, frame, args_w):
    to_clean = []
    for w_arg in args_w:
        if isinstance(w_arg, W_BaseContainerReference):
            if w_arg.isset(space):
                to_clean.append(w_arg)
            continue
        frame.store_var(space, w_arg, space.w_Null)
    for w_arg in to_clean:
        frame.store_var(space, w_arg, space.w_Null)
    return space.w_Null

@wrap(['space', 'unwrapped'])
def isset(space, w_obj):
    # optimization - be careful about forcing non-existing elements
    # from an array
    if isinstance(w_obj, W_BaseContainerReference):
        if not w_obj.isset(space):
            return space.w_False
        return space.wrap(w_obj.deref() is not space.w_Null)
    return space.wrap(w_obj.deref() is not space.w_Null)

@wrap(['space', 'args_w'])
def printf(space, args_w):
    if len(args_w) == 0:
        raise InterpreterError("Not enough arguments for printf")
    no = 1
    format = space.str_w(args_w[0])
    # improve the estimate
    builder = StringBuilder(len(format) + 5 * format.count('%'))
    i = 0
    while i < len(format):
        c = format[i]
        if c == '%':
            if i == len(format) - 1:
                raise InterpreterError("wrong % in string format")
            next = format[i + 1]
            if next == '%':
                builder.append('%')
            elif next == 'd':
                if no == len(args_w):
                    raise InterpreterError("not enough args to process")
                builder.append(str(space.int_w(args_w[no])))
            else:
                raise InterpreterError("Unknown format char")
            i += 2
        else:
            builder.append(c)
            i += 1
    space.ec.interpreter.echo(space, space.newstrconst(builder.build()))
    return space.w_Null

@wrap(['space', W_Root])
def is_array(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_array)

@wrap(['space', W_Root])
def is_bool(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_bool)

@wrap(['space', W_Root])
def is_int(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_int)

@wrap(['space', W_Root])
def is_integer(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_int)

@wrap(['space', W_Root])
def is_long(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_int)

@wrap(['space', W_Root])
def is_float(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_float)

@wrap(['space', W_Root])
def is_double(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_float)

@wrap(['space', W_Root])
def is_real(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_float)

@wrap(['space', W_Root])
def is_null(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_null)

@wrap(['space', W_Root])
def is_scalar(space, w_obj):
    return space.wrap(w_obj.tp in (space.tp_int, space.tp_float,
                                   space.tp_str, space.tp_bool))

@wrap(['space', W_Root])
def is_string(space, w_obj):
    return space.wrap(w_obj.tp == space.tp_str)

@wrap(['space', W_Root], aliases=['sizeof'])
def count(space, w_arr):
    if not isinstance(w_arr, W_ArrayObject):
        return space.wrap(int(space.is_true(w_arr))) # apparently
    return space.wrap(space.arraylen(w_arr))

@wrap(['space', 'args_w'])
def substr(space, args_w):
    if len(args_w) < 2 or len(args_w) > 3:
        raise InterpreterError("incorrect number of args")
    w_s = space.as_string(args_w[0])
    start = space.int_w(space.as_number(args_w[1]))
    lgt = w_s.strlen()
    if start < 0:
        start = lgt + start
    if len(args_w) == 3:
        stop = space.int_w(space.as_number(args_w[2]))
        if stop < 0:
            stop = lgt + stop
        else:
            stop += start
    else:
        stop = lgt
    if start < 0 or stop < 0 or start > lgt:
        raise InterpreterError("wrong start")
    if stop <= start:
        return space.newstrconst("")
    return w_s.strslice(space, start, stop)

@wrap(['space', W_Root], name='print')
def print_(space, w_arg):
    space.ec.interpreter.echo(space, w_arg)
    return space.w_Null

@wrap(['space', int])
def error_reporting(space, level):
    return space.w_Null

@wrap(['space', W_Root])
def empty(space, w_item):
    if w_item.tp == space.tp_array:
        return space.newbool(space.arraylen(w_item) == 0)
    return space.newbool(not space.is_true(w_item))


@wrap(['space', str])
def defined(space, name):
    try:
        w_c = space.ec.interpreter.constants[name]
    except KeyError:
        return space.w_False
    else:
        if w_c is space.w_Null:
            return space.w_False
        return space.w_True

@wrap(['space', str])
def file_get_contents(space, fname):
    f = open_file_as_stream(fname, 'r')
    res = f.readall()
    f.close()
    return space.newstrconst(res)

@wrap(['space'])
def getrusage(space):
    pairs = [
        (space.newstrconst('ru_utime.tv_sec'), space.wrap(time.time())),
        (space.newstrconst('ru_utime.tv_usec'), space.wrap(0)),
        (space.newstrconst('ru_stime.tv_sec'), space.wrap(0)),
        (space.newstrconst('ru_stime.tv_usec'), space.wrap(0))
        ]
    return space.new_array_from_pairs(pairs)

@wrap(['space', str, int])
def str_repeat(space, s, repeat):
    return space.newstrconst(s * repeat)

@wrap(['space', bool])
def microtime(space, is_float):
    if not is_float:
        raise InterpreterError("only is_float implemented")
    return space.wrap(time.time())

@wrap(['space', W_Root])
def gettype(space, w_x):
    return space.newstrconst(space.TYPENAMES[w_x.tp])

@wrap(['space', str])
def function_exists(space, funcname):
    return space.newbool(funcname in space.ec.interpreter.functions)

@wrap(['space', 'args_w'])
def var_dump(space, args_w):
    for w_x in args_w:
        w_x.var_dump(space, indent='', recursion={})
    return space.w_Null

def _print_r(space, w_x, indent, recursion, builder):
    if w_x.tp == space.tp_array:
        if w_x in recursion:
            builder.append('Array\n *RECURSION*')
            return
        recursion[w_x] = None
        builder.append('Array\n%s(' % indent)
        subindent = indent + '        '
        with space.iter(w_x) as w_iter:
            while not w_iter.done():
                w_key, w_value = w_iter.next_item(space)
                if w_key.tp == space.tp_int:
                    key = space.int_w(w_key)
                    s = '\n%s    [%d] => ' % (indent, key)
                else:
                    key = space.str_w(w_key)
                    s = '\n%s    ["%s"] => ' % (indent, key)
                builder.append(s)
                _print_r(space, w_value, subindent, recursion, builder)
        builder.append('\n%s)\n' % indent)
        del recursion[w_x]
    else:
        builder.append(space.conststr_w(space.as_string(w_x)))

@wrap(['space', 'args_w'])
def print_r(space, args_w):
    if len(args_w) < 1 or len(args_w) > 2:
        raise InterpreterError("incorrect number of args")
    builder = StringBuilder()
    _print_r(space, args_w[0], '', {}, builder)
    result = builder.build()
    if len(args_w) >= 2 and space.is_true(args_w[1]):
        return space.newstrconst(result)
    else:
        space.ec.writestr(result)
        return space.w_True

from hippy.module.serialize import unserialize

unserialize = wrap(['space', str])(unserialize)

def setup_builtin_functions(interpreter, space):
    for name, func in BUILTIN_FUNCTIONS:
        interpreter.functions[name] = func

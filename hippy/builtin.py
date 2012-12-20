import py
import math, time
from pypy.rlib import jit
from hippy.error import InterpreterError
from hippy.objects.base import W_Root
from hippy.objects.arrayobject import W_ArrayObject
from pypy.rlib.rstring import StringBuilder
from pypy.rlib.streamio import open_file_as_stream

class BuiltinFunctionBuilder(object):
    def __init__(self, signature, functocall):
        self.signature = signature
        self.functocall = functocall
        self.input_i = 0
        self.length_at_least = None

    def header(self):
        # call this *after* lines_for_arg()
        lines = []
        lines.append("@unroll_safe")
        lines.append("def %s(space, frame, nb_args):" %
                         (self.functocall.func_name,))
        length_at_least = self.length_at_least
        if length_at_least is None:
            lines.append("    if nb_args != %d:" % (self.input_i,))
            lines.append("        self.warn_at_least(%d)" % (self.input_i,))
            lines.append("        return space.w_Null")
            lines.append("    nb_args = %d  #constant below" % (self.input_i,))
        else:
            lines.append("    if nb_args < %d:" % (length_at_least,))
            lines.append("        self.warn_at_least(%d)" % (length_at_least,))
            lines.append("        return space.w_Null")
        return lines

    def footer(self):
        allargs = ', '.join(['arg%d' % i for i in range(len(self.signature))])
        return ['    return orig_func(%s)' % allargs]

    def _value_arg(self, i, convertion):
        self.input_i += 1
        lines = ['    w_arg = frame.peek_nth(nb_args - %d)' % (self.input_i,),
                 '    arg%d = %s' % (i, convertion)]
        return lines

    def _value_args_w(self, i):
        self.input_i += 1
        self.length_at_least = self.input_i
        lines = ['    arg%d = [frame.peek_nth(i) ' % (i,) +
                 'for i in range(nb_args - %d, -1, -1)]' % (self.input_i,)]
        self.input_i = None    # all arguments consumed
        return lines

    def lines_for_arg(self, i, tp):
        if tp is int:
            return self._value_arg(i, 'space.int_w(w_arg)')
        elif tp is bool:
            return self._value_arg(i, 'space.is_true(w_arg)')
        elif tp == 'args_w':
            return self._value_args_w(i)
        elif tp == 'args_w_unwrapped':
            return ['    XXX_args_w_unwrapped']
        elif tp == 'frame':
            return ['    arg%d = frame' % i]
        elif tp is float:
            return self._value_arg(i, 'space.float_w(w_arg)')
        elif tp is str:
            return self._value_arg(i, 'space.str_w(w_arg)')
        elif tp == 'space':
            return ['    arg%d = space' % i]
        elif tp is W_Root:
            return self._value_arg(i, 'w_arg')
        elif tp == 'unwrapped':
            return ['    XXX_unwrapped']
        else:
            raise Exception("Unknown signature %r" % tp)

def create_function(signature, functocall):
    builder = BuiltinFunctionBuilder(signature, functocall)
    lines = []
    for i, tp in enumerate(signature):
        lines.extend(builder.lines_for_arg(i, tp))
    lines = builder.header() + lines + builder.footer()
    source = '\n'.join(lines)
    d = {'orig_func': functocall, 'unroll_safe': jit.unroll_safe}
    try:
        exec py.code.Source(source).compile() in d
    except:
        print source
        raise
    return d[functocall.func_name]

class ArgumentError(InterpreterError):
    """ An exception raised when function is called with a wrong
    number of args
    """

class AbstractFunction(W_Root):
    def argument_is_byref(self, i):
        raise NotImplementedError("abstract base class")
    def prepare_argument(self, space, i, w_argument):
        raise NotImplementedError("abstract base class")
    def call(self, space, parent_frame, nb_args):
        raise NotImplementedError("abstract base class")

class BuiltinFunction(AbstractFunction):
    _immutable_fields_ = ['run']

    def __init__(self, signature, functocall):
        self.run = create_function(signature, functocall)

    def argument_is_byref(self, i):
        return False    # XXX

    def prepare_argument(self, space, i, w_argument):
        # XXX assume arguments are all by value
        return w_argument.deref()

    def call(self, space, parent_frame, nb_args):
        return self.run(space, parent_frame, nb_args)

BUILTIN_FUNCTIONS = []

def wrap(signature, name=None, aliases=()):
    assert name is None or isinstance(name, str)
    assert isinstance(aliases, (tuple, list))
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
        space.ec.notice("Constant %s already defined" % name)
        return space.w_False
    space.ec.interpreter.constants[name.lower()] = w_obj
    return space.w_True

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
        space.ec.notice("printf(): expects at least 1 parameter, 0 given")
        return space.w_False
    no = 1
    format = space.str_w(args_w[0])
    # improve the estimate
    builder = StringBuilder(len(format) + 5 * format.count('%'))
    i = 0
    while i < len(format):
        c = format[i]
        if c == '%':
            if i == len(format) - 1:
                space.ec.hippy_warn("printf(): wrong % in string format")
                i += 1
                continue
            next = format[i + 1]
            if next == '%':
                builder.append('%')
            elif next == 'd':
                if no == len(args_w):
                    space.ec.warn("printf(): Too few arguments")
                    return space.w_False
                builder.append(str(space.int_w(args_w[no])))
            else:
                space.ec.hippy_warn("printf(): Unknown format char " + next)
            i += 2
        else:
            builder.append(c)
            i += 1
    if no < len(args_w):
        space.ec.hippy_warn("printf(): Too many arguments passed")
    s = builder.build()
    space.ec.interpreter.echo(space, space.newstrconst(s))
    return space.wrap(len(s))

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
        builder.append(space.str_w(space.as_string(w_x)))

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

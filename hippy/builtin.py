
import py
import math, time
from hippy.error import InterpreterError
from hippy.objects.base import W_Root
from hippy.objects.arrayobject import W_ArrayObject
from hippy.objects.reference import W_BaseContainerReference
from pypy.rlib import jit
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
            raise Exception("Uknown signature %s" % tp)
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
    if w_item.tp == space.w_array:
        return space.newbool(space.arraylen(w_item) == 0)
    return space.newbool(not space.is_true(w_item))

fill_keys_driver = jit.JitDriver(greens = [],
                                 reds = ['w_value', 'w_res', 'w_arrayiter'],
                                 name='fill_keys',
                                 should_unroll_one_iteration=lambda *args: True)

@wrap(['space', W_Root, W_Root])
def array_fill_keys(space, w_arr, w_value):
    w_res = space.new_array_from_pairs([])
    with space.iter(w_arr) as w_arrayiter:
        while not w_arrayiter.done():
            fill_keys_driver.jit_merge_point(w_value=w_value, w_res=w_res,
                                             w_arrayiter=w_arrayiter)
            w_item = w_arrayiter.next(space)
            space.setitem(w_res, w_item, w_value)

    return w_res

@wrap(['space', W_Root])
def is_array(space, w_obj):
    return space.wrap(w_obj.tp == space.w_array)

def is_int(s):
    if not s:
        return False
    if s[0] == "0" and len(s) != 1:
        return False
    for c in s:
        if c >= '9' or c <= '0':
            return False
    return True

@wrap(['space', 'args_w'])
def array_merge(space, args_w):
    lst = [] # list of values or (None, val) in case of ints
    is_hash = False
    for w_arg in args_w:
        w_arg = space.as_array(w_arg)
        with space.iter(w_arg) as w_iter:
            while not w_iter.done():
                w_key, w_value = w_iter.next_item(space)
            # XXX a fair bit inefficient
                if w_key.tp == space.w_int or is_int(space.str_w(w_key)):
                    lst.append((None, w_value))
                else:
                    lst.append((w_key, w_value))
                    is_hash = True
    if not is_hash:
        return space.new_array_from_list([i for _, i in lst])
    else:
        r = []
        i = 0
        for w_k, w_v in lst:
            if w_k is None:
                r.append((space.wrap(i), w_v))
            else:
                r.append((w_k, w_v))
        return space.new_array_from_pairs(r)

@wrap(['space', 'args_w'])
def array_diff_key(space, args_w):
    if len(args_w) < 2:
        raise InterpreterError("not enough arguments to array_diff_key")
    for w_arg in args_w:
        if w_arg.tp != space.w_array:
            # issue notice, ignored anyway
            return space.w_Null
    w_arr = space.as_array(args_w[0])
    args_w = [space.as_array(w_arg) for w_arg in args_w[1:]]
    keys = []
    with space.iter(w_arr) as w_iter:
        while not w_iter.done():
            w_key, _ = w_iter.next_item(space)
            for w_arg in args_w:
                if w_arg.isset_index(space, w_key):
                    break
            else:
                keys.append(w_key)
    return space.new_array_from_list(keys)

@wrap(['space', W_Root, int])
def array_change_key_case(space, w_arr, str_case):
    pairs = []

    if w_arr.tp != space.w_array:
        return space.w_Null

    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_value = itr.next_item(space)
            if w_key.tp == space.w_str:
                k_str = w_key.str_w(space)
                if str_case == 1:
                    k_str = k_str.upper()
                else:
                    k_str = k_str.lower()
                pairs.append((space.newstrconst(k_str), w_value))
            else:
                pairs.append((w_key, w_value))
    return space.new_array_from_pairs(pairs)


# @wrap(['space', W_Root, bool])
# def array_chunk(space, w_arr, keep_keys):

@wrap(['space', W_Root, W_Root])
def array_combine(space, w_arr_a, w_arr_b):
    if w_arr_a.tp != space.w_array:
        return space.w_False
    if w_arr_b.tp != space.w_array:
        return space.w_False
    if space.arraylen(w_arr_a) != space.arraylen(w_arr_b):
        return space.w_False
    if space.arraylen(w_arr_a) == 0 or space.arraylen(w_arr_b) == 0:
        return space.w_False
    pairs = []
    with space.iter(w_arr_a) as a_iter:
        with space.iter(w_arr_b) as b_iter:
            while not a_iter.done():
                _, a_w_value = a_iter.next_item(space)
                _, b_w_value = b_iter.next_item(space)
                pairs.append((a_w_value, b_w_value))
    return space.new_array_from_pairs(pairs)

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

from hippy.module.serialize import unserialize

unserialize = wrap(['space', str])(unserialize)

def setup_builtin_functions(interpreter, space):
    for name, func in BUILTIN_FUNCTIONS:
        interpreter.functions[name] = func

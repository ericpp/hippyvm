from pypy.rlib import jit
from hippy.objects.base import W_Root
from hippy.error import InterpreterError
from builtin import is_int
from builtin import wrap
BUILTIN_FUNCTIONS = []


fill_keys_driver = jit.JitDriver(
    greens=[],
    reds=['w_value', 'w_res', 'w_arrayiter'],
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


@wrap(['space', 'args_w'])
def array_merge(space, args_w):
    lst = []  # list of values or (None, val) in case of ints
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


@wrap(['space', 'args_w'])
def array_slice(space, args_w):
    w_start = space.newint(0)
    w_end = space.newint(0)
    w_keep_keys = space.newbool(False)
    w_arr = []
    if len(args_w) < 2:
        raise InterpreterError("first argument must be array,\
 second must be int")
    else:
        if args_w[0].tp == space.w_array and args_w[1].tp == space.w_int:
            w_arr = args_w[0]
            w_start = args_w[1]
        else:
            raise InterpreterError("first argument must be array,\
 second must be int")
    if len(args_w) == 2:
        # w_arr, start
        w_end = space.newint(space.arraylen(w_arr))
    if len(args_w) == 3:
        # w_arr, start, end
        # w_arr, start, keep_keys
        if args_w[2].tp == space.w_bool:
            w_keep_keys = args_w[2]
            w_end = space.newint(space.arraylen(w_arr))
        elif args_w[2].tp == space.w_int:
            w_end = args_w[2]
        else:
            raise InterpreterError("third arugment must be int or bool")

    if len(args_w) == 4:
        # w_arr, start, end, keep_keys
        if args_w[2].tp == space.w_int and args_w[3].tp == space.w_bool:
            w_end = args_w[2]
            w_keep_keys = args_w[3]
        else:
            raise InterpreterError("third arugment must\
 be int and fourth must be bool")
    return space.slice(w_arr, w_start, w_end, w_keep_keys)


@wrap(['space', 'args_w'])
def array_chunk(space, args_w):
    res_arr = []
    if len(args_w) < 2:
        raise InterpreterError("function need at least two \
arguments array and int")
    if args_w[0].tp != space.w_array and args_w[0].tp != space.w_int:
        raise InterpreterError("function need at least two \
 arguments array and int")
    w_arr = args_w[0]
    w_chunk_size = args_w[1]
    chunk_size = space.int_w(w_chunk_size)
    w_keep_keys = space.newbool(False)
    last_idx = 0
    if len(args_w) == 3:
        keep_keys = args_w[2]
    for i in range(chunk_size, space.arraylen(w_arr) + chunk_size, chunk_size):
        res_arr.append(space.slice(w_arr,
                                   space.newint(last_idx),
                                   space.newint(last_idx + chunk_size),
                                   w_keep_keys))
        last_idx = i
    return space.new_array_from_list(res_arr)


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


@wrap(['space', W_Root])
def array_flip(space, w_arr):
    pairs = []
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_val = itr.next_item(space)
            if w_key.tp not in (space.w_int, space.w_str) or\
                    w_val.tp not in(space.w_int, space.w_str):
                pairs.append((w_key, w_val))
            pairs.append((w_val, w_key))
    return space.new_array_from_pairs(pairs)


@wrap(['space', 'args_w'])
def array_keys(space, args_w):
    w_search = None
    w_strict = space.newbool(False)
    idx = 0
    pairs = []
    if len(args_w) < 1:
        raise InterpreterError("array_keys take at least one argument")
    else:
        if args_w[0].tp == space.w_array:
            w_arr = args_w[0]
        else:
            raise InterpreterError("array_keys first arg must be array")
    if len(args_w) == 2:
        w_search = args_w[1]
    if len(args_w) == 3:
        w_search = args_w[1]
        if args_w[2].tp == space.w_bool:
            w_strict = args_w[2]
        else:
            raise InterpreterError("third arugment must be bool")
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_val = itr.next_item(space)
            if w_search:
                if space.str_w(w_val) == space.str_w(w_search):
                    if space.is_true(w_strict):
                        if w_val.tp == w_search.tp:
                            pairs.append((space.newint(idx), w_key))
                            idx += 1
                    else:
                        pairs.append((space.newint(idx), w_key))
                        idx += 1
            else:
                pairs.append((space.newint(idx), w_key))
                idx += 1
    return space.new_array_from_pairs(pairs)


@wrap(['space', W_Root])
def array_values(space, w_arr):
    pairs = []
    idx = 0
    with space.iter(w_arr) as itr:
        while not itr.done():
            _, w_val = itr.next_item(space)
            pairs.append((space.newint(idx), w_val))
            idx += 1
    return space.new_array_from_pairs(pairs)


# @wrap(['space', 'args_w'])
# def array_reverse(space, args_w):
#     keys = []
#     vals = []
#     last_idx = 0
#     keep_keys = space.newbool(False)
#     if len(args_w) < 1:
#         raise InterpreterError("function need at least one argument array")
#     if args_w[0].tp != space.w_array:
#         raise InterpreterError("function need at least one argument array")
#     w_arr = args_w[0]
#     if len(args_w) == 2:
#         if args_w[1].tp != space.w_bool:
#             raise InterpreterError("preserve_keys has to be bool")
#         keep_keys = args_w[1]

#     with space.iter(w_arr) as itr:
#         while not itr.done():
#             key, val = itr.next_item(space)
#             if key.tp == space.w_int and (not space.is_true(keep_keys)):
#                 keys.append(last_idx)
#                 last_idx += 1
#             else:
#                 keys.append(key)
#             vals.append(val)
#     pairs = zip(list(reversed(keys)), vals)
#     return space.new_array_from_pairs(pairs)

@wrap(['space', W_Root])
def array_sum(space, w_arr):
    res = 0
    with space.iter(w_arr) as itr:
        while not itr.done():
            _, w_val = itr.next_item(space)
            res += space.int_w(space.as_number(w_val))
    return space.newint(res)


@wrap(['space', W_Root])
def array_product(space, w_arr):
    res = 1
    with space.iter(w_arr) as itr:
        while not itr.done():
            _, w_val = itr.next_item(space)
            res *= space.int_w(space.as_number(w_val))
    return space.newint(res)


def setup_array_functions(interpreter, space):
    for name, func in BUILTIN_FUNCTIONS:
        interpreter.functions[name] = func

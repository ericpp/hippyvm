from hippy.objects.base import W_Root
from hippy.objects.arrayobject import new_rdict
from hippy.error import InterpreterError
from builtin import wrap


def is_int(s):
    if not s:
        return False
    if s[0] == "0" and len(s) != 1:
        return False
    for c in s:
        if c >= '9' or c <= '0':
            return False
    return True


@wrap(['space', W_Root, W_Root])
def array_fill_keys(space, w_arr, w_value):
    pairs = []
    with space.iter(w_arr) as w_arrayiter:
        while not w_arrayiter.done():
            w_item = w_arrayiter.next(space)
            pairs.append((w_item, w_value))
    return space.new_array_from_pairs(pairs)


@wrap(['space', W_Root, W_Root, W_Root])
def array_fill(space, w_sidx, w_num, w_value):
    pairs = []
    sidx = space.int_w(w_sidx)
    num = space.int_w(w_num)
    for i in range(sidx, num):
        pairs.append((space. newint(i), w_value))
    return space.new_array_from_pairs(pairs)


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
                if w_key.tp == space.tp_int or is_int(space.str_w(w_key)):
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
        if w_arg.tp != space.tp_array:
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


@wrap(['space', 'args_w'])
def array_diff_assoc(space, args_w):
    if len(args_w) < 2:
        raise InterpreterError("not enough arguments to array_diff_key")
    for w_arg in args_w:
        if w_arg.tp != space.tp_array:
            # issue notice, ignored anyway
            return space.w_Null
    w_arr = space.as_array(args_w[0])
    args_w = [space.as_array(w_arg) for w_arg in args_w[1:]]
    pairs = []
    with space.iter(w_arr) as w_iter:
        while not w_iter.done():
            w_key, w_val = w_iter.next_item(space)
            for w_arg in args_w:
                if w_arg.isset_index(space, w_key):
                    try:
                        other_w_val = space.getitem(w_arg, w_key)
                        if space.str_eq(other_w_val, w_val):
                            break
                    except InterpreterError:
                        pairs.append((w_key, w_val))
            else:
                pairs.append((w_key, w_val))
    return space.new_array_from_pairs(pairs)


@wrap(['space', W_Root, int])
def array_change_key_case(space, w_arr, str_case):
    pairs = []

    if w_arr.tp != space.tp_array:
        return space.w_Null

    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_value = itr.next_item(space)
            if w_key.tp == space.tp_str:
                k_str = w_key.str_w(space)
                if str_case == 1:
                    k_str = k_str.upper()
                else:
                    k_str = k_str.lower()
                pairs.append((space.newstr(k_str), w_value))
            else:
                pairs.append((w_key, w_value))
    return space.new_array_from_pairs(pairs)


@wrap(['space', 'args_w'])
def array_slice(space, args_w):
    start = 0
    end = 0
    keep_keys = False
    if len(args_w) < 2:
        raise InterpreterError("first argument must be array,\
 second must be int")
    else:
        if args_w[0].tp == space.tp_array and args_w[1].tp == space.tp_int:
            w_arr = args_w[0]
            start = space.int_w(space.as_number(args_w[1]))
        else:
            raise InterpreterError("first argument must be array,"
                                   " second must be int")
    if len(args_w) == 2:
        # w_arr, start
        end = space.arraylen(w_arr)
    if len(args_w) == 3:
        # w_arr, start, end
        # w_arr, start, keep_keys
        if args_w[2].tp == space.tp_bool:
            keep_keys = space.is_true(args_w[2])
            end = space.arraylen(w_arr)
        elif args_w[2].tp == space.tp_int:
            end = space.int_w(space.as_number(args_w[2]))
        else:
            raise InterpreterError("third arugment must be int or bool")

    if len(args_w) == 4:
        # w_arr, start, end, keep_keys
        if args_w[2].tp == space.tp_int and args_w[3].tp == space.tp_bool:
            end = space.int_w(args_w[2])
            keep_keys = space.is_true(args_w[3])
        else:
            raise InterpreterError("third arugment must"
                                   "be int and fourth must be bool")
    return space.slice(w_arr, start, end, keep_keys)


@wrap(['space', 'args_w'])
def array_chunk(space, args_w):
    res_arr = []
    if len(args_w) < 2:
        raise InterpreterError("function need at least two \
arguments array and int")
    if args_w[0].tp != space.tp_array and args_w[0].tp != space.tp_int:
        raise InterpreterError("function need at least two \
 arguments array and int")
    w_arr = args_w[0]
    w_chunk_size = args_w[1]
    chunk_size = space.int_w(w_chunk_size)
    keep_keys = False
    last_idx = 0
    if len(args_w) == 3:
        keep_keys = space.is_true(args_w[2])
    for i in range(chunk_size, space.arraylen(w_arr) + chunk_size, chunk_size):
        res_arr.append(space.slice(w_arr, last_idx,
                                   last_idx + chunk_size, keep_keys))
        last_idx = i
    return space.new_array_from_list(res_arr)


@wrap(['space', W_Root, W_Root])
def array_combine(space, w_arr_a, w_arr_b):
    if w_arr_a.tp != space.tp_array:
        return space.w_False
    if w_arr_b.tp != space.tp_array:
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
            if w_key.tp not in (space.tp_int, space.tp_str) or\
                    w_val.tp not in(space.tp_int, space.tp_str):
                space.ec.warn("Warning: array_flip(): Can only flip "
                              "STRING and INTEGER values!")
            else:
                pairs.append((w_val, w_key))
    return space.new_array_from_pairs(pairs)


@wrap(['space', 'args_w'])
def array_keys(space, args_w):
    w_search = None
    strict = False
    idx = 0
    pairs = []
    if len(args_w) < 1:
        raise InterpreterError("array_keys take at least one argument")
    else:
        if args_w[0].tp == space.tp_array:
            w_arr = args_w[0]
        else:
            raise InterpreterError("array_keys first arg must be array")
    if len(args_w) == 2:
        w_search = args_w[1]
    if len(args_w) == 3:
        w_search = args_w[1]
        if args_w[2].tp == space.tp_bool:
            strict = space.is_true(args_w[2])
        else:
            raise InterpreterError("third arugment must be bool")
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_val = itr.next_item(space)
            if w_search:
                if space.str_w(w_val) == space.str_w(w_search):
                    if strict:
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
            w_val = itr.next(space)
            pairs.append((space.newint(idx), w_val))
            idx += 1
    return space.new_array_from_pairs(pairs)


@wrap(['space', W_Root])
def array_count_values(space, w_arr):
    dct_w = new_rdict()
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_val = itr.next(space).deref()
            if not (w_val.tp == space.tp_int or w_val.tp == space.tp_str):
                space.ec.warn("Warning: array_count_values(): Can only count "
                              "STRING and INTEGER values!")
                continue
            key = space.str_w(w_val)
            try:
                w_val = dct_w[key]
            except KeyError:
                nextval = 1
            else:
                nextval = space.int_w(w_val) + 1
            dct_w[key] = space.newint(nextval)
    return space.new_array_from_rdict(dct_w)


def _pad_array(space, w_arr, pairs, idx):
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_val = itr.next_item(space)
            if w_key.tp != space.tp_int:
                pairs.append((w_key, w_val))
            else:
                pairs.append((space.newint(idx), w_val))
                idx += 1
    return idx


@wrap(['space', W_Root, int, W_Root])
def array_pad(space, w_arr, size, w_value):
    pairs = []
    arr_len = space.arraylen(w_arr)
    pad_size = abs(size) - arr_len
    if pad_size <= 0:     # XXX size == -sys.maxint-1?
        return w_arr
    if size > 0:
        idx = _pad_array(space, w_arr, pairs, 0)
        for i in range(pad_size):
            pairs.append((space.newint(idx + i), w_value))
    else:
        idx = 0
        for i in range(size + arr_len, 0):
            pairs.append((space.newint(idx), w_value))
            idx += 1
        _pad_array(space, w_arr, pairs, idx)
    return space.new_array_from_pairs(pairs)


@wrap(['space', 'args_w'])
def array_reverse(space, args_w):
    keep_keys = False
    if len(args_w) < 1:
        raise InterpreterError("function need at least one argument array")
    if args_w[0].tp != space.w_array:
        raise InterpreterError("function need at least one argument array")
    if len(args_w) == 2:
        # if args_w[1].tp != space.w_bool:
        #     raise InterpreterError("array_reverse() expects parameter"
        #                            " 2 to be boolean")
        keep_keys = space.is_true(args_w[1])
    w_arr = args_w[0]
    keys = []
    vals = []
    idx = space.arraylen(w_arr) - 1
    with space.iter(w_arr) as itr:
        while not itr.done():
            w_key, w_val = itr.next_item(space)
            if keep_keys:
                keys.append(w_key)
            else:
                keys.append(space.newint(idx))
                idx -= 1
            vals.append(w_val)
    pairs = zip(reversed(keys), reversed(vals))
    return space.new_array_from_pairs(pairs)


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
    if space.arraylen(w_arr) == 0:
        return space.newint(0)
    res = 1
    with space.iter(w_arr) as itr:
        while not itr.done():
            _, w_val = itr.next_item(space)
            res *= space.int_w(space.as_number(w_val))
    return space.newint(res)

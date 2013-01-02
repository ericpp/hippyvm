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

# array_change_key_case - Changes all keys in an array
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

# array_chunk - Split an array into chunks
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

# array_combine - Creates an array by using one array for keys and another for its values
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

# array_count_values - Counts all the values of an array
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

# array_diff_assoc - Computes the difference of arrays with additional index check
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

# array_diff_key - Computes the difference of arrays using keys for comparison
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



# array_diff_uassoc - Computes the difference of arrays with additional
#                     index check which is performed by a user supplied
#                     callback function
@wrap(['space', 'args_w'])
def array_diff_uassoc(space, args_w):
    raise NotImplementedError()

# array_diff_ukey - Computes the difference of arrays using a callback
#                   function on the keys for comparison
@wrap(['space', 'args_w'])
def array_diff_ukey(space, args_w):
    raise NotImplementedError()

# array_diff - Computes the difference of arrays
@wrap(['space', 'args_w'])
def array_diff(space, args_w):
    raise NotImplementedError()


# array_fill_keys - Fill an array with values, specifying keys
@wrap(['space', W_Root, W_Root])
def array_fill_keys(space, w_arr, w_value):
    pairs = []
    with space.iter(w_arr) as w_arrayiter:
        while not w_arrayiter.done():
            w_item = w_arrayiter.next(space)
            pairs.append((w_item, w_value))
    return space.new_array_from_pairs(pairs)


# array_fill - Fill an array with values
@wrap(['space', W_Root, W_Root, W_Root])
def array_fill(space, w_sidx, w_num, w_value):
    pairs = []
    sidx = space.int_w(w_sidx)
    num = space.int_w(w_num)
    for i in range(sidx, num):
        pairs.append((space. newint(i), w_value))
    return space.new_array_from_pairs(pairs)


# array_filter - Filters elements of an array using a callback function
@wrap(['space', W_Root, W_Root])
def array_filter(space, w_arr, w_callback):
    raise NotImplementedError()

# array_flip - Exchanges all keys with their associated values in an array
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

# array_intersect_assoc - Computes the intersection of arrays with additional index check
@wrap(['space', 'args_w'])
def array_intersect_assoc(space, args_w):
    raise NotImplementedError()

# array_intersect_key - Computes the intersection of arrays using keys for comparison
@wrap(['space', 'args_w'])
def array_intersect_key(space, args_w):
    raise NotImplementedError()

# array_intersect_uassoc - Computes the intersection of arrays with additional index check,
#                          compares indexes by a callback function
@wrap(['space', 'args_w'])
def array_intersect_uassoc(space, args_w):
    raise NotImplementedError()

# array_intersect_ukey - Computes the intersection of arrays using a
#                        callback function on the keys for comparison
@wrap(['space', 'args_w'])
def array_intersect_ukey(space, args_w):
    raise NotImplementedError()

# array_intersect - Computes the intersection of arrays
@wrap(['space', 'args_w'])
def array_intersect(space, args_w):
    raise NotImplementedError()

# array_key_exists - Checks if the given key or index exists in the array
@wrap(['space', 'W_Root', 'W_Root'])
def array_intersect(space, w_key, w_arr):
    raise NotImplementedError()

# array_keys - Return all the keys or a subset of the keys of an array
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

# array_map - Applies the callback to the elements of the given arrays
@wrap(['space', 'args_w'])
def array_map(space, args_w):
    raise NotImplementedError()

# array_merge_recursive - Merge two or more arrays recursively
@wrap(['space', 'args_w'])
def array_merge_recursive(space, args_w):
    raise NotImplementedError()

# array_merge - Merge one or more arrays
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


# array_multisort - Sort multiple or multi-dimensional arrays
@wrap(['space', 'args_w'])
def array_multisort(space, args_w):
    raise NotImplementedError()

# array_pad - Pad array to the specified length with a value
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

# array_pop - Pop the element off the end of array
@wrap(['space', 'W_Root'])
def array_pop(space, w_arr):
    raise NotImplementedError()


# array_product - Calculate the product of values in an array
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

# array_push - Push one or more elements onto the end of array
@wrap(['space', 'args_w'])
def array_push(space, args_w):
    raise NotImplementedError()

# array_rand - Pick one or more random entries out of an array
@wrap(['space', 'args_w'])
def array_rand(space, args_w):
    raise NotImplementedError()

# array_reduce - Iteratively reduce the array to a single
#                value using a callback function
@wrap(['space', 'args_w'])
def array_reduce(space, args_w):
    raise NotImplementedError()

# array_replace_recursive - Replaces elements from passed arrays
#                           into the first array recursively
@wrap(['space', 'args_w'])
def array_replace_recursive(space, args_w):
    raise NotImplementedError()

# array_replace - Replaces elements from passed arrays into the first array
@wrap(['space', 'args_w'])
def array_replace(space, args_w):
    raise NotImplementedError()

# array_reverse - Return an array with elements in reverse order
@wrap(['space', 'args_w'])
def array_reverse(space, args_w):
    raise NotImplementedError()

# array_search - Searches the array for a given value and
#                returns the corresponding key if successful
@wrap(['space', 'args_w'])
def array_search(space, args_w):
    raise NotImplementedError()

# array_shift - Shift an element off the beginning of array
@wrap(['space', 'W_Root'])
def array_shift(space, w_arr):
    raise NotImplementedError()

# array_slice - Extract a slice of the array
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


# array_splice - Remove a portion of the array and replace it with something else
@wrap(['space', 'W_Root'])
def array_splice(space, w_arr):
    raise NotImplementedError()

# array_sum - Calculate the sum of values in an array
@wrap(['space', W_Root])
def array_sum(space, w_arr):
    res = 0
    with space.iter(w_arr) as itr:
        while not itr.done():
            _, w_val = itr.next_item(space)
            res += space.int_w(space.as_number(w_val))
    return space.newint(res)


# array_udiff_assoc - Computes the difference of arrays with additional index check,
#                     compares data by a callback function
@wrap(['space', 'args_w'])
def array_udiff_assoc(space, args_w):
    raise NotImplementedError()

# array_udiff_uassoc - Computes the difference of arrays with additional index check,
#                      compares data and indexes by a callback function
@wrap(['space', 'args_w'])
def array_udiff_uassoc(space, args_w):
    raise NotImplementedError()

# array_udiff - Computes the difference of arrays by using a callback function for data comparison
@wrap(['space', 'args_w'])
def array_udiff(space, args_w):
    raise NotImplementedError()

# array_uintersect_assoc - Computes the intersection of arrays with additional index check,
#                          compares data by a callback function
@wrap(['space', 'args_w'])
def array_uintersect_assoc(space, args_w):
    raise NotImplementedError()

# array_uintersect_uassoc - Computes the intersection of arrays with additional index check,
#                           compares data and indexes by a callback functions
@wrap(['space', 'args_w'])
def array_uintersect_uassoc(space, args_w):
    raise NotImplementedError()

# array_uintersect - Computes the intersection of arrays, compares data by a callback function
@wrap(['space', 'args_w'])
def array_uintersect(space, args_w):
    raise NotImplementedError()

# array_unique - Removes duplicate values from an array
@wrap(['space', 'args_w'])
def array_unique(space, args_w):
    raise NotImplementedError()

# array_unshift - Prepend one or more elements to the beginning of an array
@wrap(['space', 'args_w'])
def array_unshift(space, args_w):
    raise NotImplementedError()

# array_values - Return all the values of an array
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

# array_walk_recursive - Apply a user function recursively to every member of an array
@wrap(['space', 'args_w'])
def array_walk_recursive(space, args_w):
    raise NotImplementedError()

# array_walk - Apply a user function to every member of an array
@wrap(['space', 'args_w'])
def array_walk(space, args_w):
    raise NotImplementedError()

# array - Create an array
# arsort - Sort an array in reverse order and maintain index association
@wrap(['space', 'args_w'])
def arsort(space, args_w):
    raise NotImplementedError()

# asort - Sort an array and maintain index association
@wrap(['space', 'args_w'])
def asort(space, args_w):
    raise NotImplementedError()

# compact - Create array containing variables and their values
@wrap(['space', 'args_w'])
def compact(space, args_w):
    raise NotImplementedError()

# count - Count all elements in an array, or something in an object
@wrap(['space', 'args_w'])
def count(space, args_w):
    raise NotImplementedError()

# current - Return the current element in an array
@wrap(['space', 'args_w'])
def current(space, args_w):
    raise NotImplementedError()

# each - Return the current key and value pair from an array and advance the array cursor
@wrap(['space', 'args_w'])
def each(space, args_w):
    raise NotImplementedError()

# end - Set the internal pointer of an array to its last element
@wrap(['space', 'args_w'])
def end(space, args_w):
    raise NotImplementedError()

# extract - Import variables into the current symbol table from an array
@wrap(['space', 'args_w'])
def extract(space, args_w):
    raise NotImplementedError()

# in_array - Checks if a value exists in an array
@wrap(['space', 'args_w'])
def in_array(space, args_w):
    raise NotImplementedError()

# key - Fetch a key from an array
@wrap(['space', 'args_w'])
def key(space, args_w):
    raise NotImplementedError()

# krsort - Sort an array by key in reverse order
@wrap(['space', 'args_w'])
def krsort(space, args_w):
    raise NotImplementedError()

# ksort - Sort an array by key
@wrap(['space', 'args_w'])
def ksort(space, args_w):
    raise NotImplementedError()

# list - Assign variables as if they were an array
@wrap(['space', 'args_w'])
def list(space, args_w):
    raise NotImplementedError()

# natcasesort - Sort an array using a case insensitive "natural order" algorithm
@wrap(['space', 'args_w'])
def natcasesort(space, args_w):
    raise NotImplementedError()

# natsort - Sort an array using a "natural order" algorithm
@wrap(['space', 'args_w'])
def natsort(space, args_w):
    raise NotImplementedError()

# next - Advance the internal array pointer of an array
@wrap(['space', 'args_w'])
def next(space, args_w):
    raise NotImplementedError()

# pos - Alias of current
@wrap(['space', 'args_w'])
def pos(space, args_w):
    raise NotImplementedError()

# prev - Rewind the internal array pointer
@wrap(['space', 'args_w'])
def prev(space, args_w):
    raise NotImplementedError()

# range - Create an array containing a range of elements
@wrap(['space', 'args_w'])
def range(space, args_w):
    raise NotImplementedError()

# reset - Set the internal pointer of an array to its first element
@wrap(['space', 'args_w'])
def reset(space, args_w):
    raise NotImplementedError()

# rsort - Sort an array in reverse order
@wrap(['space', 'args_w'])
def rsort(space, args_w):
    raise NotImplementedError()

# shuffle - Shuffle an array
@wrap(['space', 'args_w'])
def shuffle(space, args_w):
    raise NotImplementedError()

# sizeof - Alias of count
@wrap(['space', 'args_w'])
def sizeof(space, args_w):
    raise NotImplementedError()

# sort - Sort an array
@wrap(['space', 'args_w'])
def sort(space, args_w):
    raise NotImplementedError()

# uasort - Sort an array with a user-defined comparison function and maintain index association
@wrap(['space', 'args_w'])
def uasort(space, args_w):
    raise NotImplementedError()

# uksort - Sort an array by keys using a user-defined comparison function
@wrap(['space', 'args_w'])
def uksort(space, args_w):
    raise NotImplementedError()

# usort - Sort an array by values using a user-defined comparison function
@wrap(['space', 'args_w'])
def usort(space, args_w):
    raise NotImplementedError()

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

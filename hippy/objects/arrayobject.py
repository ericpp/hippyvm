
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize, we_are_translated
from pypy.rlib.rarithmetic import ovfcheck
from hippy.objects.base import W_Root
from hippy.error import InterpreterError
from hippy.rpython.rdict import RDict
from hippy.objects.reference import W_Reference
from hippy.objects.convert import force_float_to_int_in_any_way


def new_rdict():
    return RDict(W_Root)

def try_convert_str_to_int(key):
    # try to convert 'key' from a string to an int, but carefully:
    # we must not remove any space, make sure the result does not
    # overflows, etc.  In general we have to make sure that the
    # result, when converted back to a string, would give exactly
    # the original string.
    try:
        i = int(key)     # XXX can be done a bit more efficiently
    except (ValueError, OverflowError):
        raise ValueError
    if str(i) != key:
        raise ValueError
    return i

@specialize.argtype(1)
def wrap_array_key(space, key):
    if isinstance(key, str):
        try:
            key = try_convert_str_to_int(key)
        except ValueError:
            return space.newstr(key)
    return space.newint(key)


class W_ArrayObject(W_Root):
    """Abstract base class.  Concrete subclasses use various strategies.
    This base class defines the general methods that can be implemented
    without needing to call (too often) the arraylen(), _getitem_str()
    and _getitem_int() methods.
    """

    @staticmethod
    def new_array_from_list(space, lst_w):
        return W_ListArrayObject(space, lst_w)

    @staticmethod
    def new_array_from_rdict(space, dct_w):
        return W_RDictArrayObject(space, dct_w)

    @staticmethod
    def new_array_from_pairs(space, pairs_ww):
        rdct_w = new_rdict()
        next_idx = 0
        for w_key, w_value in pairs_ww:
            if w_key is not None:
                as_int, as_str = W_ArrayObject._getindex(space, w_key)
                if as_int > next_idx:
                    next_idx = as_int + 1
            else:
                as_int, as_str = next_idx, None   # XXX FIX ME XXX Setting next index
                next_idx += 1
            if as_str is None:
                as_str = str(as_int)
            rdct_w[as_str] = w_value
        return W_RDictArrayObject(space, rdct_w)

    def is_true(self, space):
        return self.arraylen() > 0

    def _getindex(space, w_arg):
        "Returns a pair (int, str), where only one of the two is meaningful"
        if w_arg.tp == space.tp_int:
            return space.int_w(w_arg), None
        elif w_arg.tp == space.tp_str:
            return 0, space.str_w(w_arg)
        elif w_arg.tp == space.tp_float:
            return force_float_to_int_in_any_way(space.float_w(w_arg)), None
        else:
            # XXX make a real warning
            raise Exception("Warning: Illegal offset type")
    _getindex._always_inline_ = True
    _getindex = staticmethod(_getindex)

    def getitem(self, space, w_arg):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._getitem_int(as_int)
        else:
            return self._getitem_str(as_str)

    def setitem(self, space, w_arg, w_value):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._setitem_int(as_int, w_value, False)
        else:
            return self._setitem_str(as_str, w_value, False)

    def setitem_ref(self, space, w_arg, w_ref):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._setitem_int(as_int, w_ref, True)
        else:
            return self._setitem_str(as_str, w_ref, True)

    def unsetitem(self, space, w_arg):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._unsetitem_int(as_int)
        else:
            return self._unsetitem_str(as_str)

    def isset_index(self, space, w_index):
        as_int, as_str = self._getindex(space, w_index)
        if as_str is None:
            return self._isset_int(as_int)
        else:
            return self._isset_str(as_str)

    def append_index(self, space):
        # XXX bogus! fix me!
        return space.newint(self.arraylen())

    def _getitem_int(self, index):
        raise NotImplementedError("abstract")

    def _getitem_str(self, key):
        raise NotImplementedError("abstract")

    def _setitem_int(self, index, w_value, as_ref):
        raise NotImplementedError("abstract")

    def _setitem_str(self, key, w_value, as_ref):
        raise NotImplementedError("abstract")

    def _unsetitem_int(self, index):
        raise NotImplementedError("abstract")

    def _unsetitem_str(self, key):
        raise NotImplementedError("abstract")

    def _isset_int(self, index):
        raise NotImplementedError("abstract")

    def _isset_str(self, key):
        raise NotImplementedError("abstract")

    def arraylen(self):
        raise NotImplementedError("abstract")

    def as_rdict(self):
        raise NotImplementedError("abstract")

    def as_dict(self):
        "NOT_RPYTHON: for tests only"
        rdict = self.as_rdict()
        it = rdict.iter()
        d = {}
        for i in range(len(rdict)):
            key, w_value = it.nextitem()
            d[key] = w_value
        return d

    def var_dump(self, space, indent, recursion):
        if self in recursion:
            space.ec.writestr('%s*RECURSION*\n' % indent)
            return
        recursion[self] = None
        space.ec.writestr('%sarray(%d) {\n' % (indent, self.arraylen()))
        subindent = indent + '  '
        with space.iter(self) as itr:
            while not itr.done():
                w_key, w_value = itr.next_item(space)
                if w_key.tp == space.tp_int:
                    key = space.int_w(w_key)
                    s = '%s[%d]=>\n' % (subindent, key)
                else:
                    key = space.str_w(w_key)
                    s = '%s["%s"]=>\n' % (subindent, key)
                space.ec.writestr(s)
                w_value.var_dump(space, subindent, recursion)
        space.ec.writestr('%s}\n' % indent)
        del recursion[self]

    def as_string(self, space):
        return space.newstr("Array")


class W_ListArrayObject(W_ArrayObject):
    _has_string_keys = False

    def __init__(self, space, lst_w):
        self.space = space
        self.lst_w = lst_w

    def as_unique_arraylist(self):
        return W_ListArrayObject(self.space, self.lst_w[:])

    def arraylen(self):
        return len(self.lst_w)

    def as_rdict(self):
        d = new_rdict()
        for i in range(len(self.lst_w)):
            d[str(i)] = self.lst_w[i]
        return d

    def _getitem_int(self, index):
        if index >= 0:
            try:
                return self.lst_w[index]
            except IndexError:
                pass
        return self.space.w_Null

    def _getitem_str(self, key):
        try:
            i = try_convert_str_to_int(key)
        except ValueError:
            return self.space.w_Null
        return self._getitem_int(i)

    def _setitem_int(self, index, w_value, as_ref):
        if index < 0 or index > self.arraylen():
            return self._setitem_str_fresh(str(index), w_value)
        res = self.as_unique_arraylist()
        lst_w = res.lst_w
        if index == len(lst_w):
            lst_w.append(w_value)
        else:
            if not as_ref:
                w_old = lst_w[index]
            else:
                w_old = None
            if isinstance(w_old, W_Reference):
                w_old.w_value = w_value
            else:
                lst_w[index] = w_value
        return res

    def _setitem_str(self, key, w_value, as_ref):
        try:
            i = try_convert_str_to_int(key)
        except ValueError:
            return self._setitem_str_fresh(key, w_value)
        else:
            return self._setitem_int(i, w_value, as_ref)

    def _setitem_str_fresh(self, key, w_value):
        d = self.as_rdict()    # make a fresh dictionary
        assert key not in d
        d[key] = w_value
        return W_RDictArrayObject(self.space, d)

    def _unsetitem_int(self, index):
        if index < 0 or index >= self.arraylen():
            return self
        if index == self.arraylen() - 1:
            res = self.as_unique_arraylist()
            del res.lst_w[index]
            return res
        else:
            d = self.as_rdict()   # make a fresh dictionary
            del d[str(index)]
            return W_RDictArrayObject(self.space, d)

    def _unsetitem_str(self, key):
        try:
            i = try_convert_str_to_int(key)
        except ValueError:
            return self     # str key, so not in the array at all
        else:
            return self._unsetitem_int(i)

    def _isset_int(self, index):
        return 0 <= index < self.arraylen()

    def _isset_str(self, key):
        try:
            i = try_convert_str_to_int(key)
        except ValueError:
            return False
        else:
            return self._isset_int(i)

    def create_iter(self, space):
        from hippy.objects.arrayiter import W_ListArrayIterator
        return W_ListArrayIterator(self.lst_w)


class W_RDictArrayObject(W_ArrayObject):
    _has_string_keys = True
    strategy_name = 'hash'

    def __init__(self, space, dct_w):
        if not we_are_translated():
            assert isinstance(dct_w, RDict)
        self.space = space
        self.dct_w = dct_w

    def as_rdict(self):
        return self.dct_w

    def as_unique_arraydict(self):
        return W_RDictArrayObject(self.space, self.dct_w.copy())

    def arraylen(self):
        return len(self.dct_w)

    def _getitem_int(self, index):
        return self._getitem_str(str(index))

    def _getitem_str(self, key):
        try:
            return self.dct_w[key]
        except KeyError:
            return self.space.w_Null

    def _setitem_int(self, index, w_value, as_ref):
        return self._setitem_str(str(index), w_value, as_ref)

    def _setitem_str(self, key, w_value, as_ref):
        res = self.as_unique_arraydict()
        dct_w = res.dct_w
        if not as_ref:
            try:
                w_old = dct_w[key]
            except KeyError:
                w_old = None
        else:
            w_old = None
        if isinstance(w_old, W_Reference):   # and is not None
            w_old.w_value = w_value
        else:
            dct_w[key] = w_value
        return res

    def _unsetitem_int(self, index):
        return self._unsetitem_str(str(index))

    def _unsetitem_str(self, key):
        if key not in self.dct_w:
            return self
        res = self.as_unique_arraydict()
        del res.dct_w[key]
        return res

    def _isset_int(self, index):
        return self._isset_str(str(index))

    def _isset_str(self, key):
        return key in self.dct_w

    def create_iter(self, space):
        from hippy.objects.arrayiter import W_RDictArrayIterator
        return W_RDictArrayIterator(self.dct_w)


from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from pypy.rlib.rarithmetic import ovfcheck
from hippy.objects.base import W_Root
from hippy.objects import arrayiter
from hippy.error import InterpreterError
from hippy.rpython.rdict import RDict
from hippy.objects.reference import W_Reference
from hippy.objects.convert import force_float_to_int_in_any_way


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
    def new_array_from_dict(space, dct_w):
        return W_DictArrayObject(space, dct_w)

    @staticmethod
    def new_array_from_pairs(space, pairs_ww):
        dct_w = {}
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
            dct_w[as_str] = w_value
        return W_DictArrayObject(space, dct_w)

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

    def _convert_str_to_int(key):
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
    _convert_str_to_int = staticmethod(_convert_str_to_int)

    def getitem(self, space, w_arg):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._getitem_int(as_int)
        else:
            return self._getitem_str(as_str)

    def setitem(self, space, w_arg, w_value):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            res = self._setitem_int(as_int, w_value, False)
        else:
            res = self._setitem_str(as_str, w_value, False)
        return res, w_value

    def setitem_ref(self, space, w_arg, w_ref):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._setitem_int(as_int, w_ref, True)
        else:
            return self._setitem_str(as_str, w_ref, True)

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

    def arraylen(self):
        raise NotImplementedError("abstract")

    def as_dict(self):
        raise NotImplementedError("abstract")

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


class W_ListArrayObject(W_ArrayObject):
    _has_string_keys = False

    def __init__(self, space, lst_w):
        self.space = space
        self.lst_w = lst_w

    def as_unique_arraylist(self):
        return W_ListArrayObject(self.space, self.lst_w[:])

    def arraylen(self):
        return len(self.lst_w)

    def as_dict(self):
        d = {}
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
            i = self._convert_str_to_int(key)
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
            i = self._convert_str_to_int(key)
        except ValueError:
            return self._setitem_str_fresh(key, w_value)
        else:
            return self._setitem_int(i, w_value, as_ref)

    def _setitem_str_fresh(self, key, w_value):
        d = self.as_dict()    # make a fresh dictionary
        assert key not in d
        d[key] = w_value
        return W_DictArrayObject(self.space, d)


class W_DictArrayObject(W_ArrayObject):
    _has_string_keys = True

    def __init__(self, space, dct_w):
        self.space = space
        self.dct_w = dct_w

    def as_dict(self):
        return self.dct_w

    def as_unique_arraydict(self):
        return W_DictArrayObject(self.space, self.dct_w.copy())

    def arraylen(self):
        return len(self._dct_w)

    def _getitem_int(self, index):
        return self._getitem_str(str(index))

    def _getitem_str(self, key):
        return self.dct_w.get(key, self.space.w_Null)

    def _setitem_int(self, index, w_value, as_ref):
        return self._setitem_str(str(index), w_value, as_ref)

    def _setitem_str(self, key, w_value, as_ref):
        res = self.as_unique_arraydict()
        dct_w = res.dct_w
        if not as_ref:
            w_old = dct_w.get(key, None)
        else:
            w_old = None
        if isinstance(w_old, W_Reference):   # and is not None
            w_old.w_value = w_value
        else:
            dct_w[key] = w_value
        return res

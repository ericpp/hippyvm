
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

    def is_true(self, space):
        return self.arraylen() > 0

    def _getindex(self, space, w_arg):
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

    def getitem(self, space, w_arg):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._getitem_int(as_int)
        else:
            return self._getitem_str(as_str)

    def setitem(self, space, w_arg, w_value):
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._setitem_int(as_int, w_value)
        else:
            return self._setitem_str(as_str, w_value)

    def setitem_ref(self, space, w_arg, w_ref):
        #xx
        assert isinstance(w_ref, W_Reference)
        as_int, as_str = self._getindex(space, w_arg)
        if as_str is None:
            return self._setitemref_int(as_int, w_ref)
        else:
            return self._setitemref_str(as_str, w_ref)

    def append_index(self, space):
        # XXX bogus! fix me!
        return space.newint(self.arraylen())

    def _getitem_int(self, index):
        raise NotImplementedError("abstract")

    def _getitem_str(self, key):
        raise NotImplementedError("abstract")

    def _setitem_int(self, index, w_value):
        raise NotImplementedError("abstract")

    def _setitem_str(self, key, w_value):
        raise NotImplementedError("abstract")

    def _setitemref_int(self, index, w_ref):
        raise NotImplementedError("abstract")

    def _setitemref_str(self, key, w_ref):
        raise NotImplementedError("abstract")

    def arraylen(self):
        raise NotImplementedError("abstract")

    def as_dict(self):
        raise NotImplementedError("abstract")


class W_ListArrayObject(W_ArrayObject):

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
        # try to convert 'key' from a string to an int, but carefully:
        # we must not remove any space, make sure the result does not
        # overflows, etc.  In general we have to make sure that the
        # result, when converted back to a string, would give exactly
        # the original string.
        try:
            i = int(key)     # XXX can be done a bit more efficiently
        except (ValueError, OverflowError):
            return self.space.w_Null
        if str(i) != key:
            return self.space.w_Null
        return self._getitem_int(i)

    def _setitem_int(self, index, w_value):
        if index < 0 or index > self.arraylen():
            return self._setitem_str(str(index), w_value)
        res = self.as_unique_arraylist()
        lst_w = res.lst_w
        if index == len(lst_w):
            lst_w.append(w_value)
        else:
            w_old = lst_w[index]
            if isinstance(w_old, W_Reference):
                #xx
                w_old.w_value = w_value
            else:
                lst_w[index] = w_value
        return res

    def _setitem_str(self, key, w_value):
        d = self.as_dict()
        d[key] = w_value
        return W_DictArrayObject(self.space, d)

    def _setitemref_int(self, index, w_ref):
        #xx
        res = self.as_unique_arraylist()
        lst_w = res.lst_w
        if index == len(lst_w):
            lst_w.append(w_ref)
        else:
            assert 0 <= index < len(lst_w)
            lst_w[index] = w_ref
        return res

    # XXX missing _setitem_str and _setitemref_str


class W_DictArrayObject(W_ArrayObject):

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

    def _setitem_int(self, index, w_value):
        return self._setitem_str(str(index), w_value)

    def _setitem_str(self, key, w_value):
        res = self.as_unique_arraydict()
        dct_w = res.dct_w
        w_old = dct_w.get(key, None)
        if isinstance(w_old, W_Reference):   # and is not None
            #xx
            w_old.w_value = w_value
        else:
            dct_w[key] = w_value
        return res

    def _setitemref_int(self, index, w_ref):
        #xx
        return self._setitemref_str(str(index), w_ref)

    def _setitemref_str(self, key, w_ref):
        #xx
        res = self.as_unique_arraydict()
        res.dct_w[key] = w_ref
        return res

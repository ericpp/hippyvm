
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from hippy.objects.base import W_Root
from hippy.objects import arrayiter
from hippy.error import InterpreterError
from hippy.rpython.rdict import RDict
from hippy.objects.reference import W_Reference


class W_ArrayObject(W_Root):
    """Abstract base class.  Concrete subclasses use various strategies.
    This base class defines the general methods that can be implemented
    without needing to call (too often) the arraylen() and w_item()
    methods.
    """

    @staticmethod
    def new_array_from_list(lst_w):
        return W_ListArrayObject(lst_w)


class ArrayMixin(object):
    """This is a mixin to provide a more efficient implementation for
    each subclass.  It defines the methods that call arraylen() and w_item()
    a lot.  Being a mixin, each method is actually repeated in the
    subclass, which allows arraylen() and w_item() to be inlined.
    """
    _mixin_ = True

    def is_true(self, space):
        return self.arraylen() > 0

    def getitem(self, space, w_arg):
        index = space.int_w(w_arg)
        assert 0 <= index < self.arraylen()
        return self.w_item(index)

    def setitem(self, space, w_index, w_value):
        res = self.as_unique_arraylist()
        res._inplace_setitem(space, w_index, w_value)
        return res

    def as_unique_arraylist(self):
        lst_w = [self.w_item(i) for i in range(self.arraylen())]
        return W_ListArrayObject(lst_w)

    def append(self, space, w_item):
        res = self.as_unique_arraylist()
        res._lst_w.append(w_item)    # XXX bogus
        return res


class W_ListArrayObject(ArrayMixin, W_ArrayObject):
    _refcount = 0

    def __init__(self, lst_w):
        self._lst_w = lst_w

    def arraylen(self):
        return len(self._lst_w)

    def w_item(self, index):
        return self._lst_w[index]

    def as_unique_arraylist(self):
        #if self._refcount == 1:
        #    return self
        #assert self._refcount > 1
        return W_ListArrayObject(self._lst_w[:])

    def incref(self):
        self._refcount += 1

    def decref(self):
        self._refcount -= 1

    def _inplace_setitem(self, space, w_arg, w_value):
        index = space.int_w(w_arg)
        assert 0 <= index < self.arraylen()
        lst_w = self._lst_w
        w_old = lst_w[index]
        w_value = w_value.deref()
        if isinstance(w_old, W_Reference):
            w_old.w_value = w_value
        else:
            lst_w[index] = w_value

    def _inplace_setitem_ref(self, space, w_arg, w_ref):
        index = space.int_w(w_arg)
        assert 0 <= index < self.arraylen()
        lst_w = self._lst_w
        assert isinstance(w_ref, W_Reference)
        lst_w[index] = w_ref

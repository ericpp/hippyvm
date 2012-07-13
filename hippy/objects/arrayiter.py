
from hippy.objects.base import W_Root

class BaseArrayIterator(W_Root):
    pass

class ArrayIteratorMixin(object):
    _mixin_ = True

    def __init__(self, space, copy, storage):
        self.index = 0
        self.storage = storage
        self._copy = copy

    def _force_write(self):
        self.storage = self.storage[:]
        self._copy = None

    def done(self):
        return self.index >= len(self.storage)

    def next(self, space):
        index = self.index
        self.index += 1
        return space.wrap(self.storage[index])

    def next_item(self, space):
        index = self.index
        self.index += 1
        return space.wrap(index), space.wrap(self.storage[index])

    def mark_invalid(self):
        if self._copy is not None:
            self._copy.remove()

class IntArrayIterator(ArrayIteratorMixin, BaseArrayIterator):
    pass

class FloatArrayIterator(ArrayIteratorMixin, BaseArrayIterator):
    pass

class ListArrayIterator(ArrayIteratorMixin, BaseArrayIterator):
    pass

class EmptyArrayIterator(BaseArrayIterator):
    def __init__(self, space):
        pass

    def done(self):
        return True

    def next(self, space):
        assert False

    def next_item(self, space):
        assert False

class HashIterator(BaseArrayIterator):
    def __init__(self, space, copy, storage):
        self.dct = storage
        self.index = 0
        self.dctiter = storage.iter()
        self._copy = copy

    def _force_write(self):
        self.dct = self.dct.copy()
        self.dctiter = self.dct.iter() # this is wrong,
        self._copy = None
        # fix the ownership, easy just work

    def done(self):
        return self.index >= len(self.dct)

    def next(self, space):
        self.index += 1
        return self.dctiter.next()

    def next_item(self, space):
        self.index += 1
        item, w_value = self.dctiter.nextitem()
        return space.newstrconst(item), w_value

    def mark_invalid(self):
        if self._copy is not None:
            self._copy.remove()

class MapIterator(BaseArrayIterator):
    def __init__(self, space, copy, storage):
        dct, lst = storage
        sorted_keys = [None] * len(lst)
        for k, v in dct.iteritems():
            sorted_keys[v] = k
        self.sorted_keys = sorted_keys
        self.index = 0
        self.lst = lst
        self._copy = copy

    def _force_write(self):
        # those things are immutable
        self._copy = None

    def done(self):
        return self.index >= len(self.lst)

    def next(self, space):
        w_value = self.lst[self.index]
        self.index += 1
        return w_value

    def next_item(self, space):
        key = self.sorted_keys[self.index]
        assert key is not None
        w_value = self.lst[self.index]
        self.index += 1
        return space.newstrconst(key), w_value

    def mark_invalid(self):
        if self._copy is not None:
            self._copy.child = None

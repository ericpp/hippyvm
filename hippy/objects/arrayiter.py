
from hippy.objects.base import W_Root
from hippy.objects.arrayobject import wrap_array_key
from hippy.objects.reference import W_Reference


class W_BaseArrayIterator(W_Root):

    def next(self, space):
        raise NotImplementedError

    def next_item(self, space):
        raise NotImplementedError


class W_ListArrayIterator(W_BaseArrayIterator):

    def __init__(self, storage_w):
        self.storage_w = storage_w
        self.index = 0

    def next(self, space):
        index = self.index
        try:
            w_value = self.storage_w[index]
        except IndexError:
            raise StopIteration
        self.index = index + 1
        return w_value

    def next_item(self, space):
        index = self.index
        try:
            w_value = self.storage_w[index]
        except IndexError:
            raise StopIteration
        self.index = index + 1
        return wrap_array_key(space, index), w_value


class W_RDictArrayIterator(W_BaseArrayIterator):
    def __init__(self, rdct_w):
        self.rdct_w = rdct_w
        self.dctiter = rdct_w.iter()
        self.remaining = len(rdct_w)

    def next(self, space):
        if self.remaining <= 0:
            raise StopIteration
        self.remaining -= 1
        return self.dctiter.next()

    def next_item(self, space):
        if self.remaining <= 0:
            raise StopIteration
        self.remaining -= 1
        key, w_value = self.dctiter.nextitem()
        return wrap_array_key(space, key), w_value


class W_ArrayIteratorByReference(W_BaseArrayIterator):
    def __init__(self, space, arr_ref):
        self.arr_ref = arr_ref
        self.w_array = arr_ref.deref()
        self.arrayiter = space.create_iter(self.w_array)

    def make_reference(self, space, w_key, w_value):
        if not isinstance(w_value, W_Reference):
            w_value = W_Reference(w_value)
            w_newarray = space.setitem_ref(self.w_array, w_key, w_value)
            self.arr_ref.w_value = self.w_array = w_newarray
        return w_value

    def next(self, space):
        w_key, w_value = self.arrayiter.next_item(space)
        return self.make_reference(space, w_key, w_value)

    def next_item(self, space):
        w_key, w_value = self.arrayiter.next_item(space)
        return w_key, self.make_reference(space, w_key, w_value)

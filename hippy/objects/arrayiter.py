
from hippy.objects.base import W_Root


class BaseArrayIterator(W_Root):

    def done(self):
        return self.remaining <= 0


class W_ListArrayIterator(BaseArrayIterator):

    def __init__(self, storage_w):
        self.storage_w = storage_w
        self.remaining = len(storage_w)

    def next(self, space):
        rem = self.remaining
        index = len(self.storage_w) - rem
        assert index >= 0
        self.remaining = rem - 1
        return self.storage_w[index]

    def next_item(self, space):
        rem = self.remaining
        index = len(self.storage_w) - rem
        assert index >= 0
        self.remaining = rem - 1
        return str(index), self.storage_w[index]


class W_RDictArrayIterator(BaseArrayIterator):
    def __init__(self, rdct_w):
        self.rdct_w = rdct_w
        self.dctiter = rdct_w.iter()
        self.remaining = len(rdct_w)

    def next(self, space):
        self.remaining -= 1
        return self.dctiter.next()

    def next_item(self, space):
        self.remaining -= 1
        item, w_value = self.dctiter.nextitem()
        return item, w_value

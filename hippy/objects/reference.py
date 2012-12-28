
from hippy.objects.base import W_Root


class W_Reference(W_Root):
    """This is a reference got by &$stuff.  It is also used for local
    variables, which are all reference objects.  This is the only core
    PHP object that is mutable (we can change what it refers to).
    """
    _COUNTER = 0

    def __init__(self, w_value):
        assert not isinstance(w_value, W_Reference)
        self.w_value = w_value

    def deref(self):
        return self.w_value

    def __repr__(self):
        if not hasattr(self, '_counter'):
            self._counter = W_Reference._COUNTER
            W_Reference._COUNTER += 1
        return '<Ref%d: %s>' % (self._counter, self.w_value)

    def var_dump(self, space, indent, recursion):
        self.w_value.var_dump(space, indent + '&', recursion)

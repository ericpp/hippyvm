
from hippy.objects.base import W_Root

class W_Variable(W_Root):
    """ An elusive reference, only valid in this particular context.
    Should *only* ever be stored on the valuestack, otherwise we might
    run into performance issues
    """
    def __init__(self, frame, pos):
        assert pos >= 0
        self.pos = pos
        self.frame = frame

    def deref(self):
        return self.frame.vars_w[self.pos].deref()

    def copy(self, space):
        return self.deref().copy(space)

class W_Cell(W_Root):
    def __init__(self, v):
        assert isinstance(v, W_Root)
        self.v = v

    def deref(self):
        return self.v.deref() # can be nested

    def store_var(self, space, w_value):
        if isinstance(self.v, W_Reference):
            self.v.store_var(space, w_value)
        else:
            w_v = w_value.deref_for_store().copy(space)
            self.v = w_v

class W_Reference(W_Root):
    """ This is a reference got by &$stuff. It changes semantics of writing
    to a variable. Note that a reference to arrayitem is different
    """
    def __init__(self, w_value):
        assert not isinstance(w_value, W_Reference)
        self.w_value = w_value

    def deref(self):
        return self.w_value

class W_BaseContainerReference(W_Reference):
    pass

class W_ContainerIntReference(W_BaseContainerReference):
    def __init__(self, space, cont, index):
        self.cont = cont
        self.space = space
        self.index = index

    def deref(self):
        return self.cont.getitem(self.space, self.space.wrap(self.index)).deref()

    def store_var(self, space, w_value):
        w_value = w_value.deref_for_store().copy(space)
        return self.cont.setitem(space, space.wrap(self.index), w_value)

    def isset(self, space):
        return self.cont.isset_index(space, space.wrap(self.index))

class W_ContainerReference(W_BaseContainerReference):
    def __init__(self, space, cont, w_index):
        self.cont = cont
        self.space = space
        self.w_index = w_index

    def deref(self):
        return self.cont.getitem(self.space, self.w_index).deref()

    def store_var(self, space, w_value):
        w_value = w_value.deref_for_store().copy(space)
        return self.cont.setitem(space, self.w_index, w_value)

    def isset(self, space):
        return self.cont.isset_index(space, self.w_index)

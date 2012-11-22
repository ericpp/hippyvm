
from pypy.rlib.rerased import new_erasing_pair
from pypy.rlib import jit
from pypy.rlib.objectmodel import specialize
from hippy.objects.base import W_Root
from hippy.objects.reference import W_Reference, W_ContainerReference,\
     W_ContainerIntReference
from hippy.objects import arrayiter
from hippy.error import InterpreterError
from hippy.rpython.rdict import RDict

class BaseArrayStrategy(object):
    def force_write(self, w_obj):
        pass

class ArrayStratMixin(object):
    _mixin_ = True

    def create_iter(self, space, w_obj):
        if self.IteratorClass is None:
            res = arrayiter.EmptyArrayIterator(space)
        else:
            cp = w_obj.new_copy()
            res = self.IteratorClass(space, cp, self.unerase(w_obj.storage))
            w_obj.add_copy(cp, new_weakref(res))
        return res

    def mark_invalid(self, storage):
        pass

def decode_index(space, w_index):
    if w_index.tp != space.tp_int:
        if w_index.tp == space.tp_str:
            return int(space.str_w(w_index))
        raise ValueError
    return space.int_w(w_index)

class ListArrayStrategy(BaseArrayStrategy, ArrayStratMixin):
    erase, unerase = new_erasing_pair('list')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    IteratorClass = arrayiter.ListArrayIterator

    name = 'lobject'

    def getitem(self, space, storage, w_item):
        item = space.int_w(w_item)
        try:
            return self.unerase(storage)[item]
        except IndexError:
            raise InterpreterError("Undefined offset")

    def setitem(self, space, w_obj, w_item, w_value):
        # we can consider "contains references" as yet another storage, for
        # performance when we don't have to do that
        if w_item.tp != space.tp_int:
            w_obj.promote_to_hash(space)
            return w_obj.setitem(space, w_item, w_value)
        storage = self.unerase(w_obj.storage)
        item = space.int_w(w_item)
        if item == len(storage):
            storage.append(w_value)
            return
        try:
            cur = storage[item]
        except IndexError:
            w_obj.promote_to_hash(space)
            w_obj.setitem(space, w_item, w_value)
            return
        if type(cur) is W_Reference:
            cur.store_var(space, w_value)
        else:
            storage[item] = w_value

    def append(self, space, w_obj, w_item):
        self.unerase(w_obj.storage).append(w_item)

    def copy_into(self, w_parent, w_obj):
        w_obj.storage = self.erase(self.unerase(w_parent.storage)[:])
        return self

    def write_into_dict(self, space, storage, dct):
        for i, w_item in enumerate(self.unerase(storage)):
            w_key = space.wrap(i)
            dct[space.str_w(space.as_string(w_key))] = w_item

    def len(self, space, storage):
        return len(self.unerase(storage))

    def isset_index(self, space, storage, w_index):
        try:
            index = decode_index(space, w_index)
        except ValueError:
            return False
        return 0 <= index < len(self.unerase(storage))

class UnwrappedListArrayStrategy(ArrayStratMixin):
    _mixin_ = True

    def check_type(self, space, w_obj):
        raise NotImplementedError

    def unwrap(self, space, w_obj):
        raise NotImplementedError

    def getitem(self, space, storage, w_item):
        item = space.int_w(w_item)
        try:
            return space.wrap(self.unerase(storage)[item])
        except IndexError:
            raise InterpreterError("Undefined offset")

    def setitem(self, space, w_obj, w_item, w_value):
        if not self.check_type(space, w_value):
            self.rewrite_to_object_strat(space, w_obj)
            w_obj.setitem(space, w_item, w_value)
            return w_value
        if w_item.tp != space.tp_int:
            w_obj.promote_to_hash(space)
            return w_obj.setitem(space, w_item, w_value)
        item = space.int_w(w_item)
        storage = self.unerase(w_obj.storage)
        if item == len(storage):
            self.append(space, w_obj, w_value)
            return
        try:
            storage[item] = self.unwrap(space, w_value)
        except IndexError:
            w_obj.promote_to_hash(space)
            w_obj.setitem(space, w_item, w_value)

    def append(self, space, w_obj, w_value):
        if not self.check_type(space, w_value):
            self.rewrite_to_object_strat(space, w_obj)
            w_obj.strategy.append(space, w_obj, w_value)
        else:
            self.unerase(w_obj.storage).append(self.unwrap(space, w_value))

    def rewrite_to_object_strat(self, space, w_obj):
        new_strat = get_strategy(ListArrayStrategy)
        new_storage = new_strat.erase([space.wrap(i) for i in self.unerase(
            w_obj.storage)])
        w_obj.strategy = new_strat
        w_obj.storage = new_storage

    def copy_into(self, w_parent, w_obj):
        w_obj.storage = self.erase(self.unerase(w_parent.storage)[:])
        return self

    def write_into_dict(self, space, storage, dct):
        for i, item in enumerate(self.unerase(storage)):
            w_key = space.wrap(i)
            dct[space.str_w(space.as_string(w_key))] = space.wrap(item)

    def len(self, space, storage):
        return len(self.unerase(storage))

    def isset_index(self, space, storage, w_index):
        try:
            index = decode_index(space, w_index)
        except ValueError:
            return False
        return 0 <= index < len(self.unerase(storage))

class IntListArrayStrategy(BaseArrayStrategy, UnwrappedListArrayStrategy):
    erase, unerase = new_erasing_pair('intlist')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'lint'

    IteratorClass = arrayiter.IntArrayIterator

    def check_type(self, space, w_obj):
        return w_obj.tp == space.tp_int

    def unwrap(self, space, w_obj):
        return space.int_w(w_obj)

class FloatListArrayStrategy(BaseArrayStrategy, UnwrappedListArrayStrategy):
    erase, unerase = new_erasing_pair('floatlist')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'lfloat'

    IteratorClass = arrayiter.FloatArrayIterator

    def check_type(self, space, w_obj):
        return w_obj.tp == space.tp_float

    def unwrap(self, space, w_obj):
        return space.float_w(w_obj)

CUTOFF = -1 # XXX disble for now

class EmptyArrayStrategy(BaseArrayStrategy, ArrayStratMixin):
    erase, unerase = new_erasing_pair('empty')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'empty'

    IteratorClass = None

    def getitem(self, space, storage, w_item):
        raise InterpreterError("Undefined offset")

    def setitem(self, space, w_obj, w_item, w_value):
        if w_item.tp == space.tp_int:
            if space.int_w(w_item) == 0:
                return self.append(space, w_obj, w_value)
            # XXX we can improve and have unwrapped-but-with-bitmask, if we
            #     really want to. It's an open question
            if space.int_w(w_item) < CUTOFF:
                raise NotImplementedError # disabled
                size = space.int_w(w_item)
                new_strat = get_strategy(ListArrayStrategy)
                new_storage = new_strat.erase([space.w_Null for i in range(size)])
                w_obj.strategy = new_strat
                w_obj.storage = new_storage
                new_strat.setitem(space, w_obj, w_item, w_value)
                return # we should probably return something here
        w_obj.promote_to_hash(space)
        w_obj.strategy.setitem(space, w_obj, w_item, w_value)

    def append(self, space, w_obj, w_item):
        if w_item.tp == space.tp_int:
            new_strat = get_strategy(IntListArrayStrategy)
            new_storage = new_strat.erase([space.int_w(w_item)])
        elif w_item.tp == space.tp_float:
            new_strat = get_strategy(FloatListArrayStrategy)
            new_storage = new_strat.erase([space.float_w(w_item)])
        else:
            new_strat = get_strategy(ListArrayStrategy)
            new_storage = new_strat.erase([w_item])
        w_obj.strategy = new_strat
        w_obj.storage = new_storage

    def copy_into(self, w_parent, w_obj):
        w_obj.storage = self.erase(None)
        return self

    def write_into_dict(self, space, storage, dct):
        pass

    def len(self, space, storage):
        return 0

    def isset_index(self, space, storage, w_index):
        return False

class CopyArrayStrategy(BaseArrayStrategy, ArrayStratMixin):
    erase, unerase = new_erasing_pair('copy')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'copy'

    def getitem(self, space, storage, w_item):
        return self.unerase(storage).parent.getitem(space, w_item)

    def force_write(self, w_obj):
        cp = self.unerase(w_obj.storage)
        cp.remove()
        strat = cp.parent.strategy.copy_into(cp.parent, w_obj)
        w_obj.strategy = strat

    def len(self, space, storage):
        w_parent = self.unerase(storage).parent
        return w_parent.strategy.len(space, w_parent.storage)

    def create_iter(self, space, w_obj):
        w_parent = self.unerase(w_obj.storage).parent
        return w_parent.create_iter(space)

    def isset_index(self, space, storage, w_index):
        w_parent = self.unerase(storage).parent
        return w_parent.isset_index(space, w_index)

    def copy_into(self, w_parent, w_obj):
        w_parent = self.unerase(w_parent.storage).parent
        return w_parent.strategy.copy_into(w_parent, w_obj)

    def write_into_dict(self, space, storage, dct):
        w_parent = self.unerase(storage).parent
        w_parent.strategy.write_into_dict(space, w_parent.storage, dct)

    def mark_invalid(self, storage):
        cp = self.unerase(storage)
        cp.remove()

class HashStrategy(BaseArrayStrategy, ArrayStratMixin):
    erase, unerase = new_erasing_pair('hash')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'hash'

    IteratorClass = arrayiter.HashIterator

    def setitem(self, space, w_obj, w_item, w_value):
        dct = self.unerase(w_obj.storage)
        dct[space.str_w(space.as_string(w_item))] = w_value

    def getitem(self, space, storage, w_item):
        try:
            return self.unerase(storage)[space.str_w(space.as_string(w_item))]
        except KeyError:
            raise InterpreterError("Wrong offset")

    def append(self, space, w_obj, w_item):
        dct = self.unerase(w_obj.storage)
        dct[str(w_obj.next_idx)] = w_item
        w_obj.next_idx += 1

    def len(self, space, storage):
        return len(self.unerase(storage))

    def isset_index(self, space, storage, w_index):
        dct = self.unerase(storage)
        return space.str_w(space.as_string(w_index)) in dct

    def copy_into(self, w_parent, w_obj):
        dct = self.unerase(w_parent.storage)
        w_obj.storage = self.erase((dct.copy()))
        return self

def lookup(dct, key):
    dct = jit.hint(dct, promote=True)
    return _lookup_pure(dct, key)

@jit.elidable
def _lookup_pure(dct, key):
    return dct.get(key, -1)

class MapStrategy(BaseArrayStrategy, ArrayStratMixin):
    erase, unerase = new_erasing_pair('map')
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    name = 'map'

    IteratorClass = arrayiter.MapIterator

    def setitem(self, space, w_obj, w_item, w_value):
        dct, lst = self.unerase(w_obj.storage)
        dct = jit.hint(dct, promote=True)
        pos = lookup(dct, space.str_w(space.as_string(w_item)))
        if pos == -1:
            w_obj.promote_to_hash(space)
            w_obj.setitem(space, w_item, w_value)
        else:
            lst[pos] = w_value

    def getitem(self, space, storage, w_item):
        dct, lst = self.unerase(storage)
        pos = lookup(dct, space.str_w(space.as_string(w_item)))
        if pos == -1:
            raise InterpreterError("Wrong offset")
        else:
            return lst[pos]

    def append(self, space, w_obj, w_item):
        dct, lst = self.unerase(w_obj.storage)
        dct = jit.hint(dct, promote=True)
        lst[w_obj.next_idx] = w_item
        dct[str(w_obj.next_idx)] = len(lst)
        w_obj.next_idx += 1

    def len(self, space, storage):
        return len(self.unerase(storage)[0])

    def isset_index(self, space, storage, w_index):
        dct, lst = self.unerase(storage)
        pos = lookup(dct, space.str_w(space.as_string(w_index)))
        if pos == -1:
            return False
        return True

    def copy_into(self, w_parent, w_obj):
        dct, lst = self.unerase(w_parent.storage)
        new_dict = RDict(W_Root)
        for k, v in dct.iteritems():
            new_dict[k] = lst[v]
        strat = get_strategy(HashStrategy)
        w_obj.storage = strat.erase(new_dict)
        return strat

    def write_into_dict(self, space, storage, dct):
        d, lst = self.unerase(storage)
        for k, v in d.iteritems():
            dct[k] = lst[v]

def new_weakref(w_obj):
    return w_obj

class Copy(object):
    prev_link = None

    def __init__(self, next_link, parent):
        self.child = None
        self.parent = parent
        self.next_link = next_link
        if next_link is not None:
            next_link.prev_link = self

    def remove(self):
        next_link = self.next_link
        prev_link = self.prev_link
        if next_link is not None:
            next_link.prev_link = prev_link
        if prev_link is not None:
            prev_link.next_link = next_link
        else:
            self.parent.copies = next_link

class W_FakeIndex(W_Root):
    pass

class W_ArrayObject(W_Root):
    def __init__(self, strategy, storage, next_idx=0):
        self.strategy = strategy
        self.storage = storage
        self.copies = None
        self.next_idx = next_idx

    def mark_invalid(self):
        self.strategy.mark_invalid(self.storage)

    @jit.unroll_safe
    def new_copy(self):
        return Copy(self.copies, self)

    def add_copy(self, cp, child):
        cp.child = child
        self.copies = cp

    def copy(self, space):
        new_strat = get_strategy(CopyArrayStrategy)
        cp = self.new_copy()
        w_res = W_ArrayObject(new_strat, new_strat.erase(cp), self.next_idx)
        self.add_copy(cp, new_weakref(w_res))
        return w_res

    def itemreference(self, space, w_item):
        if w_item.tp == space.tp_int:
            return W_ContainerIntReference(space, self, space.int_w(w_item))
        return W_ContainerReference(space, self, w_item)

    def getitem(self, space, w_item):
        return self.strategy.getitem(space, self.storage, w_item)

    def _invalidate_copies(self):
        cp = self.copies
        while cp:
            if cp.child is not None:
                cp.child._force_write()
            cp = cp.next_link
        self.copies = None

    def _force_write(self):
        self.strategy.force_write(self)

    def force_write(self):
        self.strategy.force_write(self)
        if self.copies:
            self._invalidate_copies()

    def setitem(self, space, w_item, w_value):
        self.force_write()
        self.strategy.setitem(space, self, w_item, w_value)
        return w_value

    def append(self, space, w_item):
        self.force_write()
        self.strategy.append(space, self, w_item)
        return w_item

    def eq_w(self, space, w_other):
        return False

    def as_number(self, space):
        return space.wrap(1)

    def is_true(self, space):
        return True

    def promote_to_hash(self, space):
        new_strat = get_strategy(HashStrategy)
        dct = RDict(W_Root)#{}#r_dict(space.str_eq, space.str_hash)
        self.strategy.write_into_dict(space, self.storage, dct)
        self.strategy = new_strat
        self.storage = new_strat.erase(dct)

    def create_iter(self, space):
        return self.strategy.create_iter(space, self)

    def arraylen(self, space):
        return self.strategy.len(space, self.storage)

    def isset_index(self, space, w_index):
        return self.strategy.isset_index(space, self.storage, w_index)

    def as_string(self, space):
        return space.newstrconst("Array")

class W_ArrayConstant(W_ArrayObject):
    def copy(self, space):
        return W_ArrayObject(self.strategy, self.storage, self.next_idx)

@specialize.memo()
def get_strategy(cls):
    return cls()

UNROLL_CUTOFF = 10

def unroll_cond(space, lst_w):
    lgt = len(lst_w)
    return ((jit.isconstant(lgt) and lgt < UNROLL_CUTOFF) or
            jit.isvirtual(lst_w))

@jit.look_inside_iff(unroll_cond)
def new_array_from_list(space, lst_w):
    if not lst_w:
        # empty strategy
        strat = get_strategy(EmptyArrayStrategy)
        return W_ArrayConstant(strat, strat.erase(None))
    if lst_w[0].deref().tp == space.tp_int:
        for w_item in lst_w:
            if w_item.deref().tp != space.tp_int:
                break
        else:
            strat = get_strategy(IntListArrayStrategy)
            storage = strat.erase([space.int_w(w_obj) for w_obj in lst_w])
            return W_ArrayConstant(strat, storage)
    elif lst_w[0].deref().tp == space.tp_float:
        for w_item in lst_w:
            if w_item.deref().tp != space.tp_float:
                break
        else:
            strat = get_strategy(FloatListArrayStrategy)
            storage = strat.erase([space.float_w(w_obj) for w_obj in lst_w])
            return W_ArrayConstant(strat, storage)
    strat = get_strategy(ListArrayStrategy)
    # XXX copy the list here (?)
    return W_ArrayConstant(strat, strat.erase(lst_w))

@jit.look_inside_iff(unroll_cond)
def new_array_from_pairs(space, lst_w):
    strat = get_strategy(EmptyArrayStrategy)
    w_obj = W_ArrayObject(strat, strat.erase(None))
    for w_k, w_v in lst_w:
        space.setitem(w_obj, w_k, w_v)
    return w_obj


def new_globals_wrapper(space, dct):
    strat = get_strategy(HashStrategy)
    storage = strat.erase(dct)
    return W_ArrayObject(strat, storage)


def new_map_from_pairs(space, lst_w):
    lst = []
    dct = {}
    next_idx = 0
    for i, (k, v) in enumerate(lst_w):
        if k.tp == space.tp_fakeindex:
            lst.append(v)
            dct[str(next_idx)] = len(lst) - 1
            next_idx += 1
        else:
            if k.tp == space.tp_int:
                if space.int_w(k) > next_idx:
                    next_idx = space.int_w(k) + 1
            if not space.str_w(space.as_string(k)) in dct:
                lst.append(v)
                dct[space.str_w(space.as_string(k))] = len(lst) - 1
            else:
                idx = dct[space.str_w(space.as_string(k))]
                lst[idx] = v
                dct[space.str_w(space.as_string(k))] = idx
    strat = get_strategy(MapStrategy)
    w_arr = W_ArrayObject(strat, strat.erase((dct, lst)), next_idx)
    return w_arr

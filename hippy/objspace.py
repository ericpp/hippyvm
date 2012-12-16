
import os, operator
from pypy.rlib.objectmodel import specialize
from hippy.consts import BINOP_LIST
from hippy.objects.base import W_Root
from hippy.objects.reference import W_Reference, W_Cell
from hippy.objects.boolobject import W_BoolObject
from hippy.objects.base import W_NullObject
from hippy.objects.intobject import W_IntObject
from hippy.objects.floatobject import W_FloatObject
from hippy.objects.strobject import W_StringObject
from hippy.objects.arrayobject import W_ArrayObject, new_array_from_list


@specialize.memo()
def getspace():
    return ObjSpace()


class ExecutionContext(object):
    def __init__(self):
        self.interpreter = None

    def writestr(self, str):
        os.write(1, str)


class ObjSpaceWithIter(object):
    def __init__(self, space, w_arr):
        self.iter = space.create_iter(w_arr)

    def __enter__(self):
        return self.iter

    def __exit__(self, exception_type, exception_val, trace):
        self.iter.mark_invalid()


class ObjSpace(object):
    """ This implements all the operations on the object. Since this is
    prebuilt, it should not contain any state
    """
    (tp_int, tp_float, tp_str, tp_array, tp_null, tp_bool) = range(6)

    # in the same order as the types above
    TYPENAMES = ["integer", "double", "string", "array",
                 "NULL", "boolean"]

    def __init__(self):
        self.w_True = W_BoolObject(True)
        self.w_False = W_BoolObject(False)
        self.w_Null = W_NullObject()
        self.ec = ExecutionContext()

    def getcommontype(self, w_left, w_right):
        tpleft = self.deref(w_left).tp
        tpright = self.deref(w_right).tp
        if tpleft == tpright:
            return tpleft
        if tpleft == self.tp_float or tpright == self.tp_float:
            return self.tp_float
        raise NotImplementedError

    def int_w(self, w_obj):
        return w_obj.deref().int_w(self)

    def is_w(self, w_a, w_b):
        return w_a.tp == w_b.tp and w_a.eq_w(self, w_b)

    def is_valid_number(self, w_obj):
        return w_obj.deref().is_valid_number(self)

    def float_w(self, w_obj):
        return w_obj.deref().float_w(self)

    def deref(self, w_obj):
        return w_obj.deref()

    def is_true(self, w_obj):
        return w_obj.deref().is_true(self)

    def newint(self, v):
        return W_IntObject(v)

    def newfloat(self, v):
        return W_FloatObject(v)

    def newbool(self, v):
        if v:
            return self.w_True
        return self.w_False

    @specialize.argtype(1)
    def newstr(self, v):
        if isinstance(v, str):
            return W_StringObject.newconststr(v)
        return W_StringObject.newliststr(v)

    newstrconst = newstr

    def str_w(self, w_v):
        return self.as_string(w_v).str_w(self)

    def as_string(self, w_v):
        return w_v.deref().as_string(self)

    def as_number(self, w_v):
        return w_v.deref().as_number(self)

    def uplus(self, w_v):
        return w_v.deref().uplus(self)

    def uminus(self, w_v):
        return w_v.deref().uminus(self)

    def uplusplus(self, w_v):
        return w_v.deref().uplusplus(self)

    def uminusminus(self, w_v):
        return w_v.deref().uminusminus(self)

    def inplace_concat(self, w_v, w_value):
        w_v = self.as_string(w_v)
        w_v.inplace_concat(self, w_value)
        return w_v

    def getitem(self, w_obj, w_item):
        return w_obj.deref().getitem(self, w_item.deref())

    def itemreference(self, w_obj, w_item):
        return w_obj.deref().itemreference(self, w_item.deref())

    def setitem(self, w_obj, w_item, w_value):
        return w_obj.deref().setitem(self, w_item.deref(),
                                     w_value.deref_for_store())

    def concat(self, w_left, w_right):
        return self.as_string(w_left).strconcat(self, self.as_string(w_right))

    def strlen(self, w_obj):
        return w_obj.deref().strlen()

    def arraylen(self, w_obj):
        return w_obj.deref().arraylen(self)

    def slice(self, w_arr, start, end, keep_keys):
        res_arr = []
        idx = 0
        if start < 0:
            start = self.arraylen(w_arr) + start
            if end > 0:
                end = start + end
        if end < 0:
            end = start + (self.arraylen(w_arr) + end)
        if self.arraylen(w_arr) == 0:
            return self.new_array_from_list([])
        if start > self.arraylen(w_arr):
            return self.new_array_from_list([])
        with self.iter(w_arr) as itr:
            while not itr.done():
                key, value = itr.next_item(self)
                if start <= idx < end:
                    if keep_keys:
                        res_arr.append((key, value))
                    else:
                        res_arr.append((self.newint(idx), value))
                idx += 1
        if keep_keys:
            return self.new_array_from_pairs(res_arr)
        return self.new_array_from_list([v for _, v in res_arr])

    def append(self, w_arr, w_val):
        w_arr.deref().append(self, w_val.deref_for_store())

    def getchar(self, w_obj):
        # get first character
        return w_obj.deref().as_string(self).getchar(self)

    @specialize.argtype(1)
    def wrap(self, v):
        if isinstance(v, bool):
            return self.newbool(v)
        elif isinstance(v, int):
            return self.newint(v)
        elif isinstance(v, float):
            return self.newfloat(v)
        elif isinstance(v, W_Root):
            return v
        else:
            raise NotImplementedError

    def _freeze_(self):
        return True

    def new_array_from_list(self, lst_w):
        return new_array_from_list(self, lst_w)

    def new_array_from_pairs(self, lst_w):
        return new_array_from_pairs(self, lst_w)

    def new_map_from_pairs(self, lst_w):
        return new_map_from_pairs(self, lst_w)

    def iter(self, w_arr):
        return ObjSpaceWithIter(self, w_arr)

    def create_iter(self, w_arr):
        w_arr = w_arr.deref()
        return w_arr.create_iter(self)

    def str_hash(self, w_obj):
        return w_obj.deref().hash()

    def str_eq(self, w_one, w_two):
        w_one = w_one.deref()
        w_two = w_two.deref()
        if w_one.tp == w_two.tp:
            return w_one.eq_w(self, w_two)
        return self.as_string(w_one).eq_w(self, self.as_string(w_two))

    def get_globals_wrapper(self):
        return self.ec.interpreter.globals_wrapper

    def as_array(self, w_obj):
        w_obj = w_obj.deref()
        if w_obj.tp != self.tp_array:
            if w_obj is self.w_Null:
                return self.new_array_from_list([])
            w_obj = self.new_array_from_list([w_obj])
        assert isinstance(w_obj, W_ArrayObject)
        return w_obj


def _new_binop(name):
    def func(self, w_left, w_right):
        w_left = w_left.deref()
        w_right = w_right.deref()
        if name == 'eq' or name == 'ne':
            # make compare and eq direct if tp matches, otherwise cast
            # to number for comparison
            if w_left.tp == w_right.tp:
                return getattr(w_left, name)(self, w_right)
            if w_left.tp == self.tp_null or w_right.tp == self.tp_null:
                return self.wrap(getattr(operator, name)(self.is_true(w_left),
                                                         self.is_true(w_right)))
        w_left = w_left.as_number(self)
        w_right = w_right.as_number(self)
        tp = self.getcommontype(w_left, w_right)
        return getattr(w_left.coerce(self, tp), name)(self,
            w_right.coerce(self, tp))
    func.func_name = name
    return func

for _name in BINOP_LIST:
    setattr(ObjSpace, _name, _new_binop(_name))

W_FloatObject.tp = ObjSpace.tp_float
W_BoolObject.tp = ObjSpace.tp_bool
W_IntObject.tp = ObjSpace.tp_int
W_StringObject.tp = ObjSpace.tp_str
W_ArrayObject.tp = ObjSpace.tp_array
W_NullObject.tp = ObjSpace.tp_null

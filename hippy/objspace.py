
import os, operator
from pypy.rlib.objectmodel import specialize
from hippy.consts import BINOP_LIST
from hippy.objects.base import W_Root
from hippy.objects.reference import W_Reference
from hippy.objects.boolobject import W_BoolObject
from hippy.objects.nullobject import W_NullObject
from hippy.objects.intobject import W_IntObject
from hippy.objects.floatobject import W_FloatObject
from hippy.objects.strobject import W_StringObject, SINGLE_CHAR_STRING
from hippy.objects.arrayobject import W_ArrayObject
from hippy.rpython.rdict import RDict


@specialize.memo()
def getspace():
    return ObjSpace()


class ExecutionContext(object):

    errors = []

    def __init__(self):
        self.interpreter = None
        self.global_frame = None

    def notice(self, msg):
        self.interpreter.logger.notice(self.interpreter, msg)

    def warn(self, msg):
        self.interpreter.logger.warn(self.interpreter, msg)

    def hippy_warn(self, msg):
        self.interpreter.logger.hippy_warn(self.interpreter, msg)

    def fatal(self, msg):
        # This one is supposed to raise FatalError.  If needed, in the
        # caller, write "raise space.ec.fatal(...)" to make it clear that
        # it cannot return (useful for RPython)
        self.interpreter.logger.fatal(self.interpreter, msg)        

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
        w_a = w_a.deref()
        w_b = w_b.deref()
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

    def setitem(self, w_obj, w_item, w_value):
        # returns the w_newobj, which is the new version of w_obj
        return w_obj.deref().setitem(self, w_item.deref(), w_value.deref())

    def setitem2(self, w_obj, w_item, w_value):
        # returns a pair (w_newobj, w_newvalue)
        w_obj = w_obj.deref()
        if w_obj.tp == self.tp_str:
            c = self.getchar(w_value)
            w_value = SINGLE_CHAR_STRING[ord(c)]
        else:
            w_value = w_value.deref()
        w_newobj = w_obj.setitem(self, w_item.deref(), w_value)
        return (w_newobj, w_value)
    setitem2._always_inline_ = True     # returns a tuple

    def setitem_ref(self, w_obj, w_item, w_ref):
        return w_obj.deref().setitem_ref(self, w_item.deref(), w_ref)

    def unsetitem(self, w_obj, w_item):
        return w_obj.deref().unsetitem(self, w_item.deref())

    def concat(self, w_left, w_right):
        return self.as_string(w_left).strconcat(self, self.as_string(w_right))

    def strlen(self, w_obj):
        return w_obj.deref().strlen()

    def arraylen(self, w_obj):
        return w_obj.deref().arraylen()

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

    def append_index(self, w_arr):
        return w_arr.deref().append_index(self)

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
        return W_ArrayObject.new_array_from_list(self, lst_w)

    def new_array_from_rdict(self, rdict_w):
        # 'dict_w' is a RDict that contains {"rpython string": W_Objects}
        return W_ArrayObject.new_array_from_rdict(self, rdict_w)

    def new_array_from_dict(self, dict_w):
        "NOT_RPYTHON: for tests only (gets a random ordering)"
        rdict_w = RDict(W_Root)
        for key, w_value in dict_w.items():
            rdict_w[key] = w_value
        return W_ArrayObject.new_array_from_rdict(self, rdict_w)

    def new_array_from_pairs(self, pairs_ww):
        return W_ArrayObject.new_array_from_pairs(self, pairs_ww)

    new_map_from_pairs = new_array_from_pairs   # for now

    def iter(self, w_arr):
        return ObjSpaceWithIter(self, w_arr)

    def create_iter(self, w_arr):
        w_arr = w_arr.deref()
        return w_arr.create_iter(self)

    def create_iter_ref(self, w_arr_ref):
        from hippy.objects.arrayiter import W_ArrayIteratorByReference
        if not isinstance(w_arr_ref, W_Reference):
            raise self.ec.fatal("foreach(1 as &2): argument 1 must be a "
                                "variable")
        return W_ArrayIteratorByReference(self, w_arr_ref)

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

    def abs(self, w_obj):
        return w_obj.abs(self)


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

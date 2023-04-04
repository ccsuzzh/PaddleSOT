import paddle
from ..proxy_tensor import paddle_api_wrapper, ProxyTensorContext
from ..utils import log

CONVERT_SKIP_NAMES = (
    "convert_one",
    "convert_multi",
    "set_eval_frame",
)

def convert_one(obj):
    # use contextmanager to change frame callback will lead to err
    if obj is paddle.fluid.core.set_eval_frame:
        return obj
    old_cb = paddle.fluid.core.set_eval_frame(None)
    log(10, "[convert] " + f"target: {obj}    ")
    if callable(obj):
        log(10, "found a callable object\n")
        obj = convert_callable(obj)
    elif isinstance(obj, paddle.Tensor):
        log(10, "found a tensor\n")
        obj = convert_tensor(obj)
    log(10, "nothing happend\n")
    paddle.fluid.core.set_eval_frame(old_cb)
    return obj

def convert_multi(args):
    old_cb = paddle.fluid.core.set_eval_frame(None)
    retval = []
    for obj in args:
        retval.append(convert_one(obj))
    retval = tuple(retval)
    paddle.fluid.core.set_eval_frame(old_cb)
    return retval
  
def convert_callable(func):
    if isinstance(func, type):
        return func
    return paddle_api_wrapper(func)

def convert_tensor(tensor):
    return ProxyTensorContext().from_tensor(tensor)


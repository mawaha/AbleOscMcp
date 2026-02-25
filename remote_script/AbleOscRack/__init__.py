try:
    from .manager import Manager
except ImportError:
    pass


def create_instance(c_instance):
    return Manager(c_instance)

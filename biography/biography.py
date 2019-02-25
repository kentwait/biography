from functools import wraps
import sys
import inspect
import warnings

from .entries import *


__all__ = ['Reporter']


class PatchedModule:
    pass


class PatchedClass:
    def __init__(self, builtin, reporter, module=None):
        self._builtin = builtin
        self._reporter = reporter
        self._module = module
    
    def __getattribute__(self, name):
        if name in ['_builtin', '_reporter', '_module']:
            return object.__getattribute__(self, name)
        else:
            func = self._builtin.__getattribute__(name)    
            if not name.startswith('_') and callable(func):
                return self._reporter.watch_method(
                    func, module=self._module)
            return func

    def __call__(self, *args, **kwargs):
        res = PatchedInstance(self._builtin(*args, **kwargs), self._reporter,
                      module=self._module)
        if sys._getframe().f_back.f_code.co_name in self._reporter.frames:
            entry = Create(self._builtin, args=args, kwargs=kwargs,
                module=self._module)
            self._reporter.entries.append(entry)
        self._reporter.tracked.append(self._builtin)
        return res

    def __repr__(self):
        return self._builtin.__repr__()


class PatchedInstance:
    def __init__(self, instance, reporter, module=None):
        self._builtin = instance
        self._reporter = reporter
        self._module = module
    
    def __getattribute__(self, name):
        if name in ['_builtin', '_reporter', '_module']:
            return object.__getattribute__(self, name)
        else:
            func = self._builtin.__getattribute__(name)    
            if not name.startswith('_') and callable(func):
                return self._reporter.watch_method(
                    func, module=self._module)
            return func

    def __repr__(self):
        return self._builtin.__repr__()


class Reporter:
    def __init__(self):
        self.entries = []
        self.frames = ['<module>']
        self.tracked = []

    def watch(self, x):
        if inspect.ismodule(x):
            return self.watch_module(x)
        elif inspect.isclass(x):
            return self.watch_class(x)
        elif inspect.ismethod(x):
            return self.watch_method(x)
        elif inspect.isfunction(x):
            return self.watch_function(x)
        elif inspect.isbuiltin(x):
            return self.watch_builtin(x)
        raise ValueError('cannot watch unknown entity')
    
    def forget(self, x):
        pass

    def watch_function(self, func, module=None, op=Operation):
        @wraps(func)
        def func_wrapper(*func_args, **func_kwargs):
            out = func(*func_args, **func_kwargs)
            # print(sys._getframe().f_back.f_code.co_name)
            if sys._getframe().f_back.f_code.co_name in self.frames:
                entry = op(func, args=func_args, kwargs=func_kwargs,
                                  module=module)
                self.entries.append(entry)
            self.tracked.append(func)
            return out
        return func_wrapper

    def watch_method(self, func, module=None, op=Method):
        return self.watch_func(func, module=module, op=op)

    def watch_class(self, cls=None, module=None):
        return self.watch_builtin(cls, module=module)

    def watch_builtin(self, cls, module=None):
        out = PatchedClass(cls, self, module=module)
        self.tracked.append(cls)
        return out

    def watch_instance(self, instance, module=None):
        out = PatchedInstance(instance, self, module=module)
        self.tracked.append(instance)
        return out

    def watch_module(self, module):
        patched = PatchedModule()
        for attr, func in inspect.getmembers(module):
            if not attr.startswith('_'):
                if inspect.isclass(func):
                    setattr(patched, attr,
                            self.watch_class(func, module=module.__name__))
                elif inspect.isfunction(func):
                    setattr(patched, attr,
                            self.watch_function(func, module=module.__name__))
                elif inspect.isbuiltin(func):
                    setattr(patched, attr,
                            self.watch_builtin(func, module=module.__name__))
                else:
                    setattr(patched, attr, func)
            else:
                try:
                    setattr(patched, attr, func)
                except (TypeError, AttributeError) as e:
                    pass
        patched.__wrapped__ = module
        self.tracked.append(module)
        return patched

    def include_frame(self, name):
        self.frames.append(name)

    def add_comment(self, comment):
        self.entries.append(Comment(comment))

    def to_json(self, path=None):
        return '[{}]'.format(
            ', '.join([i.to_json() for i in self.entries])
        )

    def to_markdown(self, path=None):
        return '\n'.join([i.to_markdown() for i in self.entries])

    def to_string(self, str_formatter=None, strftime='%m/%d/%Y %H:%M:%S'):
        return '\n'.join([
            i.to_string(str_formatter=str_formatter, strftime=strftime)
            for i in self.entries
        ])

    def to_toml(self, path=None):
        return '\n'.join([i.to_toml() for i in self.entries])

    def to_csv(self, path=None, sep='\t'):
        return '\n'.join([i.to_csv(sep=sep) for i in self.entries])

    def __str__(self):
        return '\n'.join([str(item) for item in self.entries])

    def __repr__(self):
        return repr(self.entries)

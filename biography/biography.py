from functools import wraps
from datetime import datetime
import sys
import inspect
import json
import warnings


__all__ = ['Biography']


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
                return self._reporter.watch_function(
                    func, module=self._module)
            return func

    def __call__(self, *args, **kwargs):
        res = PatchedClass(self._builtin(*args, **kwargs), self._reporter,
                      module=self._module)
        if sys._getframe().f_back.f_code.co_name in self._reporter.frames:
            entry = Operation(self._builtin, args=args, kwargs=kwargs,
                module=self._module)
            self._reporter.entries.append(entry)
        self._reporter.tracked.append(self._builtin)
        return res

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

    def watch_function(self, func, module=None):
        @wraps(func)
        def func_wrapper(*func_args, **func_kwargs):
            out = func(*func_args, **func_kwargs)
            # print(sys._getframe().f_back.f_code.co_name)
            if sys._getframe().f_back.f_code.co_name in self.frames:
                entry = Operation(func, args=func_args, kwargs=func_kwargs,
                                  module=module)
                self.entries.append(entry)
            self.tracked.append(func)
            return out
        return func_wrapper

    def watch_method(self, func, module=None):
        return self.watch_funct(func, module=module)

    def watch_class(self, cls=None, module=None):
        return self.watch_builtin(cls, module=module)

    def watch_builtin(self, cls, module=None):
        out = PatchedClass(cls, self, module=module)
        self.tracked.append(cls)
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


class Operation:
    def __init__(self, operation, args=None, kwargs=None,
                 str_formatter=None, module=None):
        self.operation = operation.__qualname__
        if module:
            self.operation = '.'.join([module, self.operation])
        # IDEA: store obj instead of repr, could allow possibility of undo?
        self.args = [repr(arg) for arg in args] if args else []
        if operation.__name__ != operation.__qualname__ and \
            '<locals>' not in operation.__qualname__:
            self.args = self.args[1:]
        self.kwargs = {key: repr(kwarg) for key, kwarg in kwargs.items()} \
            if kwargs else dict()
        self.datetime = datetime.now()
        self._threshold_args = 3
        self._threshold_kwargs = 2
        self.str_formatter = str_formatter

    def to_json(self, path=None):
        return json.dumps(
            {'Operation': 
                {
                    'datetime': self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                    'operation': self.operation,
                    'args': self.args,
                    'kwargs': self.kwargs,
                }
            }
        )

    def to_markdown(self, path=None):
        params = ''
        if len(self.args) > 0:
            params += ', '.join(self.args)
        if len(self.kwargs) > 0:
            params += ', ' + ', '.join(self.kwargs)
        return ('## {op} operation\n'
                '  * date and time - {dt}\n'
                '  * statement - `{op}({params})`\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   op=self.operation,
                   params=params,
                ))

    def to_string(self, str_formatter=None, strftime='%m/%d/%Y %H:%M:%S'):
        if str_formatter:
            return str_formatter(
                operation=self.operation,
                args=self.args,
                kwargs=self.kwargs,
                datetime=self.datetime.strftime(strftime),
            )
        if self.str_formatter:
            return self.str_formatter(
                operation=self.operation,
                args=self.args,
                kwargs=self.kwargs,
                datetime=self.datetime,
            )
        args = [v for i, v in enumerate(self.args)
                if i < self._threshold_args]
        if len(self.args) > self._threshold_args:
            args += ['...']
        kwargs = ['{k}={v}'.format(k=kv[0], v=kv[1]) 
                for i, kv in enumerate(self.kwargs.items())
                if i < self._threshold_args]
        if len(self.kwargs) > self._threshold_kwargs:
            kwargs += ['...']
        params = ''
        if len(args) > 0:
            params += ', '.join(args)
        if len(kwargs) > 0:
            params += ', ' + ', '.join(kwargs)
        return 'Operation {dt} {op}({params})'.format(
            dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            op=self.operation,
            params=params,
        )

    def to_toml(self, path=None):
        return ('[Operation]\n'
                'datetime = {dt}\n'
                'operation = \'{op}\'\n'
                'args = \'{args}\'\n'
                'kwargs = \'{kwargs}\'\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   op=self.operation,
                   args=self.args,
                   kwargs=self.kwargs,
               ))

    def to_csv(self, path=None, sep='\t'):
        return sep.join([
            'Operation',
            self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            self.operation,
            str(self.args),
            str(self.kwargs),
        ])

    def __str__(self):
        return self.to_string()

    def __repr__(self):
        return '<{clsname} datetime={dt} statement={op}({params})>'.format(
            clsname=self.__class__.__name__,
            dt=self.datetime.strftime('%m/%d/%YT%H:%M:%S'),
            op=self.operation,
            params='...' if len(self.args) > 0 or len(self.kwargs) > 0 else ''
        )

class Comment:
    def __init__(self, comment, str_formatter=None):
        self.comment = comment
        self.datetime = datetime.now()
        self.str_formatter = str_formatter

    def to_json(self, path=None):
        return json.dumps(
            {'Comment': 
                {
                    'datetime': self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                    'comment': self.comment,
                }
            }
        )

    def to_markdown(self, path=None):
        return ('## Comment\n'
                '  * date and time - {dt}\n'
                '  * comment - {comment}\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   comment=self.comment,
                ))

    def to_string(self, str_formatter, strftime='%m/%d/%Y %H:%M:%S'):
        if str_formatter:
            return str_formatter(
                comment=self.comment,
                datetime=self.datetime.strftime(strftime),
            )
        if self.str_formatter:
            return self.str_formatter(
                comment=self.comment,
                datetime=self.datetime.strftime(strftime),
            )
        return 'Comment {dt} {comment}'.format(
            dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            comment=self.comment,
        )

    def to_toml(self, path=None):
        return ('[Comment]\n'
                'datetime = {dt}\n'
                'comment = {comment}\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   comment=self.comment,
                ))

    def to_csv(self, path=None, sep='\t'):
        return sep.join([
            'Comment',
            self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            self.comment,
        ])

    def __str__(self):
        if self.str_formatter:
            return self.str_formatter(self.comment, self.datetime)
        return 'Comment {dt} "{msg}"'.format(
            dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            msg=self.comment,
        )

    def __repr__(self):
        return '<{clsname} datetime={dt} comment="{msg}">'.format(
            clsname=self.__class__.__name__,
            dt=self.datetime.strftime('%m/%d/%YT%H:%M:%S'),
            msg=self.comment,
        )

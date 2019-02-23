from functools import wraps
from datetime import datetime
import sys
import inspect
import json


__all__ = ['Biography']


class Biography:
    def __init__(self):
        self.entries = []
        self.frames = ['<module>']
        self.included = []

    # Add ability to monkey-patch other functions
    def include(self, func, module=None):
        if inspect.ismodule(func):
            self.included.append(func)
            for name, f in inspect.getmembers(func):
                try:
                    if inspect.isfunction(f) and not f.__name__.startswith('_'):
                        setattr(func, name, self.__call__(f, module=func.__name__))
                except Exception as e:
                    # TODO: raise warning
                    pass

                try:
                    if inspect.isclass(f) and not f.__name__.startswith('_'):
                        # setattr(func, name, self.__call__(f, module=func.__name__))
                        self.include(f, module=func.__name__)
                except Exception as e:
                    # TODO: raise warning
                    pass

        elif inspect.isclass(func):
            self.included.append(func)
            setattr(func, '__init__', self.__call__(func.__init__, module=func.__name__))
            if not func.__name__.startswith('_'):
                for name, f in inspect.getmembers(func):
                    try:
                        if inspect.isfunction(f) and not f.__name__.startswith('_'):
                            setattr(func, name, self.__call__(f, module=module))
                    except Exception as e:
                        # TODO: raise warning
                        pass

    def exclude(self, func):
        if inspect.ismodule(func) and func in self.included:
            for name, f in inspect.getmembers(func):
                if inspect.isfunction(f) and not f.__name__.startswith('_'):
                    while hasattr(f, '__biography_wrapped__'):
                        setattr(func, name, f.__biography_wrapped__)
                        f = getattr(func, name)
                elif inspect.isclass(f) and not f.__name__.startswith('_'):
                        self.exclude(f)
            self.included.remove(func)

        elif inspect.isclass(func) and func in self.included:
            if not func.__name__.startswith('_'):
                while hasattr(func.__init__, '__biography_wrapped__'):
                    setattr(func, '__init__', func.__init__.__biography_wrapped__)
                for name, f in inspect.getmembers(func):
                    if inspect.isfunction(f) and not f.__name__.startswith('_'):
                        while hasattr(f, '__biography_wrapped__'):
                            setattr(func, name, f.__biography_wrapped__)
                            f = getattr(func, name)
            self.included.remove(func)            

    def wrap(func):
        if inspect.isfunction(func):
            return self.__call__(func)
        else:
            raise ValueError('not a function')

    def unwrap(func):
        if inspect.isfunction(func):
            while hasattr(func, '__biography_wrapped__'):
                func = func.__biography_wrapped__
                delattr(func, '__biography_wrapped__')
        else:
            raise ValueError('not a function')
        return func

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

    def __call__(self, lambda_func=None, module=None):
        if lambda_func:
            @wraps(lambda_func)
            def func_wrapper(*func_args, **func_kwargs):
                out = lambda_func(*func_args, **func_kwargs)
                if sys._getframe().f_back.f_code.co_name in self.frames:
                    entry = Operation(lambda_func, args=func_args, module=module)
                    self.entries.append(entry)
                return out
            wrapped = func_wrapper
            wrapped.__biography_wrapped__ = lambda_func
            return wrapped

        def decorator(func):
            @wraps(func)
            def func_wrapper(*func_args, **func_kwargs):
                out = func(*func_args, **func_kwargs)
                if sys._getframe().f_back.f_code.co_name in self.frames:
                    entry = Operation(func, args=func_args, kwargs=func_kwargs)
                    self.entries.append(entry)
                return out
            wrapped = func_wrapper
            wrapped.__biography_wrapped__ = func
            return wrapped
        return decorator

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
            dt=self.datetime.strftime('%m/%d/%Y|%H:%M:%S'),
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
            dt=self.datetime.strftime('%m/%d/%Y|%H:%M:%S'),
            msg=self.comment,
        )

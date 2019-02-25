import json
from datetime import datetime


__all__ = [
    'Operation', 'Create', 'Method', 
    'Comment'
]


class Operation:
    def __init__(self, operation, args=None, kwargs=None,
                 str_formatter=None, module=None):
        self.operation = operation.__qualname__  # BUG: fails on some objects like pandas.core.indexing._iLocIndexer
        self.optype = 'operation'
        if module:
            self.operation = '.'.join([module, self.operation])
        # IDEA: store obj instead of repr, could allow possibility of undo?
        self.args = [repr(arg).replace('\n', ' ') for arg in args] \
            if args else []
        if operation.__name__ != operation.__qualname__ and \
            '<locals>' not in operation.__qualname__:
            self.args = self.args[1:]
        self.kwargs = {key: repr(kwarg).replace('\n', ' ') 
                       for key, kwarg in kwargs.items()} \
            if kwargs else dict()
        self.datetime = datetime.now()
        self._threshold_args = 3
        self._threshold_kwargs = 2
        self.str_formatter = str_formatter

    def to_json(self, path=None):
        return json.dumps(
            {self.optype: 
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
        return ('## {optype} {op}\n'
                '  * date and time - {dt}\n'
                '  * statement - `{op}({params})`\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   op=self.operation,
                   optype=self.optype,
                   params=params,
                ))

    def to_string(self, str_formatter=None, strftime='%m/%d/%Y %H:%M:%S'):
        if str_formatter:
            return str_formatter(
                operation=self.operation,
                optype=self.optype,
                args=self.args,
                kwargs=self.kwargs,
                datetime=self.datetime.strftime(strftime),
            )
        if self.str_formatter:
            return self.str_formatter(
                operation=self.operation,
                optype=self.optype,
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
        return '{optype} {dt} {op}({params})'.format(
            dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
            optype=self.optype,
            op=self.operation,
            params=params,
        )

    def to_toml(self, path=None):
        return ('[{optype}]\n'
                'datetime = {dt}\n'
                'operation = \'{op}\'\n'
                'args = \'{args}\'\n'
                'kwargs = \'{kwargs}\'\n'.format(
                   dt=self.datetime.strftime('%m/%d/%Y %H:%M:%S'),
                   op=self.operation,
                   optype=self.optype,
                   args=self.args,
                   kwargs=self.kwargs,
               ))

    def to_csv(self, path=None, sep='\t'):
        return sep.join([
            self.optype,
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


class Create(Operation):
    def __init__(self, operation, args=None, kwargs=None,
                 str_formatter=None, module=None):
        super().__init__(operation, args=args, kwargs=kwargs,
                         str_formatter=str_formatter, module=module)
        self.optype = 'create'


class Method(Operation):
    def __init__(self, operation, args=None, kwargs=None,
                 str_formatter=None, module=None):
        super().__init__(operation, args=args, kwargs=kwargs,
                         str_formatter=str_formatter, module=module)
        self.optype = 'method'


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

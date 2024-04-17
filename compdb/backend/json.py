from __future__ import print_function, unicode_literals, absolute_import

import json
import os
import re
import shlex

import compdb.utils

from compdb.models import (CompileCommand, CompilationDatabaseInterface)


class JSONCompilationDatabase(CompilationDatabaseInterface):
    def __init__(self, json_db_path):
        self.json_db_path = json_db_path
        self.__data = None

    @classmethod
    def probe_directory(cls, directory):
        """Automatically create a CompilationDatabase from build directory."""
        db_path = os.path.join(directory, 'compile_commands.json')
        if os.path.exists(db_path):
            return cls(db_path)
        return super(JSONCompilationDatabase, cls).probe_directory(directory)

    def get_compile_commands(self, filepath):
        filepath = compdb.utils.logical_abspath(filepath)
        for elem in self._data:
            if os.path.normpath(os.path.join(elem['directory'],
                                             elem['file'])) == filepath:
                yield self._dict_to_compile_command(elem)

    def get_all_files(self):
        for entry in self._data:
            yield os.path.normpath(
                os.path.join(entry['directory'], entry['file']))

    def get_all_compile_commands(self):
        return map(self._dict_to_compile_command, self._data)

    @staticmethod
    def _dict_to_compile_command(d):
        if 'arguments' in d:
            arguments = d['arguments']
        else:
            # PERFORMANCE: I think shlex is inherently slow,
            # something performing better may be necessary
            arguments = shlex.split(d['command'],
                                    # XXX: os.name is "posix" on mysys2/cygwin,
                                    # is that correct?
                                    posix=os.name == "posix")
            arguments = list(map(lambda x: x.replace(r'\\', '\\').replace(r'\"', '"'), arguments))
            output = d.get('output')
            if output:
                output = output.replace(r'\\', '\\')
        return CompileCommand(d['directory'].replace(r'\\', '\\'), d['file'].replace(r'\\', '\\'), arguments,
                              output)

    @property
    def _data(self):
        if self.__data is None:
            with open(self.json_db_path) as f:
                self.__data = json.load(f)
        return self.__data


def arguments_to_json(arguments):
    cmd_line = '"'
    for i, argument in enumerate(arguments):
        if i != 0:
            cmd_line += ' '
        cmd_line += argument.replace("\\", r"\\").replace('"', r'\"')
    return cmd_line + '"'


def str_to_json(s):
    return '"{}"'.format(s.replace("\\", r"\\").replace('"', r'\"'))


def compile_command_to_json(compile_command):
    output_str = ""
    if compile_command.output:
        output_str = ',\n  "output": {}'.format(
            str_to_json(compile_command.output))
    return r'''{{
  "directory": {},
  "command": {},
  "file": {}{}
}}'''.format(
        str_to_json(compile_command.directory),
        arguments_to_json(compile_command.arguments),
        str_to_json(compile_command.file), output_str)


class JSONCompileCommandSerializer(object):
    def __init__(self, fp):
        self.fp = fp
        self.__count = 0

    def __enter__(self):
        self.fp.write('[\n')
        return self

    def serialize(self, compile_command):
        if self.__count != 0:
            self.fp.write(',\n\n')
        self.fp.write(compile_command_to_json(compile_command))
        self.__count += 1

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.__count != 0:
            self.fp.write('\n')
        self.fp.write(']\n')


def compile_commands_to_json(compile_commands, fp):
    """
    Dump Json.

    Parameters
    ----------
    compile_commands : CompileCommand iterable
    fp
        A file-like object, JSON is written to this element.
    """
    with JSONCompileCommandSerializer(fp) as serializer:
        for compile_command in compile_commands:
            serializer.serialize(compile_command)

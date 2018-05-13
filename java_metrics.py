from antlr4 import *
import re

from antlr_java_parser.JavaLexer import JavaLexer
from antlr_java_parser.JavaParser import JavaParser
from antlr_java_parser.JavaParserListener import JavaParserListener


class ClassCountingListener(JavaParserListener):
    def __init__(self):
        self.count = 0

    def enterClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        self.count += 1


class MethodsCountingListener(JavaParserListener):
    def __init__(self, tokens_stream):
        self.count = 0
        self.tokens = tokens_stream
        self.blocks = {}
        self.__nested_in = []
        self.__in_method_counter = 0
        self.__current_method = None

    def enterClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        self.__nested_in.append(ctx.IDENTIFIER().getText())

    def exitClassDeclaration(self, ctx: JavaParser.ClassDeclarationContext):
        self.__nested_in.pop(-1)

    def enterMethodBody(self, ctx: JavaParser.MethodBodyContext):
        self.__in_method_counter += 1

    def exitMethodBody(self, ctx: JavaParser.MethodBodyContext):
        self.__in_method_counter -= 1

    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        if self.__in_method_counter == 0:
            method_declaration = self.tokens.getText(interval=(ctx.start.tokenIndex, ctx.stop.tokenIndex))
            method_signature = retrieve_signature(method_declaration)
            method_id = ".".join(self.__nested_in + [method_signature])
            self.blocks[method_id] = method_declaration.split("\n")
        self.count += 1


def retrieve_signature(first_line: str):
    try:
        # suposingly string of the following format will remain: name(parameters)
        tokens = re.findall(r"[\w_\d\[\]]+|[@(),<>&]|\.+", first_line)
        tokens = tokens[tokens.index('(') - 1: tokens.index(')') + 1]

        # concatenating varargs, arrays and complex types
        valid_tokens = []
        prev_token = ''
        for token in tokens:
            if token in ['[', ']', '.'] or prev_token == '.' or token == '...':
                valid_tokens[-1] += token
            else:
                valid_tokens.append(token)
            prev_token = token
        tokens = valid_tokens

        # erasing 'final' key words
        tokens = filter(lambda x: x != "final", tokens)

        # erasing annotations
        tokens_without_annotations = []
        prev_token = ""
        for token in tokens:
            if prev_token != "@" and token != "@":
                tokens_without_annotations.append(token)
            prev_token = token
        tokens = tokens_without_annotations

        # erasing templates
        tokens_without_templates = []
        balance = 0
        for token in tokens:
            if token == '<':
                balance += 1
            if balance == 0:
                tokens_without_templates.append(token)
            if token == '>':
                balance -= 1
        tokens = tokens_without_templates

        # leaving only name and types
        result_tokens = []
        prev_token = ''
        for token in tokens:
            if prev_token in ['', '(', ',', ')'] or token in ['', '(', ',', ')']:
                result_tokens.append(token)
            prev_token = token

        return "".join(result_tokens)
    except Exception as e:
        print("error on line:", tokens)
        print(e.__str__())
    return first_line.replace(" ", '')


class JavaFile:
    def __init__(self, lines):
        self.lines = [line.decode() for line in lines]
        code = "\n".join(self.lines)
        codeStream = InputStream(code)
        lexer = JavaLexer(codeStream)
        self.tokens_stream = CommonTokenStream(lexer)
        self.parser = JavaParser(self.tokens_stream)
        self.tree = self.parser.compilationUnit()

    def _walk_file(self, listener):
        ParseTreeWalker.DEFAULT.walk(listener, self.tree)
        return listener

    def count_classes(self):
        listener = self._walk_file(ClassCountingListener())
        return listener.count

    def count_methods(self):
        listener = self._walk_file(MethodsCountingListener(self.tokens_stream))
        return listener.count

    def eval_blocks(self):
        listener = self._walk_file(MethodsCountingListener(self.tokens_stream))
        return listener.blocks

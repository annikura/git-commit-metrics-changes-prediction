from antlr4 import *

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
            method_signature = self.retrieve_signature(method_declaration)
            method_id = ".".join(self.__nested_in + [method_signature])
            self.blocks[method_id] = method_declaration.split("\n   ")
        self.count += 1

    @staticmethod
    def retrieve_signature(first_line: str):
        closing_bracket_position = first_line.find(')')

        word = ""
        first_word_sym_position = -1
        splitted = True

        for i, s in enumerate(first_line):
            if s == '(':
                break
            if s.isalnum():
                if splitted:
                    word = ""
                    first_word_sym_position = i
                    splitted = False
                word += s
                continue
            splitted = True

        first_line = first_line[first_word_sym_position:closing_bracket_position + 1]
        template_balance = 0
        line_without_templates = ""

        for s in first_line:
            if s == '<':
                template_balance += 1
            if template_balance == 0:
                line_without_templates += s
            if s == '>':
                template_balance -= 1

        signature = ""
        in_type_parameters_list = False
        right_after_divider = False
        word_started = False

        for s in line_without_templates:
            if s in ['(', ')', ',']:
                if s == '(':
                    in_type_parameters_list = True
                if s == ')':
                    in_type_parameters_list = False
                right_after_divider = True
                word_started = False
                signature += s
                continue
            if not s.isalnum():
                if word_started:
                    word_started = False
                    right_after_divider = False
                continue
            if not in_type_parameters_list or right_after_divider:
                word_started = True
                signature += s

        signature.replace(' ', '')
        print(signature)
        return signature


class JavaFile:
    def __init__(self, lines):
        self.lines = lines
        code = "\n".join(lines)
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

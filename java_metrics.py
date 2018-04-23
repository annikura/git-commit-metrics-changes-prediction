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
    def __init__(self):
        self.count = 0
        self.blocks = {}
        self.__nested_in = []
        self.__last_opened = -1
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
            self.__last_opened = ctx.start.line
            self.__current_method = ".".join(self.__nested_in + [ctx.IDENTIFIER().getText()])
        self.count += 1

    def exitMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        if self.__in_method_counter == 0:
            assert self.__last_opened != -1
            assert self.__current_method is not None
            last_closed = ctx.methodBody().stop.line
            self.blocks[self.__current_method] = (self.__last_opened, last_closed)


class JavaFile:
    def __init__(self, lines):
        self.lines = lines
        code = "\n".join(lines)
        codeStream = InputStream(code)
        lexer = JavaLexer(codeStream)
        tokensStream = CommonTokenStream(lexer)
        self.parser = JavaParser(tokensStream)
        self.tree = self.parser.compilationUnit()

    def _walk_file(self, listener):
        ParseTreeWalker.DEFAULT.walk(listener, self.tree)
        return listener

    def count_classes(self):
        listener = self._walk_file(ClassCountingListener())
        return listener.count

    def count_methods(self):
        listener = self._walk_file(MethodsCountingListener())
        return listener.count

    def eval_blocks(self):
        listener = self._walk_file(MethodsCountingListener())
        result = {}
        for name in listener.blocks:
            s, f = listener.blocks[name]
            result[name] = self.lines[s - 1:f]
        return result

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

    def enterMethodDeclaration(self, ctx: JavaParser.MethodDeclarationContext):
        self.count += 1


class JavaFile:
    def __init__(self, lines):
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

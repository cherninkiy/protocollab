"""protocollab.expression — safe expression engine for protocol spec fields."""

from protocollab.expression.ast_nodes import (
    ASTNode,
    Attribute,
    BinOp,
    Literal,
    Name,
    Subscript,
    Ternary,
    UnaryOp,
)
from protocollab.expression.evaluator import ExpressionEvalError, evaluate
from protocollab.expression.lexer import ExpressionSyntaxError, Token, TokenKind, tokenize
from protocollab.expression.parser import Parser, parse_expr
from protocollab.expression.validator import ExprError, validate_expr

__all__ = [
    # AST nodes
    "ASTNode",
    "Literal",
    "Name",
    "Attribute",
    "Subscript",
    "UnaryOp",
    "BinOp",
    "Ternary",
    # Lexer
    "Token",
    "TokenKind",
    "tokenize",
    # Parser
    "Parser",
    "parse_expr",
    # Evaluator
    "evaluate",
    # Errors
    "ExpressionSyntaxError",
    "ExpressionEvalError",
    # Static validator
    "ExprError",
    "validate_expr",
]

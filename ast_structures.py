from dataclasses import dataclass
from typing import List, Any, Optional

class ASTNode:
    pass

@dataclass
class NumberLiteral(ASTNode):
    value: str

@dataclass
class StringLiteral(ASTNode):
    value: str

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class BinaryOperation(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode

@dataclass
class VariableDeclaration(ASTNode):
    var_type: str
    name: str
    value: Optional[ASTNode]

@dataclass
class Assignment(ASTNode):
    target: str
    value: ASTNode

@dataclass
class MethodCall(ASTNode):
    target: str
    args: List[ASTNode]

@dataclass
class Block(ASTNode):
    statements: List[ASTNode]

@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode
    body: Block

@dataclass
class MethodDeclaration(ASTNode):
    modifiers: List[str]
    return_type: str
    name: str
    params: List[str]
    body: Block

@dataclass
class ClassDeclaration(ASTNode):
    modifiers: List[str]
    name: str
    body: List[ASTNode]

@dataclass
class Program(ASTNode):
    statements: List[ASTNode]
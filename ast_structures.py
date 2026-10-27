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
class CharLiteral(ASTNode):
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
class ConstantDeclaration(ASTNode):
    var_type: str
    name: str
    value: ASTNode

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
class DoWhileStatement(ASTNode):
    body: Block
    condition: ASTNode

@dataclass
class ForStatement(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: Block

@dataclass
class IfStatement(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode]

@dataclass
class PackageDeclaration(ASTNode):
    name: str

@dataclass
class ImportDeclaration(ASTNode):
    path: str

@dataclass
class ReturnStatement(ASTNode):
    value: Optional[ASTNode]

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
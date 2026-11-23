from dataclasses import dataclass, field
from typing import List, Optional, Union


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
class BooleanLiteral(ASTNode):
    value: str


@dataclass
class Identifier(ASTNode):
    name: str


@dataclass
class ThisExpression(ASTNode):
    pass


@dataclass
class BinaryOperation(ASTNode):
    left: ASTNode
    operator: str
    right: ASTNode


@dataclass
class UnaryOperation(ASTNode):
    operator: str
    operand: ASTNode
    postfix: bool = False


@dataclass
class TernaryOperation(ASTNode):
    condition: ASTNode
    true_expr: ASTNode
    false_expr: ASTNode


@dataclass
class ArrayAccess(ASTNode):
    array: ASTNode
    index: ASTNode


@dataclass
class MemberAccess(ASTNode):
    target: ASTNode
    member: str


@dataclass
class ArrayInitializer(ASTNode):
    elements: List[ASTNode]


@dataclass
class ArrayCreation(ASTNode):
    element_type: str
    dimensions: List[Optional[ASTNode]]
    initializer: Optional[ArrayInitializer] = None


@dataclass
class ObjectCreation(ASTNode):
    class_name: str
    type_args: List[str]
    args: List[ASTNode]


@dataclass
class ExpressionStatement(ASTNode):
    expression: ASTNode


@dataclass
class VariableDeclaration(ASTNode):
    var_type: str
    name: str
    value: Optional[ASTNode]
    modifiers: List[str] = field(default_factory=list)


@dataclass
class ConstantDeclaration(ASTNode):
    var_type: str
    name: str
    value: ASTNode
    modifiers: List[str] = field(default_factory=list)


@dataclass
class Assignment(ASTNode):
    target: Union[str, ASTNode]
    value: ASTNode
    operator: str = '='


@dataclass
class MethodCall(ASTNode):
    target: Union[str, ASTNode]
    args: List[ASTNode]


@dataclass
class Block(ASTNode):
    statements: List[ASTNode]


@dataclass
class WhileStatement(ASTNode):
    condition: ASTNode
    body: ASTNode


@dataclass
class DoWhileStatement(ASTNode):
    body: ASTNode
    condition: ASTNode


@dataclass
class ForStatement(ASTNode):
    init: Optional[ASTNode]
    condition: Optional[ASTNode]
    update: Optional[ASTNode]
    body: ASTNode


@dataclass
class ForEachStatement(ASTNode):
    var_type: str
    var_name: str
    iterable: ASTNode
    body: ASTNode


@dataclass
class IfStatement(ASTNode):
    condition: ASTNode
    then_branch: ASTNode
    else_branch: Optional[ASTNode]


@dataclass
class SwitchCase(ASTNode):
    value: Optional[ASTNode]
    statements: List[ASTNode]


@dataclass
class SwitchStatement(ASTNode):
    expression: ASTNode
    cases: List[SwitchCase]


@dataclass
class BreakStatement(ASTNode):
    pass


@dataclass
class ContinueStatement(ASTNode):
    pass


@dataclass
class Parameter(ASTNode):
    var_type: str
    name: str


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
class ConstructorDeclaration(ASTNode):
    modifiers: List[str]
    name: str
    params: List[Parameter]
    body: Block


@dataclass
class MethodDeclaration(ASTNode):
    modifiers: List[str]
    return_type: str
    name: str
    params: List[Parameter]
    body: Block


@dataclass
class ClassDeclaration(ASTNode):
    modifiers: List[str]
    name: str
    body: List[ASTNode]


@dataclass
class Program(ASTNode):
    statements: List[ASTNode]
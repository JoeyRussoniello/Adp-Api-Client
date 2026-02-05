import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union


# AST NODE TYPES
class Expr:
    def to_odata(self) -> str:
        raise NotImplementedError
    
    def __and__(self, other: 'Expr') -> 'BinaryOp':
        return BinaryOp(self, 'and', other)
    
    def __or__(self, other: 'Expr') -> 'BinaryOp':
        return BinaryOp(self, 'or', other)

    def __invert__(self) -> 'UnaryOp':
        return UnaryOp('not', self)


@dataclass(frozen=True)
class Field(Expr):
    path: str

    # comparisons
    def eq(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "eq", literal(val))

    def ne(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "ne", literal(val))

    def gt(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "gt", literal(val))

    def ge(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "ge", literal(val))

    def lt(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "lt", literal(val))

    def le(self, val: Any) -> "BinaryOp":
        return BinaryOp(self, "le", literal(val))

    # string functions
    def contains(self, val: Any) -> "Func":
        return Func("contains", [self, literal(val)])

    def startswith(self, val: Any) -> "Func":
        return Func("startswith", [self, literal(val)])

    def endswith(self, val: Any) -> "Func":
        return Func("endswith", [self, literal(val)])

    # emulate IN as disjunction
    def isin(self, values: List[Any]) -> "Expr":
        if not values:
            # empty IN -> false; represent as (1 eq 0)
            return BinaryOp(Literal(1), "eq", Literal(0))
        expr = None
        for v in values:
            clause = BinaryOp(self, "eq", literal(v))
            expr = clause if expr is None else BinaryOp(expr, "or", clause)
        return expr

    def to_odata(self) -> str:
        return self.path  # path like worker.person.legalName.givenName


@dataclass(frozen=True)
class Literal(Expr):
    value: Any

    def to_odata(self) -> str:
        v = self.value
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, (int, float)):
            return str(v)
        # Default: string; escape single quotes by doubling them
        s = str(v).replace("'", "''")
        return f"'{s}'"

def literal(v: Any) -> Literal:
    return Literal(v)

@dataclass(frozen = True)
class Func(Expr):
    name: str
    args: List[Expr]
    
    def to_odata(self) -> str:
        args_s = ', '.join(a.to_odata() for a in self.args)
        return f'{self.name}({args_s})'

@dataclass(frozen = True)
class BinaryOp(Expr):
    left: Expr
    # * Could be replaced with enum
    op: str  #'eq','ne','gt','ge','lt','le','and','or'
    right: Expr


    def to_odata(self) -> str:
        # Parentheses ensure correct precedence in mixed expressions
        return f"({self.left.to_odata()} {self.op} {self.right.to_odata()})"


@dataclass(frozen=True)
class UnaryOp(Expr):
    op: str # 'not'
    expr: Expr
    def to_odata(self) -> str:
        return f"({self.op} {self.expr.to_odata()})"


# ---------------------------
# Public facade
# ---------------------------


class FilterExpression(Expr):
    """
    Public wrapper to create and parse filter expressions.
    Behaves like an Expr and delegates to_odata to its underlying node.
    """

    def __init__(self, node: Expr):
        self._node = node

    # façade pass-through
    def to_odata(self) -> str:
        return self._node.to_odata()

    # convenience constructors
    @staticmethod
    def field(path: str) -> Field:
        return Field(path)

    # parse a limited OData subset into an AST
    @staticmethod
    def from_string(s: str) -> "FilterExpression":
        node = _FilterParser(s).parse()
        return FilterExpression(node)

    # combinators keep returning FilterExpression
    def __and__(self, other: Expr) -> "FilterExpression":
        return FilterExpression(BinaryOp(self._node, "and", _unwrap(other)))

    def __or__(self, other: Expr) -> "FilterExpression":
        return FilterExpression(BinaryOp(self._node, "or", _unwrap(other)))

    def __invert__(self) -> "FilterExpression":
        return FilterExpression(UnaryOp("not", self._node))


def _unwrap(e: Union[Expr, FilterExpression]) -> Expr:
    return e._node if isinstance(e, FilterExpression) else e


# ---------------------------
# Minimal OData filter parser
# Supports:
#   - parentheses
#   - and/or/not
#   - eq, ne, gt, ge, lt, le
#   - contains(), startswith(), endswith()
#   - identifiers with dot (field paths), string/number/bool/null
# ---------------------------

_TOKEN_SPEC = [
    ("WS", r"[ \t\n\r]+"),
    ("LPAREN", r"\("),
    ("RPAREN", r"\)"),
    ("COMMA", r","),
    ("OP", r"\b(eq|ne|gt|ge|lt|le|and|or|not)\b"),
    ("FUNC", r"\b(contains|startswith|endswith)\b"),
    ("BOOL", r"\b(true|false)\b"),
    ("NULL", r"\bnull\b"),
    ("NUMBER", r"-?\d+(\.\d+)?"),
    ("IDENT", r"[A-Za-z_][A-Za-z0-9_\.]*"),
    ("STRING", r"'([^']|'')*'"),
]

_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_SPEC), re.IGNORECASE
)


class _Token:
    def __init__(self, typ: str, val: str):
        self.type = typ
        self.value = val


class _FilterParser:
    def __init__(self, text: str):
        self.tokens = [t for t in self._tokenize(text)]
        self.pos = 0

    def _tokenize(self, text):
        for m in _TOKEN_RE.finditer(text):
            typ = m.lastgroup
            val = m.group(typ)
            if typ == "WS":
                continue
            yield _Token(typ, val)
        # implicit EOF

    def _peek(self) -> Optional[_Token]:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _eat(self, typ: str) -> _Token:
        tok = self._peek()
        if not tok or tok.type != typ:
            raise ValueError(f"Expected {typ}, found {tok.type if tok else 'EOF'}")
        self.pos += 1
        return tok

    def _match(self, typ: str) -> Optional[_Token]:
        tok = self._peek()
        if tok and tok.type == typ:
            self.pos += 1
            return tok
        return None

    # Grammar (Pratt-ish recursive descent):
    # expr  := or_expr
    # or_expr := and_expr ('or' and_expr)*
    # and_expr := not_expr ('and' not_expr)*
    # not_expr := ['not'] cmp_expr
    # cmp_expr := primary (OP primary)?
    # primary := FUNC '(' arg_list ')' | '(' expr ')' | literal | field
    # arg_list := expr (',' expr)*
    def parse(self) -> Expr:
        expr = self._parse_or()
        if self._peek():
            raise ValueError(f"Unexpected token: {self._peek().value}")
        return expr

    def _parse_or(self) -> Expr:
        node = self._parse_and()
        while (
            self._peek()
            and self._peek().type == "OP"
            and self._peek().value.lower() == "or"
        ):
            self._eat("OP")
            rhs = self._parse_and()
            node = BinaryOp(node, "or", rhs)
        return node

    def _parse_and(self) -> Expr:
        node = self._parse_not()
        while (
            self._peek()
            and self._peek().type == "OP"
            and self._peek().value.lower() == "and"
        ):
            self._eat("OP")
            rhs = self._parse_not()
            node = BinaryOp(node, "and", rhs)
        return node

    def _parse_not(self) -> Expr:
        if (
            self._peek()
            and self._peek().type == "OP"
            and self._peek().value.lower() == "not"
        ):
            self._eat("OP")
            return UnaryOp("not", self._parse_cmp())
        return self._parse_cmp()

    def _parse_cmp(self) -> Expr:
        left = self._parse_primary()
        tok = self._peek()
        if (
            tok
            and tok.type == "OP"
            and tok.value.lower() in {"eq", "ne", "gt", "ge", "lt", "le"}
        ):
            op = tok.value.lower()
            self._eat("OP")
            right = self._parse_primary()
            return BinaryOp(left, op, right)
        return left

    def _parse_primary(self) -> Expr:
        tok = self._peek()
        if not tok:
            raise ValueError("Unexpected EOF")

        if tok.type == "FUNC":
            name = tok.value.lower()
            self._eat("FUNC")
            self._eat("LPAREN")
            args = [self._parse()]
            while self._match("COMMA"):
                args.append(self._parse())
            self._eat("RPAREN")
            return Func(name, args)

        if tok.type == "LPAREN":
            self._eat("LPAREN")
            node = self._parse_or()
            self._eat("RPAREN")
            return node

        if tok.type == "IDENT":
            self._eat("IDENT")
            return Field(tok.value)

        if tok.type == "STRING":
            self._eat("STRING")
            # unescape doubled single quotes
            inner = tok.value[1:-1].replace("''", "'")
            return Literal(inner)

        if tok.type == "NUMBER":
            self._eat("NUMBER")
            return Literal(float(tok.value) if "." in tok.value else int(tok.value))

        if tok.type == "BOOL":
            self._eat("BOOL")
            return Literal(tok.value.lower() == "true")

        if tok.type == "NULL":
            self._eat("NULL")
            return Literal(None)

        raise ValueError(f"Unexpected token: {tok.value}")


if __name__ == "__main__":
    # Example: Building filters programmatically with the fluent API
    print("=== Programmatic Filter Building ===\n")

    # Simple equality filter
    filter1 = FilterExpression.field("worker.person.legalName.givenName").eq("John")
    print(f"givenName = 'John':\n  {filter1.to_odata()}\n")

    # Comparison operators
    filter2 = FilterExpression.field("employee.hireDate").ge("2020-01-01")
    print(f"hireDate >= '2020-01-01':\n  {filter2.to_odata()}\n")

    # String functions
    filter3 = FilterExpression.field("worker.person.legalName.familyName").contains("Smith")
    print(f"familyName contains 'Smith':\n  {filter3.to_odata()}\n")

    # Complex expressions with and/or operators (wrap in FilterExpression)
    filter4 = (
        FilterExpression(FilterExpression.field("worker.person.legalName.givenName").eq("John"))
        & FilterExpression(FilterExpression.field("worker.person.legalName.familyName").eq("Doe"))
    )
    print(f"givenName = 'John' AND familyName = 'Doe':\n  {filter4.to_odata()}\n")

    # Complex expression with or
    filter5 = (
        FilterExpression(FilterExpression.field("department").eq("Engineering"))
        | FilterExpression(FilterExpression.field("department").eq("Sales"))
    )
    print(f"department = 'Engineering' OR department = 'Sales':\n  {filter5.to_odata()}\n")

    # Using isin for multiple values
    filter6 = FilterExpression.field("status").isin(["Active", "OnLeave", "Pending"])
    print(f"status IN ('Active', 'OnLeave', 'Pending'):\n  {filter6.to_odata()}\n")

    # Using not operator (wrap in FilterExpression)
    filter7 = ~FilterExpression(FilterExpression.field("isTerminated").eq(True))
    print(f"NOT isTerminated = true:\n  {filter7.to_odata()}\n")

    print("=== Parsing OData Filter Strings ===\n")

    # Parse existing OData filter strings
    odata_str = "(worker.person.legalName.givenName eq 'John') and (hireDate ge '2020-01-01')"
    try:
        filter8 = FilterExpression.from_string(odata_str)
        print(f"Parsed filter:\n  Input:  {odata_str}")
        print(f"  Output: {filter8.to_odata()}\n")
    except Exception as e:
        print(f"Parse error: {e}\n")



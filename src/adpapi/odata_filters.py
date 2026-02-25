"""OData Filter Expression Builder and Parser.

This module provides a fluent API for constructing OData filter expressions
for API queries. It supports both programmatic filter building and parsing
of existing OData filter strings.

Key features:
- Fluent API for building filter expressions
- Support for comparison operators (eq, ne, gt, ge, lt, le)
- String functions (contains, startswith, endswith)
- Logical operators (and, or, not)
- Parse existing OData filter strings into expressions
- Type-safe filter construction

Example:
    >>> from adpapi.odata_filters import FilterExpression
    >>> f = FilterExpression.field('worker.firstName').eq('John')
    >>> f.to_odata()
    "(worker/firstName eq 'John')"
"""

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Union


# AST NODE TYPES
class Expr:
    """Abstract base class for OData filter expression AST nodes.

    All filter expressions inherit from this class and implement the to_odata()
    method to convert the expression tree to an OData filter string.

    Supports logical operator overloading:
    - & (and): Combines two expressions with AND
    - | (or): Combines two expressions with OR
    - ~ (not): Inverts an expression with NOT
    """

    def to_odata(self) -> str:
        """Convert this expression to an OData filter string.

        Returns:
            str: The OData v4 filter string representation of this expression.

        Raises:
            NotImplementedError: This method must be implemented by subclasses.
        """
        raise NotImplementedError

    def __and__(self, other: "Expr") -> "Expr":
        """Combine two expressions with logical AND.

        Args:
            other: Another Expr to combine with AND.

        Returns:
            Expr: A new binary operation node representing the AND operation.

        Example:
            >>> expr1 = FilterExpression.field('age').gt(18)
            >>> expr2 = FilterExpression.field('status').eq('Active')
            >>> combined = expr1 & expr2
        """
        return BinaryOp(self, "and", other)

    def __or__(self, other: "Expr") -> "Expr":
        """Combine two expressions with logical OR.

        Args:
            other: Another Expr to combine with OR.

        Returns:
            Expr: A new binary operation node representing the OR operation.

        Example:
            >>> expr1 = FilterExpression.field('status').eq('Active')
            >>> expr2 = FilterExpression.field('status').eq('Pending')
            >>> combined = expr1 | expr2
        """
        return BinaryOp(self, "or", other)

    def __invert__(self) -> "Expr":
        """Invert an expression with logical NOT.

        Returns:
            Expr: A new unary operation node applying NOT to this expression.

        Example:
            >>> expr = FilterExpression.field('isTerminated').eq(True)
            >>> inverted = ~expr  # NOT isTerminated = true
        """
        return UnaryOp("not", self)


@dataclass(frozen=True)
class Field(Expr):
    """Represents a field reference in an OData filter expression.

    Fields are identified by their path (e.g., 'worker.person.firstName').
    This class provides a fluent API for building filter conditions on fields.

    Attributes:
        path (str): The dot-separated path to the field, supporting nested properties.

    Example:
        >>> field = Field('worker.hireDate')
        >>> field.eq('2020-01-01').to_odata()
        "(worker/hireDate eq '2020-01-01')"
    """

    path: str

    # comparisons
    def eq(self, val: Any) -> "BinaryOp":
        """Create an equality comparison filter (field = value).

        Args:
            val: The value to compare against. Can be string, number, boolean, or None.

        Returns:
            BinaryOp: A binary operation representing the equality condition.

        Example:
            >>> FilterExpression.field('status').eq('Active').to_odata()
            "(status eq 'Active')"
        """
        return BinaryOp(self, "eq", literal(val))

    def ne(self, val: Any) -> "BinaryOp":
        """Create a not-equal comparison filter (field != value).

        Args:
            val: The value to compare against. Can be string, number, boolean, or None.

        Returns:
            BinaryOp: A binary operation representing the not-equal condition.

        Example:
            >>> FilterExpression.field('status').ne('Inactive').to_odata()
            "(status ne 'Inactive')"
        """
        return BinaryOp(self, "ne", literal(val))

    def gt(self, val: Any) -> "BinaryOp":
        """Create a greater-than comparison filter (field > value).

        Args:
            val: The value to compare against. Typically a number or date string.

        Returns:
            BinaryOp: A binary operation representing the greater-than condition.

        Example:
            >>> FilterExpression.field('salary').gt(50000).to_odata()
            "(salary gt 50000)"
        """
        return BinaryOp(self, "gt", literal(val))

    def ge(self, val: Any) -> "BinaryOp":
        """Create a greater-than-or-equal comparison filter (field >= value).

        Args:
            val: The value to compare against. Typically a number or date string.

        Returns:
            BinaryOp: A binary operation representing the greater-than-or-equal condition.

        Example:
            >>> FilterExpression.field('hireDate').ge('2020-01-01').to_odata()
            "(hireDate ge '2020-01-01')"
        """
        return BinaryOp(self, "ge", literal(val))

    def lt(self, val: Any) -> "BinaryOp":
        """Create a less-than comparison filter (field < value).

        Args:
            val: The value to compare against. Typically a number or date string.

        Returns:
            BinaryOp: A binary operation representing the less-than condition.

        Example:
            >>> FilterExpression.field('salary').lt(100000).to_odata()
            "(salary lt 100000)"
        """
        return BinaryOp(self, "lt", literal(val))

    def le(self, val: Any) -> "BinaryOp":
        """Create a less-than-or-equal comparison filter (field <= value).

        Args:
            val: The value to compare against. Typically a number or date string.

        Returns:
            BinaryOp: A binary operation representing the less-than-or-equal condition.

        Example:
            >>> FilterExpression.field('retirementDate').le('2025-12-31').to_odata()
            "(retirementDate le '2025-12-31')"
        """
        return BinaryOp(self, "le", literal(val))

    # string functions
    def contains(self, val: Any) -> "Func":
        """Create a substring contains filter for string fields.

        Args:
            val: The substring to search for within the field value.

        Returns:
            Func: A function call representing the contains operation.

        Example:
            >>> FilterExpression.field('lastName').contains('Smith').to_odata()
            "contains(lastName, 'Smith')"
        """
        return Func("contains", [self, literal(val)])

    def startswith(self, val: Any) -> "Func":
        """Create a string starts-with filter.

        Args:
            val: The prefix to search for at the start of the field value.

        Returns:
            Func: A function call representing the startswith operation.

        Example:
            >>> FilterExpression.field('firstName').startswith('John').to_odata()
            "startswith(firstName, 'John')"
        """
        return Func("startswith", [self, literal(val)])

    def endswith(self, val: Any) -> "Func":
        """Create a string ends-with filter.

        Args:
            val: The suffix to search for at the end of the field value.

        Returns:
            Func: A function call representing the endswith operation.

        Example:
            >>> FilterExpression.field('email').endswith('@company.com').to_odata()
            "endswith(email, '@company.com')"
        """
        return Func("endswith", [self, literal(val)])

    # emulate IN as disjunction
    def isin(self, values: List[Any]) -> "Expr":
        """Create an IN filter for multiple values (field IN (val1, val2, ...)).

        Since OData v4 doesn't have a native IN operator, this is implemented as
        a series of OR conditions joined together.

        Args:
            values: A list of values to check against. If empty, returns false.

        Returns:
            Expr: An expression representing the IN operation. For empty lists,
                  returns an always-false condition (1 eq 0).

        Example:
            >>> statuses = ['Active', 'OnLeave', 'Pending']
            >>> FilterExpression.field('status').isin(statuses).to_odata()
            "((status eq 'Active') or ((status eq 'OnLeave') or (status eq 'Pending')))"
        """
        if not values:
            # empty IN -> false; represent as (1 eq 0)
            return BinaryOp(Literal(1), "eq", Literal(0))
        expr: Expr = BinaryOp(self, "eq", literal(values[0]))
        for v in values[1:]:
            clause = BinaryOp(self, "eq", literal(v))
            expr = BinaryOp(expr, "or", clause)
        return expr

    def to_odata(self) -> str:
        """Convert this field reference to an OData path string.

        Converts dot notation to forward slash notation for OData v4 compliance.

        Returns:
            str: The OData-compliant field path.

        Example:
            >>> Field('worker.person.firstName').to_odata()
            'worker/person/firstName'
        """
        # Convert dot notation to forward slash for OData v4 compliance
        # Input: "workers.workAssignments.reportsTo.positionID"
        # Output: "workers/workAssignments/reportsTo/positionID"
        return self.path.replace(".", "/")


@dataclass(frozen=True)
class Literal(Expr):
    """Represents a literal value in an OData filter expression.

    Handles conversion of Python values (strings, numbers, booleans, None) to
    their OData string representation.

    Attributes:
        value: The Python value to represent as a literal.

    Example:
        >>> lit = Literal(42)
        >>> lit.to_odata()
        '42'
        >>> lit = Literal('hello')
        >>> lit.to_odata()
        \"'hello'\"
    """

    value: Any

    def to_odata(self) -> str:
        """Convert this literal value to an OData string representation.

        Handles proper escaping of quotes and conversion of Python types to
        OData literal syntax.

        Returns:
            str: The OData-compliant literal representation.
            - null for None values
            - true/false for booleans
            - numeric representation for numbers
            - quoted and escaped string for text values

        Example:
            >>> Literal(None).to_odata()
            'null'
            >>> Literal(True).to_odata()
            'true'
            >>> Literal("O'Reilly").to_odata()
            \"'O''Reilly'\"
        """
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
    """Create a Literal value from a Python value.

    Convenience function for creating Literal nodes.

    Args:
        v: Any Python value (string, number, boolean, None).

    Returns:
        Literal: A new Literal node representing the value.

    Example:
        >>> literal(42).to_odata()
        '42'
        >>> literal('test').to_odata()
        \"'test'\"
    """
    return Literal(v)


@dataclass(frozen=True)
class Func(Expr):
    """Represents a function call in an OData filter expression.

    Functions can include built-in OData string functions like contains,
    startswith, and endswith, or potentially custom functions.

    Attributes:
        name (str): The function name (e.g., 'contains', 'startswith', 'endswith').
        args (List[Expr]): List of argument expressions to pass to the function.

    Example:
        >>> func = Func('contains', [Field('lastName'), Literal('Smith')])
        >>> func.to_odata()
        \"contains(lastName, 'Smith')\"
    """

    name: str
    args: List[Expr]

    def to_odata(self) -> str:
        """Convert this function call to an OData string representation.

        Returns:
            str: The OData-compliant function call syntax.

        Example:
            >>> Func('startswith', [Field('email'), Literal('admin')]).to_odata()
            \"startswith(email, 'admin')\"
        """
        args_s = ", ".join(a.to_odata() for a in self.args)
        return f"{self.name}({args_s})"


@dataclass(frozen=True)
class BinaryOp(Expr):
    """Represents a binary operation in an OData filter expression.

    Binary operations include comparisons (eq, ne, gt, ge, lt, le) and logical
    operators (and, or).

    Attributes:
        left (Expr): The left operand expression.
        op (str): The operator ('eq', 'ne', 'gt', 'ge', 'lt', 'le', 'and', 'or').
        right (Expr): The right operand expression.

    Example:
        >>> op = BinaryOp(Field('age'), 'gt', Literal(18))
        >>> op.to_odata()
        '(age gt 18)'
    """

    left: Expr
    # * Could be replaced with enum
    op: str  #'eq','ne','gt','ge','lt','le','and','or'
    right: Expr

    def to_odata(self) -> str:
        """Convert this binary operation to an OData string representation.

        Wraps the entire operation in parentheses to ensure correct precedence
        in complex expressions.

        Returns:
            str: The OData-compliant operation syntax with parentheses.

        Example:
            >>> BinaryOp(Field('a'), 'eq', Literal(1)).to_odata()
            '(a eq 1)'
        """
        # Parentheses ensure correct precedence in mixed expressions
        return f"({self.left.to_odata()} {self.op} {self.right.to_odata()})"


@dataclass(frozen=True)
class UnaryOp(Expr):
    """Represents a unary operation in an OData filter expression.

    Currently supports the NOT operator for inverting boolean expressions.

    Attributes:
        op (str): The operator (typically 'not').
        expr (Expr): The operand expression to apply the operator to.

    Example:
        >>> op = UnaryOp('not', BinaryOp(Field('isActive'), 'eq', Literal(True)))
        >>> op.to_odata()
        '(not (isActive eq true))'
    """

    op: str  # 'not'
    expr: Expr

    def to_odata(self) -> str:
        """Convert this unary operation to an OData string representation.

        Returns:
            str: The OData-compliant operation syntax with parentheses.

        Example:
            >>> UnaryOp('not', Field('isActive')).to_odata()
            '(not isActive)'
        """
        return f"({self.op} {self.expr.to_odata()})"


# ---------------------------
# Public facade
# ---------------------------


class FilterExpression(Expr):
    """Public API for creating and managing OData filter expressions.

    Attributes:
        _node (Expr): The internal AST node representing the expression.

    Examples:
        Build filters programmatically:
        >>> f = FilterExpression.field('firstName').eq('John')
        >>> f.to_odata()
        "(firstName eq 'John')"

        Combine with logical operators:
        >>> f1 = FilterExpression.field('age').gt(18)
        >>> f2 = FilterExpression.field('status').eq('Active')
        >>> combined = f1 & f2
        >>> combined.to_odata()
        "((age gt 18) and (status eq 'Active'))"

        Parse existing OData filter strings:
        >>> f = FilterExpression.from_string("firstName eq 'John'")
        >>> f.to_odata()
        "(firstName eq 'John')"
    """

    def __init__(self, node: Expr):
        """Initialize a FilterExpression with an AST node.

        Args:
            node: An Expr AST node representing the filter expression.
        """
        self._node = node

    # façade pass-through
    def to_odata(self) -> str:
        """Convert this filter expression to an OData v4 filter string.

        Returns:
            str: The complete OData filter string ready for use in API requests.

        Example:
            >>> FilterExpression.field('status').eq('Active').to_odata()
            "(status eq 'Active')"
        """
        return self._node.to_odata()

    # convenience constructors
    @staticmethod
    def field(path: str) -> Field:
        """Create a field reference for building filter conditions.

        This is the primary entry point for building filters. The returned Field
        object provides a fluent API with comparison and string function methods.

        Args:
            path (str): Dot-separated field path (e.g., 'worker.person.firstName').
                       Supports nested properties accessible through the API.

        Returns:
            Field: A Field object with methods for building conditions.

        Example:
            >>> f = FilterExpression.field('lastName')
            >>> f = f.eq('Smith')
            >>> f.to_odata()
            "(lastName eq 'Smith')"

        Commonly used field paths:
            - 'worker.firstName' - Worker's first name
            - 'worker.lastName' - Worker's last name
            - 'hireDate' - Date of hire
            - 'department' - Department assignment
            - 'salary' - Salary information
        """
        return Field(path)

    # parse a limited OData subset into an AST
    @staticmethod
    def from_string(s: str) -> "FilterExpression":
        """Parse an OData filter string into a FilterExpression.

        This parser supports a subset of OData v4 filter syntax, including:
        - Comparison operators: eq, ne, gt, ge, lt, le
        - Logical operators: and, or, not
        - Boolean operators with parentheses for grouping
        - String functions: contains(), startswith(), endswith()
        - Literal values: strings, numbers, booleans, null
        - Field paths with dot notation

        Args:
            s (str): An OData filter string to parse.

        Returns:
            FilterExpression: A parsed and structured filter expression.

        Raises:
            ValueError: If the filter string has syntax errors or uses unsupported
                       OData features.

        Example:
            >>> f = FilterExpression.from_string(
            ...     "(firstName eq 'John') and (lastName eq 'Doe')"
            ... )
            >>> f.to_odata()
            "((firstName eq 'John') and (lastName eq 'Doe'))"

            Parse a string function:
            >>> f = FilterExpression.from_string(
            ...     "contains(email, '@company.com')"
            ... )
            >>> f.to_odata()
            "contains(email, '@company.com')"
        """
        node = _FilterParser(s).parse()
        return FilterExpression(node)

    # combinators keep returning FilterExpression
    def __and__(self, other: Expr) -> "FilterExpression":
        """Combine this expression with another using logical AND.

        Args:
            other: Another FilterExpression or Expr to combine with AND.

        Returns:
            FilterExpression: A new combined filter expression.

        Example:
            >>> expr1 = FilterExpression.field('age').gt(18)
            >>> expr2 = FilterExpression.field('status').eq('Active')
            >>> combined = expr1 & expr2
            >>> combined.to_odata()
            "((age gt 18) and (status eq 'Active'))"
        """
        return FilterExpression(BinaryOp(self._node, "and", _unwrap(other)))

    def __or__(self, other: Expr) -> "FilterExpression":
        """Combine this expression with another using logical OR.

        Args:
            other: Another FilterExpression or Expr to combine with OR.

        Returns:
            FilterExpression: A new combined filter expression.

        Example:
            >>> expr1 = FilterExpression.field('status').eq('Active')
            >>> expr2 = FilterExpression.field('status').eq('Pending')
            >>> combined = expr1 | expr2
            >>> combined.to_odata()
            "((status eq 'Active') or (status eq 'Pending'))"
        """
        return FilterExpression(BinaryOp(self._node, "or", _unwrap(other)))

    def __invert__(self) -> "FilterExpression":
        """Invert this expression using logical NOT.

        Returns:
            FilterExpression: A new inverted filter expression.

        Example:
            >>> expr = FilterExpression.field('isTerminated').eq(True)
            >>> inverted = ~expr
            >>> inverted.to_odata()
            "(not (isTerminated eq true))"
        """
        return FilterExpression(UnaryOp("not", self._node))


def _unwrap(e: Union[Expr, FilterExpression]) -> Expr:
    """Extract the internal AST node from a FilterExpression if needed.

    Helper function to unwrap FilterExpression instances for combining with
    other expressions. Returns the input unchanged if it's already an Expr.

    Args:
        e: An Expr or FilterExpression.

    Returns:
        Expr: The underlying AST node.
    """
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

"""Token specification for OData filter lexer.

Defines regex patterns for recognizing different token types in OData filter
strings, including operators, literals, identifiers, and special syntax.
"""
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

"""Compiled regex for tokenizing OData filter strings."""
_TOKEN_RE = re.compile(
    "|".join(f"(?P<{name}>{pat})" for name, pat in _TOKEN_SPEC), re.IGNORECASE
)


class _Token:
    """Internal representation of a lexical token.

    Attributes:
        type (str): The token type (e.g., 'IDENT', 'OP', 'STRING').
        value (str): The raw text value of the token.
    """

    def __init__(self, typ: str, val: str):
        """Initialize a token.

        Args:
            typ: The token type identifier.
            val: The token's string value.
        """
        self.type = typ
        self.value = val


class _FilterParser:
    """Internal parser for OData filter strings.

    Implements a recursive descent parser for a subset of OData v4 filters.
    Produces an AST of Expr nodes that can be converted to OData syntax.

    Supported grammar:
        expr       := or_expr
        or_expr    := and_expr ('or' and_expr)*
        and_expr   := not_expr ('and' not_expr)*
        not_expr   := [not'] cmp_expr
        cmp_expr   := primary (OP primary)?
        primary    := FUNC '(' arg_list ')' | '(' expr ')' | literal | field
        arg_list   := expr (',' expr)*
    """

    def __init__(self, text: str):
        """Initialize the parser with a filter string.

        Args:
            text: The OData filter string to parse.
        """
        self.tokens = [t for t in self._tokenize(text)]
        self.pos = 0

    def _tokenize(self, text):
        """Tokenize an OData filter string.

        Args:
            text: The filter string to tokenize.

        Yields:
            _Token: Individual tokens from the input.
        """
        for m in _TOKEN_RE.finditer(text):
            typ = m.lastgroup
            val = m.group(typ)
            if typ == "WS":
                continue
            yield _Token(typ, val)
        # implicit EOF

    def _peek(self) -> Optional[_Token]:
        """Look at the current token without consuming it.

        Returns:
            _Token: The current token, or None if at EOF.
        """
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _eat(self, typ: str) -> _Token:
        """Consume and return the next token if it matches expected type.

        Args:
            typ: The expected token type.

        Returns:
            _Token: The consumed token.

        Raises:
            ValueError: If the current token doesn't match the expected type.
        """
        tok = self._peek()
        if not tok or tok.type != typ:
            raise ValueError(f"Expected {typ}, found {tok.type if tok else 'EOF'}")
        self.pos += 1
        return tok

    def _match(self, typ: str) -> Optional[_Token]:
        """Optionally consume the next token if it matches a type.

        Args:
            typ: The expected token type.

        Returns:
            _Token: The consumed token if matched, None otherwise.
        """
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
        """Parse the entire filter string into an AST.

        Returns:
            Expr: The root node of the parsed expression tree.

        Raises:
            ValueError: If the filter string has syntax errors or unexpected tokens.
        """
        expr = self._parse_or()
        tok = self._peek()
        if tok:
            raise ValueError(f"Unexpected token: {tok.value}")
        return expr

    def _parse_or(self) -> Expr:
        """Parse OR expressions (lowest precedence).

        Returns:
            Expr: The parsed OR expression.
        """
        node = self._parse_and()
        while (
            (tok := self._peek()) is not None
            and tok.type == "OP"
            and tok.value.lower() == "or"
        ):
            self._eat("OP")
            rhs = self._parse_and()
            node = BinaryOp(node, "or", rhs)
        return node

    def _parse_and(self) -> Expr:
        """Parse AND expressions.

        Returns:
            Expr: The parsed AND expression.
        """
        node = self._parse_not()
        while (
            (tok := self._peek()) is not None
            and tok.type == "OP"
            and tok.value.lower() == "and"
        ):
            self._eat("OP")
            rhs = self._parse_not()
            node = BinaryOp(node, "and", rhs)
        return node

    def _parse_not(self) -> Expr:
        """Parse NOT expressions.

        Returns:
            Expr: The parsed NOT expression.
        """
        if (
            (tok := self._peek()) is not None
            and tok.type == "OP"
            and tok.value.lower() == "not"
        ):
            self._eat("OP")
            return UnaryOp("not", self._parse_cmp())
        return self._parse_cmp()

    def _parse_cmp(self) -> Expr:
        """Parse comparison expressions (eq, ne, gt, ge, lt, le).

        Returns:
            Expr: The parsed comparison or primary expression.
        """
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
        """Parse primary expressions (function calls, parentheses, literals, fields).

        Returns:
            Expr: The parsed primary expression.

        Raises:
            ValueError: If an unexpected token is encountered or EOF is reached.
        """
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

    def _parse(self) -> Expr:
        """Parse an expression (internal method for recursive parsing).

        Used internally for parsing function arguments and ensures proper
        precedence handling in recursive contexts.

        Returns:
            Expr: The parsed expression.
        """
        return self._parse_or()


if __name__ == "__main__":
    """Example usage of the FilterExpression API.
    
    This section demonstrates both approaches:
    1. Programmatic filter building using the fluent API
    2. Parsing existing OData filter strings
    
    Run this file directly to see example output:
        python -m src.adpapi.odata_filters
    
    Examples cover:
    - Simple equality filters
    - Comparison operators (eq, ne, gt, ge, lt, le)
    - String functions (contains, startswith, endswith)
    - Complex expressions with logical operators (and, or, not)
    - Multiple value matching with isin()
    - Parsing OData filter strings
    """
    # Example: Building filters programmatically with the fluent API
    print("=== Programmatic Filter Building ===\n")

    # Simple equality filter
    filter1 = FilterExpression.field("worker.person.legalName.givenName").eq("John")
    print(f"givenName = 'John':\n  {filter1.to_odata()}\n")

    # Comparison operators
    filter2 = FilterExpression.field("employee.hireDate").ge("2020-01-01")
    print(f"hireDate >= '2020-01-01':\n  {filter2.to_odata()}\n")

    # String functions
    filter3 = FilterExpression.field("worker.person.legalName.familyName").contains(
        "Smith"
    )
    print(f"familyName contains 'Smith':\n  {filter3.to_odata()}\n")

    # Complex expressions with and/or operators (wrap in FilterExpression)
    filter4 = FilterExpression(
        FilterExpression.field("worker.person.legalName.givenName").eq("John")
    ) & FilterExpression(
        FilterExpression.field("worker.person.legalName.familyName").eq("Doe")
    )
    print(f"givenName = 'John' AND familyName = 'Doe':\n  {filter4.to_odata()}\n")

    # Complex expression with or
    filter5 = FilterExpression(
        FilterExpression.field("department").eq("Engineering")
    ) | FilterExpression(FilterExpression.field("department").eq("Sales"))
    print(
        f"department = 'Engineering' OR department = 'Sales':\n  {filter5.to_odata()}\n"
    )

    # Using isin for multiple values
    filter6 = FilterExpression.field("status").isin(["Active", "OnLeave", "Pending"])
    print(f"status IN ('Active', 'OnLeave', 'Pending'):\n  {filter6.to_odata()}\n")

    # Using not operator (wrap in FilterExpression)
    filter7 = ~FilterExpression(FilterExpression.field("isTerminated").eq(True))
    print(f"NOT isTerminated = true:\n  {filter7.to_odata()}\n")

    print("=== Parsing OData Filter Strings ===\n")

    # Parse existing OData filter strings
    odata_str = (
        "(worker.person.legalName.givenName eq 'John') and (hireDate ge '2020-01-01')"
    )
    try:
        filter8 = FilterExpression.from_string(odata_str)
        print(f"Parsed filter:\n  Input:  {odata_str}")
        print(f"  Output: {filter8.to_odata()}\n")
    except Exception as e:
        print(f"Parse error: {e}\n")

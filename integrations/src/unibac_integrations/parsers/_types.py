from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer

# Serialise Decimals as JSON numbers (not strings) so LLM tool callers don't
# misread "100.00" as "10%". rust_decimal's default serde impl accepts both
# strings and numbers, so the cam-builder path is unaffected.
JsonDecimal = Annotated[
    Decimal,
    PlainSerializer(lambda v: float(v), return_type=float, when_used="json"),
]

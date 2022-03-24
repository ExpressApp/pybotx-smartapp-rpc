from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RPCError:
    reason: str
    id: str
    meta: Dict[str, Any] = field(default_factory=dict)

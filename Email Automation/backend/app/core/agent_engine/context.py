from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class StateContext:
    """
    Enhanced state manager for passing variables between tasks.
    Supports namespacing and history tracking.
    """
    
    def __init__(self):
        self._memory: Dict[str, Any] = {}
        self._history: list = []  # Track updates for debugging
        self._namespaces: Dict[str, Dict[str, Any]] = {}

    def update(self, key: str, value: Any, namespace: Optional[str] = None):
        """Update the shared memory with a new key-value pair."""
        if namespace:
            if namespace not in self._namespaces:
                self._namespaces[namespace] = {}
            self._namespaces[namespace][key] = value
            logger.info(f"🚧 [StateContext] Updated {namespace}.{key}")
        else:
            self._memory[key] = value
            logger.info(f"🚧 [StateContext] Updated {key}")
        
        # Track history
        self._history.append({
            "timestamp": datetime.utcnow(),
            "key": key,
            "namespace": namespace,
            "action": "update"
        })

    def get(self, key: str, default: Any = None, namespace: Optional[str] = None) -> Any:
        """Retrieve a value from the shared memory."""
        if namespace:
            return self._namespaces.get(namespace, {}).get(key, default)
        return self._memory.get(key, default)

    def get_namespace(self, namespace: str) -> Dict[str, Any]:
        """Get all variables in a namespace."""
        return self._namespaces.get(namespace, {}).copy()

    def clear(self, namespace: Optional[str] = None):
        """Clear all stored variables or a specific namespace."""
        if namespace:
            self._namespaces.pop(namespace, None)
            logger.info(f"🚧 [StateContext] Cleared namespace: {namespace}")
        else:
            self._memory = {}
            self._namespaces = {}
            self._history = []
            logger.info("🚧 [StateContext] Cleared all memory")

    @property
    def all_vars(self) -> Dict[str, Any]:
        """Return a copy of all variables (including namespaces)."""
        result = self._memory.copy()
        for ns, vars in self._namespaces.items():
            result[f"__namespace_{ns}"] = vars
        return result

    def get_history(self, limit: Optional[int] = None) -> list:
        """Get update history (for debugging)."""
        if limit:
            return self._history[-limit:]
        return self._history.copy()


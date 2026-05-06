"""
Policies Engine - Core implementation.
"""

from enum import Enum
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
import asyncio


class ErrorType(Enum):
    """Types of errors that can occur during parsing."""
    SUCCESS = "success"  # Добавлено для успешных операций
    HTTP_403 = "http_403"
    HTTP_404 = "http_404"
    HTTP_429 = "http_429"  # Rate limited
    HTTP_500 = "http_500"
    TIMEOUT = "timeout"
    CAPTCHA = "captcha"
    SELECTOR_NOT_FOUND = "selector_not_found"
    EMPTY_RESPONSE = "empty_response"
    NETWORK_ERROR = "network_error"
    UNKNOWN = "unknown"


class ActionType(Enum):
    """Actions that can be taken in response to errors."""
    RETRY = "retry"
    CHANGE_PROXY = "change_proxy"
    CHANGE_USER_AGENT = "change_user_agent"
    INCREASE_DELAY = "increase_delay"
    SWITCH_TO_PLAYWRIGHT = "switch_to_playwright"
    SWITCH_TO_CURL = "switch_to_curl"
    SKIP_CATEGORY = "skip_category"
    ABORT_SESSION = "abort_session"
    WAIT_AND_RETRY = "wait_and_retry"
    CLEAR_COOKIES = "clear_cookies"
    SOLVE_CAPTCHA = "solve_captcha"


@dataclass
class PolicyRule:
    """A single policy rule for error handling."""
    error_types: List[ErrorType]
    actions: List[ActionType]
    max_retries: int = 3
    delay_between_retries: float = 1.0
    priority: int = 1  # Higher priority rules are checked first
    condition: Optional[Callable[[Any], bool]] = None  # Custom condition
    
    def matches(self, error_type: ErrorType, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if this rule matches the given error type."""
        if error_type not in self.error_types:
            return False
            
        if self.condition and context:
            return self.condition(context)
            
        return True


@dataclass
class PolicyResult:
    """Result of policy evaluation."""
    should_retry: bool = False
    actions: List[ActionType] = field(default_factory=list)
    delay: float = 0.0
    new_proxy: bool = False
    abort: bool = False
    message: str = ""


class PoliciesEngine:
    """
    Policy-driven error handling engine.
    
    Automatically responds to errors based on configurable rules,
    implementing best practices from browser-act.
    """

    # Default policies for common scenarios
    DEFAULT_POLICIES = [
        # HTTP 403 - Forbidden (likely blocked)
        PolicyRule(
            error_types=[ErrorType.HTTP_403],
            actions=[
                ActionType.CHANGE_PROXY,
                ActionType.CHANGE_USER_AGENT,
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=5,
            delay_between_retries=2.0,
            priority=10,
        ),
        
        # HTTP 429 - Rate limited
        PolicyRule(
            error_types=[ErrorType.HTTP_429],
            actions=[
                ActionType.INCREASE_DELAY,
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=3,
            delay_between_retries=5.0,
            priority=9,
        ),
        
        # CAPTCHA detected
        PolicyRule(
            error_types=[ErrorType.CAPTCHA],
            actions=[
                ActionType.SOLVE_CAPTCHA,
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=2,
            delay_between_retries=10.0,
            priority=8,
        ),
        
        # Timeout
        PolicyRule(
            error_types=[ErrorType.TIMEOUT],
            actions=[
                ActionType.CHANGE_PROXY,
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=3,
            delay_between_retries=3.0,
            priority=7,
        ),
        
        # Selector not found
        PolicyRule(
            error_types=[ErrorType.SELECTOR_NOT_FOUND],
            actions=[
                ActionType.SWITCH_TO_PLAYWRIGHT,
                ActionType.RETRY,
            ],
            max_retries=2,
            delay_between_retries=1.0,
            priority=6,
        ),
        
        # Empty response
        PolicyRule(
            error_types=[ErrorType.EMPTY_RESPONSE],
            actions=[
                ActionType.CHANGE_PROXY,
                ActionType.CLEAR_COOKIES,
                ActionType.RETRY,
            ],
            max_retries=3,
            delay_between_retries=2.0,
            priority=5,
        ),
        
        # Network errors
        PolicyRule(
            error_types=[ErrorType.NETWORK_ERROR],
            actions=[
                ActionType.CHANGE_PROXY,
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=5,
            delay_between_retries=1.0,
            priority=4,
        ),
        
        # HTTP 500
        PolicyRule(
            error_types=[ErrorType.HTTP_500],
            actions=[
                ActionType.WAIT_AND_RETRY,
            ],
            max_retries=3,
            delay_between_retries=5.0,
            priority=3,
        ),
        
        # HTTP 404
        PolicyRule(
            error_types=[ErrorType.HTTP_404],
            actions=[
                ActionType.SKIP_CATEGORY,
            ],
            max_retries=0,
            delay_between_retries=0.0,
            priority=1,
        ),
    ]

    def __init__(self, custom_policies: Optional[List[PolicyRule]] = None):
        self.policies = custom_policies or self.DEFAULT_POLICIES.copy()
        self.retry_counts: Dict[str, int] = {}
        self.current_delay: float = 1.0
        self._lock = asyncio.Lock()

    async def evaluate(
        self,
        error_type: ErrorType,
        request_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyResult:
        """Evaluate error and determine appropriate action."""
        async with self._lock:
            retry_count = self.retry_counts.get(request_id, 0)
            sorted_policies = sorted(self.policies, key=lambda p: p.priority, reverse=True)
            
            for policy in sorted_policies:
                if policy.matches(error_type, context):
                    if retry_count >= policy.max_retries:
                        return PolicyResult(
                            should_retry=False,
                            abort=True,
                            message=f"Max retries ({policy.max_retries}) exceeded",
                        )
                    
                    result = PolicyResult(
                        should_retry=True,
                        actions=policy.actions,
                        delay=policy.delay_between_retries,
                        new_proxy=ActionType.CHANGE_PROXY in policy.actions,
                        message=f"Policy triggered: {[a.value for a in policy.actions]}",
                    )
                    
                    self.retry_counts[request_id] = retry_count + 1
                    
                    if ActionType.INCREASE_DELAY in policy.actions:
                        self.current_delay = min(self.current_delay * 1.5, 30.0)
                    
                    return result
            
            return PolicyResult(
                should_retry=False,
                message=f"No policy for {error_type.value}",
            )

    async def reset_request(self, request_id: str) -> None:
        """Reset retry count for a request."""
        async with self._lock:
            if request_id in self.retry_counts:
                del self.retry_counts[request_id]

    async def reset_all(self) -> None:
        """Reset all state."""
        async with self._lock:
            self.retry_counts.clear()
            self.current_delay = 1.0

    def add_policy(self, policy: PolicyRule) -> None:
        """Add custom policy."""
        self.policies.append(policy)
        self.policies.sort(key=lambda p: p.priority, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics."""
        return {
            "total_policies": len(self.policies),
            "active_retries": len(self.retry_counts),
            "current_delay": self.current_delay,
        }


def classify_error(exception: Exception, status_code: Optional[int] = None) -> ErrorType:
    """Classify exception into ErrorType."""
    if status_code:
        if status_code == 403:
            return ErrorType.HTTP_403
        elif status_code == 404:
            return ErrorType.HTTP_404
        elif status_code == 429:
            return ErrorType.HTTP_429
        elif status_code >= 500:
            return ErrorType.HTTP_500
    
    error_msg = str(exception).lower()
    
    if "captcha" in error_msg or "challenge" in error_msg:
        return ErrorType.CAPTCHA
    elif "timeout" in error_msg:
        return ErrorType.TIMEOUT
    elif "selector" in error_msg or "not found" in error_msg:
        return ErrorType.SELECTOR_NOT_FOUND
    elif "empty" in error_msg:
        return ErrorType.EMPTY_RESPONSE
    elif "network" in error_msg or "connection" in error_msg:
        return ErrorType.NETWORK_ERROR
    
    return ErrorType.UNKNOWN

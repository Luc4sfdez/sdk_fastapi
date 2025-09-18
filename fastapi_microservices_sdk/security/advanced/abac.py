"""
Attribute-Based Access Control (ABAC) Implementation for FastAPI Microservices SDK.

This module provides comprehensive ABAC support including policy management,
attribute collection, policy evaluation with complex boolean logic, and
contextual access control for fine-grained authorization decisions.
"""
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import operator
from abc import ABC, abstractmethod

from .exceptions import ABACError, AdvancedSecurityError
from .logging import get_security_logger, SecurityEvent, SecurityEventSeverity, SecurityEventType
from .config import AdvancedSecurityConfig


class AttributeType(Enum):
    """Types of attributes in ABAC system."""
    USER = "user"
    RESOURCE = "resource"
    ENVIRONMENT = "environment"
    ACTION = "action"


class PolicyEffect(Enum):
    """Policy evaluation effects."""
    ALLOW = "allow"
    DENY = "deny"


class ComparisonOperator(Enum):
    """Comparison operators for policy rules."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    MATCHES = "matches"
    NOT_MATCHES = "not_matches"


class LogicalOperator(Enum):
    """Logical operators for combining policy rules."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class AttributeValue:
    """Represents an attribute value with metadata."""
    value: Any
    type: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate attribute value after initialization."""
        if self.value is None:
            raise ABACError("Attribute value cannot be None")
        if not self.type:
            raise ABACError("Attribute type must be specified")
        if not self.source:
            raise ABACError("Attribute source must be specified")


@dataclass
class Attributes:
    """Collection of attributes organized by type."""
    user: Dict[str, AttributeValue] = field(default_factory=dict)
    resource: Dict[str, AttributeValue] = field(default_factory=dict)
    environment: Dict[str, AttributeValue] = field(default_factory=dict)
    action: Dict[str, AttributeValue] = field(default_factory=dict)
    
    def get_attribute(self, attr_type: AttributeType, name: str) -> Optional[AttributeValue]:
        """Get attribute by type and name."""
        attr_dict = getattr(self, attr_type.value)
        return attr_dict.get(name)
    
    def set_attribute(self, attr_type: AttributeType, name: str, value: AttributeValue):
        """Set attribute by type and name."""
        attr_dict = getattr(self, attr_type.value)
        attr_dict[name] = value
    
    def has_attribute(self, attr_type: AttributeType, name: str) -> bool:
        """Check if attribute exists."""
        return self.get_attribute(attr_type, name) is not None
    
    def get_all_attributes(self) -> Dict[str, Dict[str, AttributeValue]]:
        """Get all attributes organized by type."""
        return {
            "user": self.user,
            "resource": self.resource,
            "environment": self.environment,
            "action": self.action
        }


@dataclass
class PolicyCondition:
    """Represents a single condition in a policy rule."""
    attribute_type: AttributeType
    attribute_name: str
    operator: ComparisonOperator
    value: Any
    
    def evaluate(self, attributes: Attributes) -> bool:
        """Evaluate condition against provided attributes."""
        attr_value = attributes.get_attribute(self.attribute_type, self.attribute_name)
        if attr_value is None:
            return False
        
        actual_value = attr_value.value
        expected_value = self.value
        
        # Comparison operations
        ops = {
            ComparisonOperator.EQUALS: operator.eq,
            ComparisonOperator.NOT_EQUALS: operator.ne,
            ComparisonOperator.GREATER_THAN: operator.gt,
            ComparisonOperator.GREATER_THAN_OR_EQUAL: operator.ge,
            ComparisonOperator.LESS_THAN: operator.lt,
            ComparisonOperator.LESS_THAN_OR_EQUAL: operator.le,
        }
        
        if self.operator in ops:
            try:
                return ops[self.operator](actual_value, expected_value)
            except (TypeError, ValueError):
                return False
        
        # Collection operations
        elif self.operator == ComparisonOperator.IN:
            return actual_value in expected_value if hasattr(expected_value, '__contains__') else False
        elif self.operator == ComparisonOperator.NOT_IN:
            return actual_value not in expected_value if hasattr(expected_value, '__contains__') else True
        elif self.operator == ComparisonOperator.CONTAINS:
            return expected_value in actual_value if hasattr(actual_value, '__contains__') else False
        elif self.operator == ComparisonOperator.NOT_CONTAINS:
            return expected_value not in actual_value if hasattr(actual_value, '__contains__') else True
        
        # Pattern matching operations
        elif self.operator == ComparisonOperator.MATCHES:
            try:
                return bool(re.match(str(expected_value), str(actual_value)))
            except re.error:
                return False
        elif self.operator == ComparisonOperator.NOT_MATCHES:
            try:
                return not bool(re.match(str(expected_value), str(actual_value)))
            except re.error:
                return True
        
        return False


@dataclass
class PolicyRule:
    """Represents a policy rule with conditions and logical operators."""
    conditions: List[Union[PolicyCondition, 'PolicyRule']]
    operator: LogicalOperator = LogicalOperator.AND
    
    def evaluate(self, attributes: Attributes) -> bool:
        """Evaluate rule against provided attributes."""
        if not self.conditions:
            return True
        
        results = []
        for condition in self.conditions:
            if isinstance(condition, (PolicyCondition, PolicyRule)):
                results.append(condition.evaluate(attributes))
            else:
                raise ABACError(f"Invalid condition type: {type(condition)}")
        
        if self.operator == LogicalOperator.AND:
            return all(results)
        elif self.operator == LogicalOperator.OR:
            return any(results)
        elif self.operator == LogicalOperator.NOT:
            # NOT operator should have exactly one condition
            if len(results) != 1:
                raise ABACError("NOT operator requires exactly one condition")
            return not results[0]
        
        return False


@dataclass
class Policy:
    """Represents an ABAC policy with rules and effects."""
    policy_id: str
    name: str
    description: str
    effect: PolicyEffect
    rules: List[PolicyRule]
    priority: int = 0
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate policy after initialization."""
        if not self.policy_id:
            raise ABACError("Policy ID cannot be empty")
        if not self.name:
            raise ABACError("Policy name cannot be empty")
        if not self.rules:
            raise ABACError("Policy must have at least one rule")
    
    def evaluate(self, attributes: Attributes) -> bool:
        """Evaluate policy against provided attributes."""
        if not self.enabled:
            return False
        
        # All rules must evaluate to True for policy to match
        for rule in self.rules:
            if not rule.evaluate(attributes):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to dictionary representation."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "effect": self.effect.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "rules": [self._rule_to_dict(rule) for rule in self.rules]
        }
    
    def _rule_to_dict(self, rule: PolicyRule) -> Dict[str, Any]:
        """Convert policy rule to dictionary representation."""
        return {
            "operator": rule.operator.value,
            "conditions": [
                self._condition_to_dict(cond) if isinstance(cond, PolicyCondition)
                else self._rule_to_dict(cond)
                for cond in rule.conditions
            ]
        }
    
    def _condition_to_dict(self, condition: PolicyCondition) -> Dict[str, Any]:
        """Convert policy condition to dictionary representation."""
        return {
            "attribute_type": condition.attribute_type.value,
            "attribute_name": condition.attribute_name,
            "operator": condition.operator.value,
            "value": condition.value
        }


@dataclass
class ABACContext:
    """Context for ABAC evaluation including attributes and metadata."""
    attributes: Attributes
    request_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate context after initialization."""
        if not self.request_id:
            raise ABACError("Request ID cannot be empty")
        if not isinstance(self.attributes, Attributes):
            raise ABACError("Attributes must be an instance of Attributes class")


class AttributeProvider(ABC):
    """Abstract base class for attribute providers."""
    
    @abstractmethod
    async def get_user_attributes(self, user_id: str) -> Dict[str, AttributeValue]:
        """Get user attributes by user ID."""
        pass
    
    @abstractmethod
    async def get_resource_attributes(self, resource_id: str) -> Dict[str, AttributeValue]:
        """Get resource attributes by resource ID."""
        pass
    
    @abstractmethod
    async def get_environment_attributes(self, context: Dict[str, Any]) -> Dict[str, AttributeValue]:
        """Get environment attributes from context."""
        pass
    
    @abstractmethod
    async def get_action_attributes(self, action: str) -> Dict[str, AttributeValue]:
        """Get action attributes by action name."""
        pass


class DefaultAttributeProvider(AttributeProvider):
    """Default implementation of attribute provider."""
    
    def __init__(self):
        """Initialize default attribute provider."""
        self._logger = get_security_logger()
        self._user_cache: Dict[str, Dict[str, AttributeValue]] = {}
        self._resource_cache: Dict[str, Dict[str, AttributeValue]] = {}
    
    async def get_user_attributes(self, user_id: str) -> Dict[str, AttributeValue]:
        """Get user attributes by user ID."""
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        
        # Default user attributes
        attributes = {
            "id": AttributeValue(user_id, "string", "default_provider"),
            "authenticated": AttributeValue(True, "boolean", "default_provider"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "default_provider")
        }
        
        self._user_cache[user_id] = attributes
        return attributes
    
    async def get_resource_attributes(self, resource_id: str) -> Dict[str, AttributeValue]:
        """Get resource attributes by resource ID."""
        if resource_id in self._resource_cache:
            return self._resource_cache[resource_id]
        
        # Default resource attributes
        attributes = {
            "id": AttributeValue(resource_id, "string", "default_provider"),
            "type": AttributeValue("unknown", "string", "default_provider"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "default_provider")
        }
        
        self._resource_cache[resource_id] = attributes
        return attributes
    
    async def get_environment_attributes(self, context: Dict[str, Any]) -> Dict[str, AttributeValue]:
        """Get environment attributes from context."""
        now = datetime.now(timezone.utc)
        
        attributes = {
            "current_time": AttributeValue(now, "datetime", "default_provider"),
            "day_of_week": AttributeValue(now.strftime("%A"), "string", "default_provider"),
            "hour": AttributeValue(now.hour, "integer", "default_provider"),
        }
        
        # Add context-specific attributes
        if "source_ip" in context:
            attributes["source_ip"] = AttributeValue(context["source_ip"], "string", "default_provider")
        if "user_agent" in context:
            attributes["user_agent"] = AttributeValue(context["user_agent"], "string", "default_provider")
        
        return attributes
    
    async def get_action_attributes(self, action: str) -> Dict[str, AttributeValue]:
        """Get action attributes by action name."""
        attributes = {
            "name": AttributeValue(action, "string", "default_provider"),
            "type": AttributeValue("api_call", "string", "default_provider"),
        }
        
        # Determine action category
        if action.lower().startswith(("get", "read", "list", "view")):
            attributes["category"] = AttributeValue("read", "string", "default_provider")
        elif action.lower().startswith(("post", "create", "add", "insert")):
            attributes["category"] = AttributeValue("create", "string", "default_provider")
        elif action.lower().startswith(("put", "patch", "update", "modify")):
            attributes["category"] = AttributeValue("update", "string", "default_provider")
        elif action.lower().startswith(("delete", "remove", "destroy")):
            attributes["category"] = AttributeValue("delete", "string", "default_provider")
        else:
            attributes["category"] = AttributeValue("other", "string", "default_provider")
        
        return attributes


class PolicyParser:
    """Parser for ABAC policy expressions."""
    
    def __init__(self):
        """Initialize policy parser."""
        self._logger = get_security_logger()
    
    def parse_policy_from_dict(self, policy_dict: Dict[str, Any]) -> Policy:
        """Parse policy from dictionary representation."""
        try:
            # Parse basic policy information
            policy_id = policy_dict.get("policy_id")
            name = policy_dict.get("name")
            description = policy_dict.get("description", "")
            effect = PolicyEffect(policy_dict.get("effect", "deny"))
            priority = policy_dict.get("priority", 0)
            enabled = policy_dict.get("enabled", True)
            
            # Parse rules
            rules_data = policy_dict.get("rules", [])
            rules = [self._parse_rule(rule_data) for rule_data in rules_data]
            
            # Parse timestamps
            created_at = self._parse_timestamp(policy_dict.get("created_at"))
            updated_at = self._parse_timestamp(policy_dict.get("updated_at"))
            
            return Policy(
                policy_id=policy_id,
                name=name,
                description=description,
                effect=effect,
                rules=rules,
                priority=priority,
                enabled=enabled,
                created_at=created_at,
                updated_at=updated_at
            )
        
        except (KeyError, ValueError, TypeError) as e:
            raise ABACError(f"Failed to parse policy: {e}")
    
    def _parse_rule(self, rule_data: Dict[str, Any]) -> PolicyRule:
        """Parse policy rule from dictionary."""
        operator = LogicalOperator(rule_data.get("operator", "and"))
        conditions_data = rule_data.get("conditions", [])
        
        conditions = []
        for cond_data in conditions_data:
            if "attribute_type" in cond_data:
                # This is a condition
                conditions.append(self._parse_condition(cond_data))
            else:
                # This is a nested rule
                conditions.append(self._parse_rule(cond_data))
        
        return PolicyRule(conditions=conditions, operator=operator)
    
    def _parse_condition(self, cond_data: Dict[str, Any]) -> PolicyCondition:
        """Parse policy condition from dictionary."""
        attribute_type = AttributeType(cond_data["attribute_type"])
        attribute_name = cond_data["attribute_name"]
        operator = ComparisonOperator(cond_data["operator"])
        value = cond_data["value"]
        
        return PolicyCondition(
            attribute_type=attribute_type,
            attribute_name=attribute_name,
            operator=operator,
            value=value
        )
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> datetime:
        """Parse timestamp string to datetime object."""
        if not timestamp_str:
            return datetime.now(timezone.utc)
        
        try:
            return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return datetime.now(timezone.utc)
    
    def parse_policy_from_json(self, json_str: str) -> Policy:
        """Parse policy from JSON string."""
        try:
            policy_dict = json.loads(json_str)
            return self.parse_policy_from_dict(policy_dict)
        except json.JSONDecodeError as e:
            raise ABACError(f"Invalid JSON policy: {e}")
    
    def parse_policy_from_file(self, file_path: Union[str, Path]) -> Policy:
        """Parse policy from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return self.parse_policy_from_json(f.read())
        except (IOError, OSError) as e:
            raise ABACError(f"Failed to read policy file {file_path}: {e}")


class PolicyStore:
    """Storage and management for ABAC policies."""
    
    def __init__(self):
        """Initialize policy store."""
        self._policies: Dict[str, Policy] = {}
        self._logger = get_security_logger()
    
    def add_policy(self, policy: Policy):
        """Add policy to store."""
        if not isinstance(policy, Policy):
            raise ABACError("Invalid policy type")
        
        self._policies[policy.policy_id] = policy
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=SecurityEventSeverity.LOW,
            message=f"Policy added: {policy.policy_id}",
            details={"policy_id": policy.policy_id, "policy_name": policy.name}
        ))
    
    def remove_policy(self, policy_id: str):
        """Remove policy from store."""
        if policy_id in self._policies:
            del self._policies[policy_id]
            
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.LOW,
                message=f"Policy removed: {policy_id}",
                details={"policy_id": policy_id}
            ))
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)
    
    def get_all_policies(self) -> List[Policy]:
        """Get all policies."""
        return list(self._policies.values())
    
    def get_enabled_policies(self) -> List[Policy]:
        """Get all enabled policies."""
        return [policy for policy in self._policies.values() if policy.enabled]
    
    def get_policies_by_priority(self) -> List[Policy]:
        """Get policies sorted by priority (highest first)."""
        return sorted(self._policies.values(), key=lambda p: p.priority, reverse=True)
    
    def clear(self):
        """Clear all policies from store."""
        self._policies.clear()
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=SecurityEventSeverity.MEDIUM,
            message="All policies cleared from store",
            details={}
        ))
    
    def load_policies_from_directory(self, directory_path: Union[str, Path]):
        """Load policies from JSON files in directory."""
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ABACError(f"Policy directory does not exist: {directory_path}")
        
        parser = PolicyParser()
        loaded_count = 0
        
        for policy_file in directory.glob("*.json"):
            try:
                policy = parser.parse_policy_from_file(policy_file)
                self.add_policy(policy)
                loaded_count += 1
            except ABACError as e:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUTHORIZATION,
                    severity=SecurityEventSeverity.HIGH,
                    message=f"Failed to load policy from {policy_file}: {e}",
                    details={"file_path": str(policy_file), "error": str(e)}
                ))
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=SecurityEventSeverity.LOW,
            message=f"Loaded {loaded_count} policies from directory",
            details={"directory": str(directory_path), "count": loaded_count}
        ))


class PolicyDecision:
    """Represents the result of a policy evaluation."""
    
    def __init__(
        self,
        decision: PolicyEffect,
        policy_id: Optional[str] = None,
        reason: Optional[str] = None,
        evaluated_policies: Optional[List[str]] = None,
        evaluation_time: Optional[datetime] = None
    ):
        self.decision = decision
        self.policy_id = policy_id
        self.reason = reason
        self.evaluated_policies = evaluated_policies or []
        self.evaluation_time = evaluation_time or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert decision to dictionary."""
        return {
            "decision": self.decision.value,
            "policy_id": self.policy_id,
            "reason": self.reason,
            "evaluated_policies": self.evaluated_policies,
            "evaluation_time": self.evaluation_time.isoformat()
        }


class PolicyEvaluator:
    """Evaluates policies with boolean logic and precedence rules."""
    
    def __init__(self, logger: Optional['SecurityLogger'] = None):
        self._logger = logger or get_security_logger()
    
    def evaluate_policies(
        self,
        policies: List[Policy],
        context: ABACContext,
        precedence_rule: str = "deny_overrides"
    ) -> PolicyDecision:
        """
        Evaluate multiple policies with precedence rules.
        
        Args:
            policies: List of policies to evaluate
            context: ABAC context with attributes
            precedence_rule: Rule for combining policy decisions
                - "deny_overrides": Any DENY decision overrides ALLOW
                - "allow_overrides": Any ALLOW decision overrides DENY
                - "first_applicable": First matching policy wins
                - "only_one_applicable": Error if multiple policies match
        
        Returns:
            PolicyDecision with final decision and reasoning
        """
        if not policies:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="No policies to evaluate",
                evaluated_policies=[]
            )
        
        # Sort policies by priority (highest first)
        sorted_policies = sorted(policies, key=lambda p: p.priority, reverse=True)
        
        evaluated_policies = []
        applicable_policies = []
        
        # Evaluate each policy
        for policy in sorted_policies:
            if not policy.enabled:
                continue
                
            evaluated_policies.append(policy.policy_id)
            
            try:
                if policy.evaluate(context.attributes):
                    applicable_policies.append(policy)
                    
                    self._logger.log_event(SecurityEvent(
                        event_type=SecurityEventType.AUTHORIZATION,
                        severity=SecurityEventSeverity.LOW,
                        message=f"Policy {policy.policy_id} matched",
                        details={
                            "policy_id": policy.policy_id,
                            "effect": policy.effect.value,
                            "request_id": context.request_id
                        }
                    ))
                    
                    # First applicable rule - return immediately
                    if precedence_rule == "first_applicable":
                        return PolicyDecision(
                            decision=policy.effect,
                            policy_id=policy.policy_id,
                            reason=f"First applicable policy: {policy.name}",
                            evaluated_policies=evaluated_policies
                        )
                        
            except Exception as e:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUTHORIZATION,
                    severity=SecurityEventSeverity.HIGH,
                    message=f"Error evaluating policy {policy.policy_id}: {e}",
                    details={
                        "policy_id": policy.policy_id,
                        "error": str(e),
                        "request_id": context.request_id
                    }
                ))
        
        # Apply precedence rules
        return self._apply_precedence_rule(
            applicable_policies, 
            precedence_rule, 
            evaluated_policies
        )
    
    def _apply_precedence_rule(
        self,
        applicable_policies: List[Policy],
        precedence_rule: str,
        evaluated_policies: List[str]
    ) -> PolicyDecision:
        """Apply precedence rule to determine final decision."""
        
        if not applicable_policies:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="No applicable policies found",
                evaluated_policies=evaluated_policies
            )
        
        if precedence_rule == "only_one_applicable":
            if len(applicable_policies) > 1:
                policy_ids = [p.policy_id for p in applicable_policies]
                raise ABACError(
                    f"Multiple policies applicable with 'only_one_applicable' rule: {policy_ids}"
                )
            
            policy = applicable_policies[0]
            return PolicyDecision(
                decision=policy.effect,
                policy_id=policy.policy_id,
                reason=f"Only applicable policy: {policy.name}",
                evaluated_policies=evaluated_policies
            )
        
        # Separate ALLOW and DENY policies
        allow_policies = [p for p in applicable_policies if p.effect == PolicyEffect.ALLOW]
        deny_policies = [p for p in applicable_policies if p.effect == PolicyEffect.DENY]
        
        if precedence_rule == "deny_overrides":
            if deny_policies:
                # Highest priority DENY policy wins
                deny_policy = max(deny_policies, key=lambda p: p.priority)
                return PolicyDecision(
                    decision=PolicyEffect.DENY,
                    policy_id=deny_policy.policy_id,
                    reason=f"Deny overrides - policy: {deny_policy.name}",
                    evaluated_policies=evaluated_policies
                )
            elif allow_policies:
                # Highest priority ALLOW policy wins
                allow_policy = max(allow_policies, key=lambda p: p.priority)
                return PolicyDecision(
                    decision=PolicyEffect.ALLOW,
                    policy_id=allow_policy.policy_id,
                    reason=f"Allow policy - policy: {allow_policy.name}",
                    evaluated_policies=evaluated_policies
                )
        
        elif precedence_rule == "allow_overrides":
            if allow_policies:
                # Highest priority ALLOW policy wins
                allow_policy = max(allow_policies, key=lambda p: p.priority)
                return PolicyDecision(
                    decision=PolicyEffect.ALLOW,
                    policy_id=allow_policy.policy_id,
                    reason=f"Allow overrides - policy: {allow_policy.name}",
                    evaluated_policies=evaluated_policies
                )
            elif deny_policies:
                # Highest priority DENY policy wins
                deny_policy = max(deny_policies, key=lambda p: p.priority)
                return PolicyDecision(
                    decision=PolicyEffect.DENY,
                    policy_id=deny_policy.policy_id,
                    reason=f"Deny policy - policy: {deny_policy.name}",
                    evaluated_policies=evaluated_policies
                )
        
        # Default to DENY if no clear decision
        return PolicyDecision(
            decision=PolicyEffect.DENY,
            reason="Default deny - no clear policy decision",
            evaluated_policies=evaluated_policies
        )


class ABACEngine:
    """Main ABAC engine for policy loading and evaluation."""
    
    def __init__(
        self,
        policy_store: Optional[PolicyStore] = None,
        attribute_provider: Optional[AttributeProvider] = None,
        logger: Optional['SecurityLogger'] = None
    ):
        self._policy_store = policy_store or PolicyStore()
        self._attribute_provider = attribute_provider or DefaultAttributeProvider()
        self._evaluator = PolicyEvaluator(logger)
        self._logger = logger or get_security_logger()
        self._cache_ttl = 300  # 5 minutes default cache TTL
        self._decision_cache: Dict[str, Tuple[PolicyDecision, datetime]] = {}
    
    async def evaluate_access(
        self,
        user_id: str,
        resource_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        precedence_rule: str = "deny_overrides",
        use_cache: bool = True
    ) -> PolicyDecision:
        """
        Evaluate access request against ABAC policies.
        
        Args:
            user_id: User identifier
            resource_id: Resource identifier  
            action: Action being performed
            context: Additional context information
            precedence_rule: Policy precedence rule
            use_cache: Whether to use decision caching
            
        Returns:
            PolicyDecision with access decision
        """
        request_id = f"{user_id}:{resource_id}:{action}:{hash(str(context))}"
        
        # Check cache first
        if use_cache and request_id in self._decision_cache:
            cached_decision, cached_time = self._decision_cache[request_id]
            if (datetime.now(timezone.utc) - cached_time).seconds < self._cache_ttl:
                self._logger.log_event(SecurityEvent(
                    event_type=SecurityEventType.AUTHORIZATION,
                    severity=SecurityEventSeverity.LOW,
                    message="Access decision served from cache",
                    details={"request_id": request_id, "decision": cached_decision.decision.value}
                ))
                return cached_decision
        
        try:
            # Collect attributes
            attributes = await self._collect_attributes(user_id, resource_id, action, context)
            
            # Create ABAC context
            abac_context = ABACContext(
                attributes=attributes,
                request_id=request_id,
                source_ip=context.get("source_ip") if context else None,
                user_agent=context.get("user_agent") if context else None,
                session_id=context.get("session_id") if context else None
            )
            
            # Get applicable policies
            policies = self._policy_store.get_enabled_policies()
            
            # Evaluate policies
            decision = self._evaluator.evaluate_policies(
                policies, abac_context, precedence_rule
            )
            
            # Cache decision
            if use_cache:
                self._decision_cache[request_id] = (decision, datetime.now(timezone.utc))
            
            # Log decision
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.MEDIUM if decision.decision == PolicyEffect.DENY else SecurityEventSeverity.LOW,
                message=f"Access decision: {decision.decision.value}",
                details={
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "action": action,
                    "decision": decision.decision.value,
                    "policy_id": decision.policy_id,
                    "reason": decision.reason,
                    "request_id": request_id
                }
            ))
            
            return decision
            
        except Exception as e:
            # Log error and default to DENY
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.HIGH,
                message=f"Error during access evaluation: {e}",
                details={
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "action": action,
                    "error": str(e),
                    "request_id": request_id
                }
            ))
            
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason=f"Evaluation error: {str(e)}",
                evaluated_policies=[]
            )
    
    async def _collect_attributes(
        self,
        user_id: str,
        resource_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Attributes:
        """Collect attributes from various sources."""
        attributes = Attributes()
        
        try:
            # Get user attributes
            user_attrs = await self._attribute_provider.get_user_attributes(user_id)
            for name, attr_value in user_attrs.items():
                attributes.set_attribute(AttributeType.USER, name, attr_value)
            
            # Get resource attributes
            resource_attrs = await self._attribute_provider.get_resource_attributes(resource_id)
            for name, attr_value in resource_attrs.items():
                attributes.set_attribute(AttributeType.RESOURCE, name, attr_value)
            
            # Get action attributes
            action_attrs = await self._attribute_provider.get_action_attributes(action)
            for name, attr_value in action_attrs.items():
                attributes.set_attribute(AttributeType.ACTION, name, attr_value)
            
            # Get environment attributes
            env_context = context or {}
            env_attrs = await self._attribute_provider.get_environment_attributes(env_context)
            for name, attr_value in env_attrs.items():
                attributes.set_attribute(AttributeType.ENVIRONMENT, name, attr_value)
                
        except Exception as e:
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.HIGH,
                message=f"Error collecting attributes: {e}",
                details={"error": str(e)}
            ))
            raise ABACError(f"Failed to collect attributes: {e}")
        
        return attributes
    
    def add_policy(self, policy: Policy):
        """Add policy to the engine."""
        self._policy_store.add_policy(policy)
        self._clear_cache()
    
    def remove_policy(self, policy_id: str):
        """Remove policy from the engine."""
        self._policy_store.remove_policy(policy_id)
        self._clear_cache()
    
    def load_policies_from_directory(self, directory_path: Union[str, Path]):
        """Load policies from directory."""
        self._policy_store.load_policies_from_directory(directory_path)
        self._clear_cache()
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get policy by ID."""
        return self._policy_store.get_policy(policy_id)
    
    def get_all_policies(self) -> List[Policy]:
        """Get all policies."""
        return self._policy_store.get_all_policies()
    
    def _clear_cache(self):
        """Clear decision cache."""
        self._decision_cache.clear()
        
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=SecurityEventSeverity.LOW,
            message="ABAC decision cache cleared",
            details={}
        ))
    
    def set_cache_ttl(self, ttl_seconds: int):
        """Set cache TTL in seconds."""
        self._cache_ttl = ttl_seconds
    
    async def re_evaluate_context(
        self,
        user_id: str,
        resource_id: str,
        action: str,
        new_context: Dict[str, Any],
        precedence_rule: str = "deny_overrides"
    ) -> PolicyDecision:
        """
        Re-evaluate access with updated context.
        This method forces a fresh evaluation without using cache.
        """
        return await self.evaluate_access(
            user_id=user_id,
            resource_id=resource_id,
            action=action,
            context=new_context,
            precedence_rule=precedence_rule,
            use_cache=False
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        valid_entries = 0
        expired_entries = 0
        
        for _, (_, cached_time) in self._decision_cache.items():
            if (now - cached_time).seconds < self._cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._decision_cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl": self._cache_ttl
        }


# =============================================================================
# ADVANCED ATTRIBUTE PROVIDERS
# =============================================================================

class DatabaseAttributeProvider(AttributeProvider):
    """Database-backed attribute provider for production use."""
    
    def __init__(self, db_connection=None, cache_ttl: int = 300):
        self._db = db_connection
        self._cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[Dict[str, AttributeValue], datetime]] = {}
    
    async def get_user_attributes(self, user_id: str) -> Dict[str, AttributeValue]:
        """Get user attributes from database with caching."""
        cache_key = f"user:{user_id}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_attrs, cached_time = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).seconds < self._cache_ttl:
                return cached_attrs
        
        # Simulate database query (replace with actual DB logic)
        attributes = {
            "id": AttributeValue(user_id, "string", "database"),
            "authenticated": AttributeValue(True, "boolean", "database"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "database"),
            # Add more attributes based on your user schema
        }
        
        # Cache the result
        self._cache[cache_key] = (attributes, datetime.now(timezone.utc))
        
        return attributes
    
    async def get_resource_attributes(self, resource_id: str) -> Dict[str, AttributeValue]:
        """Get resource attributes from database with caching."""
        cache_key = f"resource:{resource_id}"
        
        # Check cache first
        if cache_key in self._cache:
            cached_attrs, cached_time = self._cache[cache_key]
            if (datetime.now(timezone.utc) - cached_time).seconds < self._cache_ttl:
                return cached_attrs
        
        # Simulate database query (replace with actual DB logic)
        attributes = {
            "id": AttributeValue(resource_id, "string", "database"),
            "type": AttributeValue("document", "string", "database"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "database"),
            # Add more attributes based on your resource schema
        }
        
        # Cache the result
        self._cache[cache_key] = (attributes, datetime.now(timezone.utc))
        
        return attributes
    
    async def get_environment_attributes(self, context: Dict[str, Any]) -> Dict[str, AttributeValue]:
        """Get environment attributes with enhanced context."""
        current_time = datetime.now(timezone.utc)
        
        attributes = {
            "current_time": AttributeValue(current_time, "datetime", "system"),
            "day_of_week": AttributeValue(current_time.strftime("%A").lower(), "string", "system"),
            "hour": AttributeValue(current_time.hour, "integer", "system"),
            "is_business_hours": AttributeValue(9 <= current_time.hour <= 17, "boolean", "system"),
            "is_weekend": AttributeValue(current_time.weekday() >= 5, "boolean", "system"),
        }
        
        # Add context-specific attributes
        if "source_ip" in context:
            attributes["source_ip"] = AttributeValue(context["source_ip"], "string", "request")
            # Add IP-based attributes (geolocation, internal/external, etc.)
            attributes["is_internal_ip"] = AttributeValue(
                context["source_ip"].startswith(("192.168.", "10.", "172.")), 
                "boolean", "system"
            )
        
        if "user_agent" in context:
            attributes["user_agent"] = AttributeValue(context["user_agent"], "string", "request")
            # Add user agent analysis
            attributes["is_mobile"] = AttributeValue(
                "mobile" in context["user_agent"].lower(), 
                "boolean", "system"
            )
        
        if "session_id" in context:
            attributes["session_id"] = AttributeValue(context["session_id"], "string", "request")
        
        return attributes
    
    async def get_action_attributes(self, action: str) -> Dict[str, AttributeValue]:
        """Get action attributes with enhanced categorization."""
        attributes = {
            "name": AttributeValue(action, "string", "system"),
            "created_at": AttributeValue(datetime.now(timezone.utc), "datetime", "system")
        }
        
        # Enhanced action categorization
        action_lower = action.lower()
        
        if any(keyword in action_lower for keyword in ["get", "read", "view", "list", "fetch"]):
            attributes["category"] = AttributeValue("read", "string", "system")
            attributes["risk_level"] = AttributeValue("low", "string", "system")
        elif any(keyword in action_lower for keyword in ["post", "create", "add", "insert"]):
            attributes["category"] = AttributeValue("create", "string", "system")
            attributes["risk_level"] = AttributeValue("medium", "string", "system")
        elif any(keyword in action_lower for keyword in ["put", "patch", "update", "modify", "edit"]):
            attributes["category"] = AttributeValue("update", "string", "system")
            attributes["risk_level"] = AttributeValue("medium", "string", "system")
        elif any(keyword in action_lower for keyword in ["delete", "remove", "destroy"]):
            attributes["category"] = AttributeValue("delete", "string", "system")
            attributes["risk_level"] = AttributeValue("high", "string", "system")
        elif any(keyword in action_lower for keyword in ["admin", "manage", "configure"]):
            attributes["category"] = AttributeValue("admin", "string", "system")
            attributes["risk_level"] = AttributeValue("critical", "string", "system")
        else:
            attributes["category"] = AttributeValue("other", "string", "system")
            attributes["risk_level"] = AttributeValue("medium", "string", "system")
        
        return attributes


class CompositeAttributeProvider(AttributeProvider):
    """Composite attribute provider that combines multiple providers."""
    
    def __init__(self, providers: List[AttributeProvider]):
        self._providers = providers
    
    async def get_user_attributes(self, user_id: str) -> Dict[str, AttributeValue]:
        """Get user attributes from all providers and merge them."""
        merged_attributes = {}
        
        for provider in self._providers:
            try:
                attributes = await provider.get_user_attributes(user_id)
                merged_attributes.update(attributes)
            except Exception:
                # Continue with other providers if one fails
                continue
        
        return merged_attributes
    
    async def get_resource_attributes(self, resource_id: str) -> Dict[str, AttributeValue]:
        """Get resource attributes from all providers and merge them."""
        merged_attributes = {}
        
        for provider in self._providers:
            try:
                attributes = await provider.get_resource_attributes(resource_id)
                merged_attributes.update(attributes)
            except Exception:
                # Continue with other providers if one fails
                continue
        
        return merged_attributes
    
    async def get_environment_attributes(self, context: Dict[str, Any]) -> Dict[str, AttributeValue]:
        """Get environment attributes from all providers and merge them."""
        merged_attributes = {}
        
        for provider in self._providers:
            try:
                attributes = await provider.get_environment_attributes(context)
                merged_attributes.update(attributes)
            except Exception:
                # Continue with other providers if one fails
                continue
        
        return merged_attributes
    
    async def get_action_attributes(self, action: str) -> Dict[str, AttributeValue]:
        """Get action attributes from all providers and merge them."""
        merged_attributes = {}
        
        for provider in self._providers:
            try:
                attributes = await provider.get_action_attributes(action)
                merged_attributes.update(attributes)
            except Exception:
                # Continue with other providers if one fails
                continue
        
        return merged_attributes


# =============================================================================
# ABAC MIDDLEWARE FOR FASTAPI
# =============================================================================

class ABACMiddleware:
    """FastAPI middleware for ABAC enforcement."""
    
    def __init__(
        self,
        abac_engine: ABACEngine,
        extract_user_id: Optional[Callable] = None,
        extract_resource_id: Optional[Callable] = None,
        extract_action: Optional[Callable] = None,
        precedence_rule: str = "deny_overrides",
        skip_paths: Optional[List[str]] = None,
        logger: Optional['SecurityLogger'] = None
    ):
        self._engine = abac_engine
        self._extract_user_id = extract_user_id or self._default_extract_user_id
        self._extract_resource_id = extract_resource_id or self._default_extract_resource_id
        self._extract_action = extract_action or self._default_extract_action
        self._precedence_rule = precedence_rule
        self._skip_paths = skip_paths or ["/docs", "/redoc", "/openapi.json", "/health"]
        self._logger = logger or get_security_logger()
    
    def _default_extract_user_id(self, request) -> str:
        """Default user ID extraction from request."""
        # Try to get from JWT token
        if hasattr(request.state, "user_id"):
            return request.state.user_id
        
        # Try to get from headers
        user_id = request.headers.get("X-User-ID")
        if user_id:
            return user_id
        
        # Default to anonymous
        return "anonymous"
    
    def _default_extract_resource_id(self, request) -> str:
        """Default resource ID extraction from request."""
        # Try to get from path parameters
        if hasattr(request, "path_params"):
            for param_name in ["id", "resource_id", "item_id"]:
                if param_name in request.path_params:
                    return str(request.path_params[param_name])
        
        # Use the path as resource identifier
        return request.url.path
    
    def _default_extract_action(self, request) -> str:
        """Default action extraction from request."""
        method = request.method.lower()
        path = request.url.path
        
        # Create action from method and path
        return f"{method}_{path.replace('/', '_').strip('_')}"
    
    async def __call__(self, request, call_next):
        """Process request through ABAC middleware."""
        # Skip ABAC for certain paths
        if request.url.path in self._skip_paths:
            return await call_next(request)
        
        try:
            # Extract identifiers
            user_id = self._extract_user_id(request)
            resource_id = self._extract_resource_id(request)
            action = self._extract_action(request)
            
            # Build context
            context = {
                "source_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("User-Agent"),
                "session_id": request.headers.get("X-Session-ID"),
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
            }
            
            # Evaluate access
            decision = await self._engine.evaluate_access(
                user_id=user_id,
                resource_id=resource_id,
                action=action,
                context=context,
                precedence_rule=self._precedence_rule
            )
            
            # Log the decision
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.MEDIUM if decision.decision == PolicyEffect.DENY else SecurityEventSeverity.LOW,
                message=f"ABAC decision: {decision.decision.value}",
                details={
                    "user_id": user_id,
                    "resource_id": resource_id,
                    "action": action,
                    "decision": decision.decision.value,
                    "policy_id": decision.policy_id,
                    "reason": decision.reason,
                    "source_ip": context.get("source_ip"),
                    "path": request.url.path,
                    "method": request.method
                }
            ))
            
            # Enforce decision
            if decision.decision == PolicyEffect.DENY:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Access Denied",
                        "reason": decision.reason,
                        "policy_id": decision.policy_id
                    }
                )
            
            # Store decision in request state for later use
            request.state.abac_decision = decision
            
            # Continue with request
            response = await call_next(request)
            
            return response
            
        except Exception as e:
            # Log error and deny by default
            self._logger.log_event(SecurityEvent(
                event_type=SecurityEventType.AUTHORIZATION,
                severity=SecurityEventSeverity.HIGH,
                message=f"ABAC middleware error: {e}",
                details={
                    "error": str(e),
                    "path": request.url.path,
                    "method": request.method,
                    "source_ip": request.client.host if request.client else None
                }
            ))
            
            # Default to deny on error
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail="Internal security error"
            )
    
    def create_fastapi_middleware(self):
        """Create FastAPI middleware instance."""
        from starlette.middleware.base import BaseHTTPMiddleware
        
        class ABACHTTPMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, abac_middleware: ABACMiddleware):
                super().__init__(app)
                self.abac_middleware = abac_middleware
            
            async def dispatch(self, request, call_next):
                return await self.abac_middleware(request, call_next)
        
        return ABACHTTPMiddleware


# =============================================================================
# FASTAPI INTEGRATION HELPERS
# =============================================================================

def setup_abac_middleware(
    app,
    abac_engine: ABACEngine,
    extract_user_id: Optional[Callable] = None,
    extract_resource_id: Optional[Callable] = None,
    extract_action: Optional[Callable] = None,
    precedence_rule: str = "deny_overrides",
    skip_paths: Optional[List[str]] = None
):
    """
    Setup ABAC middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
        abac_engine: ABAC engine instance
        extract_user_id: Function to extract user ID from request
        extract_resource_id: Function to extract resource ID from request
        extract_action: Function to extract action from request
        precedence_rule: Policy precedence rule
        skip_paths: Paths to skip ABAC enforcement
    
    Example:
        from fastapi import FastAPI
        from fastapi_microservices_sdk.security.advanced.abac import setup_abac_middleware, ABACEngine
        
        app = FastAPI()
        engine = ABACEngine()
        
        setup_abac_middleware(app, engine)
    """
    middleware = ABACMiddleware(
        abac_engine=abac_engine,
        extract_user_id=extract_user_id,
        extract_resource_id=extract_resource_id,
        extract_action=extract_action,
        precedence_rule=precedence_rule,
        skip_paths=skip_paths
    )
    
    app.add_middleware(middleware.create_fastapi_middleware(), abac_middleware=middleware)


def abac_protected(
    resource_type: Optional[str] = None,
    action_override: Optional[str] = None,
    precedence_rule: str = "deny_overrides"
):
    """
    Decorator to mark endpoints as ABAC protected.
    
    Args:
        resource_type: Override resource type for this endpoint
        action_override: Override action for this endpoint
        precedence_rule: Policy precedence rule for this endpoint
    
    Example:
        @app.get("/users/{user_id}")
        @abac_protected(resource_type="user", action_override="read_user")
        async def get_user(user_id: str):
            return {"user_id": user_id}
    """
    def decorator(func):
        # Store ABAC metadata on the function
        func._abac_protected = True
        func._abac_resource_type = resource_type
        func._abac_action_override = action_override
        func._abac_precedence_rule = precedence_rule
        return func
    
    return decorator


def get_abac_decision(request):
    """
    Get ABAC decision from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        PolicyDecision if available, None otherwise
        
    Example:
        from fastapi import Request, Depends
        
        @app.get("/protected")
        async def protected_endpoint(request: Request):
            decision = get_abac_decision(request)
            return {"decision": decision.to_dict() if decision else None}
    """
    return getattr(request.state, "abac_decision", None)


# =============================================================================
# POLICY CONFLICT RESOLUTION
# =============================================================================

class PolicyConflictResolver:
    """Advanced policy conflict resolution with multiple strategies."""
    
    def __init__(self, logger: Optional['SecurityLogger'] = None):
        self._logger = logger or get_security_logger()
    
    def resolve_conflicts(
        self,
        decisions: List[PolicyDecision],
        strategy: str = "deny_overrides"
    ) -> PolicyDecision:
        """
        Resolve conflicts between multiple policy decisions.
        
        Args:
            decisions: List of policy decisions to resolve
            strategy: Conflict resolution strategy
            
        Returns:
            Final resolved policy decision
        """
        if not decisions:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="No decisions to resolve"
            )
        
        if len(decisions) == 1:
            return decisions[0]
        
        # Log conflict detection
        self._logger.log_event(SecurityEvent(
            event_type=SecurityEventType.AUTHORIZATION,
            severity=SecurityEventSeverity.MEDIUM,
            message=f"Policy conflict detected, using {strategy} strategy",
            details={
                "decision_count": len(decisions),
                "strategy": strategy,
                "decisions": [d.to_dict() for d in decisions]
            }
        ))
        
        if strategy == "deny_overrides":
            return self._deny_overrides(decisions)
        elif strategy == "allow_overrides":
            return self._allow_overrides(decisions)
        elif strategy == "first_applicable":
            return decisions[0]
        elif strategy == "unanimous":
            return self._unanimous(decisions)
        elif strategy == "majority":
            return self._majority(decisions)
        else:
            # Default to deny_overrides
            return self._deny_overrides(decisions)
    
    def _deny_overrides(self, decisions: List[PolicyDecision]) -> PolicyDecision:
        """Deny overrides strategy - any DENY wins."""
        deny_decisions = [d for d in decisions if d.decision == PolicyEffect.DENY]
        if deny_decisions:
            return deny_decisions[0]
        
        allow_decisions = [d for d in decisions if d.decision == PolicyEffect.ALLOW]
        if allow_decisions:
            return allow_decisions[0]
        
        return PolicyDecision(
            decision=PolicyEffect.DENY,
            reason="No clear decision in deny_overrides resolution"
        )
    
    def _allow_overrides(self, decisions: List[PolicyDecision]) -> PolicyDecision:
        """Allow overrides strategy - any ALLOW wins."""
        allow_decisions = [d for d in decisions if d.decision == PolicyEffect.ALLOW]
        if allow_decisions:
            return allow_decisions[0]
        
        deny_decisions = [d for d in decisions if d.decision == PolicyEffect.DENY]
        if deny_decisions:
            return deny_decisions[0]
        
        return PolicyDecision(
            decision=PolicyEffect.DENY,
            reason="No clear decision in allow_overrides resolution"
        )
    
    def _unanimous(self, decisions: List[PolicyDecision]) -> PolicyDecision:
        """Unanimous strategy - all decisions must agree."""
        if all(d.decision == PolicyEffect.ALLOW for d in decisions):
            return PolicyDecision(
                decision=PolicyEffect.ALLOW,
                reason="Unanimous ALLOW decision"
            )
        elif all(d.decision == PolicyEffect.DENY for d in decisions):
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="Unanimous DENY decision"
            )
        else:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="No unanimous decision - defaulting to DENY"
            )
    
    def _majority(self, decisions: List[PolicyDecision]) -> PolicyDecision:
        """Majority strategy - majority decision wins."""
        allow_count = sum(1 for d in decisions if d.decision == PolicyEffect.ALLOW)
        deny_count = sum(1 for d in decisions if d.decision == PolicyEffect.DENY)
        
        if allow_count > deny_count:
            return PolicyDecision(
                decision=PolicyEffect.ALLOW,
                reason=f"Majority ALLOW decision ({allow_count}/{len(decisions)})"
            )
        elif deny_count > allow_count:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason=f"Majority DENY decision ({deny_count}/{len(decisions)})"
            )
        else:
            return PolicyDecision(
                decision=PolicyEffect.DENY,
                reason="Tie in majority vote - defaulting to DENY"
            )


# =============================================================================
# ABAC FACTORY AND BUILDER PATTERNS
# =============================================================================

class ABACEngineBuilder:
    """Builder pattern for creating ABAC engines with different configurations."""
    
    def __init__(self):
        self._policy_store = None
        self._attribute_provider = None
        self._logger = None
        self._cache_ttl = 300
        self._precedence_rule = "deny_overrides"
    
    def with_policy_store(self, policy_store: PolicyStore) -> 'ABACEngineBuilder':
        """Set policy store."""
        self._policy_store = policy_store
        return self
    
    def with_attribute_provider(self, provider: AttributeProvider) -> 'ABACEngineBuilder':
        """Set attribute provider."""
        self._attribute_provider = provider
        return self
    
    def with_logger(self, logger: 'SecurityLogger') -> 'ABACEngineBuilder':
        """Set security logger."""
        self._logger = logger
        return self
    
    def with_cache_ttl(self, ttl_seconds: int) -> 'ABACEngineBuilder':
        """Set cache TTL."""
        self._cache_ttl = ttl_seconds
        return self
    
    def with_precedence_rule(self, rule: str) -> 'ABACEngineBuilder':
        """Set default precedence rule."""
        self._precedence_rule = rule
        return self
    
    def with_database_provider(self, db_connection=None) -> 'ABACEngineBuilder':
        """Add database attribute provider."""
        self._attribute_provider = DatabaseAttributeProvider(db_connection)
        return self
    
    def with_composite_provider(self, providers: List[AttributeProvider]) -> 'ABACEngineBuilder':
        """Add composite attribute provider."""
        self._attribute_provider = CompositeAttributeProvider(providers)
        return self
    
    def build(self) -> ABACEngine:
        """Build the ABAC engine."""
        engine = ABACEngine(
            policy_store=self._policy_store,
            attribute_provider=self._attribute_provider,
            logger=self._logger
        )
        
        if self._cache_ttl != 300:
            engine.set_cache_ttl(self._cache_ttl)
        
        return engine


def create_abac_engine(
    policy_directory: Optional[str] = None,
    attribute_provider: Optional[AttributeProvider] = None,
    cache_ttl: int = 300,
    precedence_rule: str = "deny_overrides"
) -> ABACEngine:
    """
    Factory function to create ABAC engine with common configurations.
    
    Args:
        policy_directory: Directory containing policy JSON files
        attribute_provider: Custom attribute provider
        cache_ttl: Cache TTL in seconds
        precedence_rule: Default precedence rule
        
    Returns:
        Configured ABAC engine
        
    Example:
        engine = create_abac_engine(
            policy_directory="./policies",
            cache_ttl=600
        )
    """
    builder = ABACEngineBuilder()
    
    # Set up policy store
    policy_store = PolicyStore()
    if policy_directory:
        policy_store.load_policies_from_directory(policy_directory)
    builder.with_policy_store(policy_store)
    
    # Set up attribute provider
    if attribute_provider:
        builder.with_attribute_provider(attribute_provider)
    else:
        builder.with_attribute_provider(DefaultAttributeProvider())
    
    # Configure cache and precedence
    builder.with_cache_ttl(cache_ttl)
    builder.with_precedence_rule(precedence_rule)
    
    return builder.build()


# =============================================================================
# Aliases for backward compatibility and convenience
# =============================================================================

# ABACManager is an alias for ABACEngine for better naming consistency
ABACManager = ABACEngine
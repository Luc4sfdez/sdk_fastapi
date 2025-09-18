"""
Template Validator - Advanced validation system for templates
"""
import re
import json
import yaml
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import ast
import logging

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    level: ValidationLevel
    message: str
    line: Optional[int] = None
    column: Optional[int] = None
    rule: Optional[str] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    score: int
    issues: List[ValidationIssue]
    suggestions: List[str]
    passed: bool

class TemplateValidator:
    """Advanced template validation system"""
    
    def __init__(self):
        self.validation_rules = {
            'syntax': self._validate_syntax,
            'variables': self._validate_variables,
            'structure': self._validate_structure,
            'security': self._validate_security,
            'performance': self._validate_performance,
            'best_practices': self._validate_best_practices
        }
        
    def validate_template(self, template_content: str, template_type: str = "custom") -> ValidationResult:
        """Validate a template and return comprehensive results"""
        issues = []
        suggestions = []
        
        try:
            # Run all validation rules
            for rule_name, rule_func in self.validation_rules.items():
                try:
                    rule_issues, rule_suggestions = rule_func(template_content, template_type)
                    issues.extend(rule_issues)
                    suggestions.extend(rule_suggestions)
                except Exception as e:
                    logger.error(f"Error in validation rule {rule_name}: {e}")
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Validation rule '{rule_name}' failed: {str(e)}",
                        rule=rule_name
                    ))
            
            # Calculate score
            score = self._calculate_score(issues)
            passed = score >= 70  # Minimum passing score
            
            return ValidationResult(
                score=score,
                issues=issues,
                suggestions=suggestions,
                passed=passed
            )
            
        except Exception as e:
            logger.error(f"Template validation failed: {e}")
            return ValidationResult(
                score=0,
                issues=[ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Validation failed: {str(e)}"
                )],
                suggestions=[],
                passed=False
            )
    
    def _validate_syntax(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template syntax"""
        issues = []
        suggestions = []
        
        # Check for basic syntax issues
        if not content.strip():
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Template content is empty",
                rule="syntax"
            ))
            return issues, suggestions
        
        # Check for unmatched brackets/braces
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        for i, char in enumerate(content):
            if char in brackets:
                stack.append((char, i))
            elif char in brackets.values():
                if not stack:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Unmatched closing bracket '{char}'",
                        line=content[:i].count('\n') + 1,
                        column=i - content.rfind('\n', 0, i),
                        rule="syntax"
                    ))
                else:
                    open_char, _ = stack.pop()
                    if brackets[open_char] != char:
                        issues.append(ValidationIssue(
                            level=ValidationLevel.ERROR,
                            message=f"Mismatched brackets: '{open_char}' and '{char}'",
                            line=content[:i].count('\n') + 1,
                            column=i - content.rfind('\n', 0, i),
                            rule="syntax"
                        ))
        
        # Check for unclosed brackets
        for open_char, pos in stack:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message=f"Unclosed bracket '{open_char}'",
                line=content[:pos].count('\n') + 1,
                column=pos - content.rfind('\n', 0, pos),
                rule="syntax"
            ))
        
        # Validate specific formats
        if template_type in ['yaml', 'kubernetes']:
            try:
                yaml.safe_load(content)
            except yaml.YAMLError as e:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Invalid YAML syntax: {str(e)}",
                    rule="syntax"
                ))
        
        elif template_type == 'json':
            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Invalid JSON syntax: {str(e)}",
                    line=e.lineno,
                    column=e.colno,
                    rule="syntax"
                ))
        
        elif template_type == 'python':
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Invalid Python syntax: {str(e)}",
                    line=e.lineno,
                    column=e.offset,
                    rule="syntax"
                ))
        
        return issues, suggestions
    
    def _validate_variables(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template variables"""
        issues = []
        suggestions = []
        
        # Find all variable patterns
        variable_patterns = [
            r'\{\{(\s*\w+\s*)\}\}',  # Jinja2 style
            r'\$\{(\w+)\}',          # Shell style
            r'\%(\w+)\%',            # Windows style
            r'\<(\w+)\>',            # XML style
        ]
        
        found_variables = set()
        for pattern in variable_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                var_name = match.group(1).strip()
                found_variables.add(var_name)
        
        # Check for common variable naming issues
        for var in found_variables:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Variable '{var}' doesn't follow naming conventions",
                    rule="variables",
                    suggestion="Use alphanumeric characters and underscores only"
                ))
            
            if var.upper() == var and len(var) > 1:
                suggestions.append(f"Consider using lowercase for variable '{var}' unless it's a constant")
        
        # Check for undefined variables (basic check)
        if found_variables:
            suggestions.append("Ensure all variables are properly defined in template metadata")
        
        return issues, suggestions
    
    def _validate_structure(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template structure"""
        issues = []
        suggestions = []
        
        lines = content.split('\n')
        
        # Check for proper indentation
        if template_type in ['yaml', 'python']:
            indent_levels = []
            for i, line in enumerate(lines):
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    indent_levels.append(indent)
                    
                    # Check for inconsistent indentation
                    if i > 0 and indent_levels:
                        prev_indent = indent_levels[-2] if len(indent_levels) > 1 else 0
                        if indent > prev_indent and (indent - prev_indent) not in [2, 4]:
                            issues.append(ValidationIssue(
                                level=ValidationLevel.WARNING,
                                message=f"Inconsistent indentation on line {i+1}",
                                line=i+1,
                                rule="structure",
                                suggestion="Use consistent 2 or 4 space indentation"
                            ))
        
        # Check for very long lines
        for i, line in enumerate(lines):
            if len(line) > 120:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Line {i+1} is too long ({len(line)} characters)",
                    line=i+1,
                    rule="structure",
                    suggestion="Consider breaking long lines for better readability"
                ))
        
        # Check for empty template
        if len([line for line in lines if line.strip()]) < 3:
            issues.append(ValidationIssue(
                level=ValidationLevel.WARNING,
                message="Template appears to be very short",
                rule="structure",
                suggestion="Consider adding more content or documentation"
            ))
        
        return issues, suggestions
    
    def _validate_security(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template security"""
        issues = []
        suggestions = []
        
        # Check for potential security issues
        security_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token detected"),
            (r'eval\s*\(', "Use of eval() function detected"),
            (r'exec\s*\(', "Use of exec() function detected"),
            (r'__import__\s*\(', "Use of __import__() function detected"),
        ]
        
        for pattern, message in security_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=message,
                    line=line_num,
                    rule="security",
                    suggestion="Use environment variables or secure configuration instead"
                ))
        
        return issues, suggestions
    
    def _validate_performance(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template performance"""
        issues = []
        suggestions = []
        
        # Check for performance anti-patterns
        if template_type == 'python':
            # Check for inefficient loops
            if re.search(r'for\s+\w+\s+in\s+range\s*\(\s*len\s*\(', content):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message="Inefficient loop pattern detected",
                    rule="performance",
                    suggestion="Use 'for item in list' instead of 'for i in range(len(list))'"
                ))
        
        # Check for very large templates
        if len(content) > 10000:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                message="Template is very large",
                rule="performance",
                suggestion="Consider breaking into smaller, reusable templates"
            ))
        
        return issues, suggestions
    
    def _validate_best_practices(self, content: str, template_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """Validate template best practices"""
        issues = []
        suggestions = []
        
        lines = content.split('\n')
        
        # Check for documentation
        has_comments = any(line.strip().startswith('#') or line.strip().startswith('//') 
                          for line in lines)
        
        if not has_comments and len(lines) > 10:
            issues.append(ValidationIssue(
                level=ValidationLevel.INFO,
                message="Template lacks documentation/comments",
                rule="best_practices",
                suggestion="Add comments to explain complex logic"
            ))
        
        return issues, suggestions
    
    def _calculate_score(self, issues: List[ValidationIssue]) -> int:
        """Calculate validation score based on issues"""
        base_score = 100
        
        for issue in issues:
            if issue.level == ValidationLevel.ERROR:
                base_score -= 20
            elif issue.level == ValidationLevel.WARNING:
                base_score -= 10
            elif issue.level == ValidationLevel.INFO:
                base_score -= 2
        
        return max(0, base_score)
    
    def get_validation_summary(self, result: ValidationResult) -> Dict[str, Any]:
        """Get a summary of validation results"""
        error_count = sum(1 for issue in result.issues if issue.level == ValidationLevel.ERROR)
        warning_count = sum(1 for issue in result.issues if issue.level == ValidationLevel.WARNING)
        info_count = sum(1 for issue in result.issues if issue.level == ValidationLevel.INFO)
        
        return {
            'score': result.score,
            'passed': result.passed,
            'total_issues': len(result.issues),
            'errors': error_count,
            'warnings': warning_count,
            'info': info_count,
            'suggestions_count': len(result.suggestions)
        }
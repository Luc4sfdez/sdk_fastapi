"""
CLI Framework Core

Core CLI framework with command registration and execution.
"""

from typing import Dict, List, Optional, Any, Callable
from abc import ABC, abstractmethod
import argparse
import sys
from dataclasses import dataclass, field

from .context import CLIContext
from .exceptions import CLIError, CommandError, CommandNotFoundError, ArgumentError


@dataclass
class Argument:
    """Command argument definition."""
    name: str
    help: str
    type: type = str
    required: bool = True
    default: Any = None
    choices: Optional[List[Any]] = None
    
    def add_to_parser(self, parser: argparse.ArgumentParser) -> None:
        """Add argument to argument parser."""
        kwargs = {
            'help': self.help,
            'type': self.type
        }
        
        if not self.required:
            kwargs['default'] = self.default
            kwargs['nargs'] = '?'
        
        if self.choices:
            kwargs['choices'] = self.choices
        
        parser.add_argument(self.name, **kwargs)


@dataclass
class Option:
    """Command option definition."""
    name: str
    short_name: Optional[str]
    help: str
    type: type = str
    default: Any = None
    action: str = 'store'
    choices: Optional[List[Any]] = None
    
    def add_to_parser(self, parser: argparse.ArgumentParser) -> None:
        """Add option to argument parser."""
        names = [f'--{self.name}']
        if self.short_name:
            names.append(f'-{self.short_name}')
        
        kwargs = {
            'help': self.help,
            'action': self.action,
            'default': self.default
        }
        
        if self.action == 'store':
            kwargs['type'] = self.type
        
        if self.choices:
            kwargs['choices'] = self.choices
        
        parser.add_argument(*names, **kwargs)


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    exit_code: int = 0


class Command(ABC):
    """Base command class."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.arguments: List[Argument] = []
        self.options: List[Option] = []
        self._setup_arguments()
    
    @abstractmethod
    def _setup_arguments(self) -> None:
        """Setup command arguments and options."""
        pass
    
    @abstractmethod
    def execute(self, context: CLIContext, args: argparse.Namespace) -> CommandResult:
        """Execute command with given context and arguments."""
        pass
    
    def add_argument(self, name: str, help: str, **kwargs) -> None:
        """Add command argument."""
        argument = Argument(name=name, help=help, **kwargs)
        self.arguments.append(argument)
    
    def add_option(self, name: str, help: str, short_name: Optional[str] = None, **kwargs) -> None:
        """Add command option."""
        option = Option(name=name, short_name=short_name, help=help, **kwargs)
        self.options.append(option)
    
    def create_parser(self, parent_parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
        """Create argument parser for command."""
        if parent_parser:
            parser = parent_parser.add_parser(self.name, help=self.description)
        else:
            parser = argparse.ArgumentParser(description=self.description)
        
        # Add arguments
        for argument in self.arguments:
            argument.add_to_parser(parser)
        
        # Add options
        for option in self.options:
            option.add_to_parser(parser)
        
        return parser
    
    def validate_args(self, args: argparse.Namespace) -> None:
        """Validate command arguments."""
        # Override in subclasses for custom validation
        pass


class CommandRegistry:
    """Registry for CLI commands."""
    
    def __init__(self):
        self.commands: Dict[str, Command] = {}
        self.aliases: Dict[str, str] = {}
    
    def register(self, command: Command, aliases: Optional[List[str]] = None) -> None:
        """Register command with optional aliases."""
        self.commands[command.name] = command
        
        if aliases:
            for alias in aliases:
                self.aliases[alias] = command.name
    
    def get_command(self, name: str) -> Optional[Command]:
        """Get command by name or alias."""
        # Check direct name
        if name in self.commands:
            return self.commands[name]
        
        # Check aliases
        if name in self.aliases:
            return self.commands[self.aliases[name]]
        
        return None
    
    def list_commands(self) -> List[str]:
        """List all registered command names."""
        return list(self.commands.keys())
    
    def get_command_names(self) -> List[str]:
        """Get all command names including aliases."""
        names = list(self.commands.keys())
        names.extend(self.aliases.keys())
        return sorted(names)


class CLIFramework:
    """Main CLI framework."""
    
    def __init__(self, name: str = "fastapi-sdk", description: str = "FastAPI Microservices SDK CLI"):
        self.name = name
        self.description = description
        self.registry = CommandRegistry()
        self.context: Optional[CLIContext] = None
        self._setup_global_options()
    
    def _setup_global_options(self) -> None:
        """Setup global CLI options."""
        self.global_options = [
            Option(
                name='verbose',
                short_name='v',
                help='Enable verbose output',
                action='store_true'
            ),
            Option(
                name='quiet',
                short_name='q',
                help='Suppress output',
                action='store_true'
            ),
            Option(
                name='dry-run',
                help='Show what would be done without executing',
                action='store_true'
            ),
            Option(
                name='config',
                short_name='c',
                help='Path to configuration file',
                type=str
            )
        ]
    
    def register_command(self, command: Command, aliases: Optional[List[str]] = None) -> None:
        """Register command with framework."""
        self.registry.register(command, aliases)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create main argument parser."""
        parser = argparse.ArgumentParser(
            prog=self.name,
            description=self.description,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Add global options
        for option in self.global_options:
            option.add_to_parser(parser)
        
        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            metavar='COMMAND'
        )
        
        # Add commands
        for command_name, command in self.registry.commands.items():
            command.create_parser(subparsers)
        
        return parser
    
    def execute_command(self, command_name: str, args: argparse.Namespace) -> CommandResult:
        """Execute command with given arguments."""
        command = self.registry.get_command(command_name)
        if not command:
            raise CommandNotFoundError(
                command_name=command_name,
                available_commands=self.registry.list_commands()
            )
        
        try:
            # Validate arguments
            command.validate_args(args)
            
            # Execute command
            return command.execute(self.context, args)
            
        except Exception as e:
            if isinstance(e, CLIError):
                raise
            else:
                raise CommandError(
                    command_name=command_name,
                    error_message=str(e)
                )
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """Run CLI with given arguments."""
        try:
            # Parse arguments
            parser = self.create_parser()
            args = parser.parse_args(argv)
            
            # Create context
            self.context = CLIContext.create(
                config_path=getattr(args, 'config', None),
                verbose=getattr(args, 'verbose', False),
                quiet=getattr(args, 'quiet', False),
                dry_run=getattr(args, 'dry_run', False)
            )
            
            # Check if command was provided
            if not hasattr(args, 'command') or not args.command:
                parser.print_help()
                return 0
            
            # Execute command
            result = self.execute_command(args.command, args)
            
            # Print result message
            if result.message:
                if result.success:
                    self.context.print_success(result.message)
                else:
                    self.context.print_error(result.message)
            
            return result.exit_code
            
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
            return 130
            
        except CLIError as e:
            print(f"❌ {e.message}")
            if hasattr(e, 'details') and e.details and self.context and self.context.verbose:
                print(f"🔍 Details: {e.details}")
            return e.exit_code
            
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            if self.context and self.context.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    def add_completion_support(self) -> None:
        """Add shell completion support."""
        # This would integrate with argcomplete or similar
        # for shell auto-completion
        pass


def create_cli() -> CLIFramework:
    """Create and configure CLI framework with default commands."""
    from .commands import (
        CreateCommand,
        GenerateCommand,
        ListCommand,
        ConfigCommand,
        InitCommand
    )
    
    cli = CLIFramework()
    
    # Register core commands
    cli.register_command(CreateCommand(), ['new'])
    cli.register_command(GenerateCommand(), ['gen'])
    cli.register_command(ListCommand(), ['ls'])
    cli.register_command(ConfigCommand(), ['cfg'])
    cli.register_command(InitCommand())
    
    return cli
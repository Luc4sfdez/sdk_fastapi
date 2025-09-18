"""
Console utilities for cross-platform compatibility.
"""

import sys
from rich import print as rprint


def safe_print(message: str, style: str = "") -> None:
    """Print message with emoji fallback for Windows compatibility."""
    
    # Emoji to text mapping for Windows compatibility
    emoji_fallbacks = {
        "✅": "[SUCCESS]",
        "❌": "[ERROR]", 
        "⚠️": "[WARNING]",
        "🚀": "[ROCKET]",
        "📁": "[FOLDER]",
        "📄": "[FILE]",
        "🔧": "[TOOL]",
        "🎉": "[PARTY]",
        "💾": "[SAVE]",
        "🛑": "[STOP]",
        "🏥": "[HEALTH]",
        "⏱️": "[TIME]",
        "📊": "[CHART]",
        "⏳": "[HOURGLASS]",
        "🛠️": "[TOOLS]",
        "🐳": "[DOCKER]",
        "☸️": "[K8S]",
        "🔄": "[CYCLE]",
        "🏗️": "[CONSTRUCTION]",
        "🔐": "[LOCK]",
        "📨": "[MESSAGE]",
        "⚙️": "[GEAR]"
    }
    
    # Replace emojis with text on Windows or if encoding issues
    try:
        # Test if we can encode emojis
        "✅".encode(sys.stdout.encoding or 'utf-8')
        safe_message = message
    except (UnicodeEncodeError, LookupError):
        safe_message = message
        for emoji, fallback in emoji_fallbacks.items():
            safe_message = safe_message.replace(emoji, fallback)
    
    # Apply style if provided
    if style:
        safe_message = f"[{style}]{safe_message}[/{style}]"
    
    try:
        rprint(safe_message)
    except UnicodeEncodeError:
        # Final fallback - strip all non-ASCII
        ascii_message = safe_message.encode('ascii', 'ignore').decode('ascii')
        print(ascii_message)


def success(message: str) -> None:
    """Print success message."""
    safe_print(f"✅ {message}", "green")


def error(message: str) -> None:
    """Print error message.""" 
    safe_print(f"❌ {message}", "red")


def warning(message: str) -> None:
    """Print warning message."""
    safe_print(f"⚠️ {message}", "yellow")


def info(message: str) -> None:
    """Print info message."""
    safe_print(f"📄 {message}", "blue")


def folder(message: str) -> None:
    """Print folder message."""
    safe_print(f"📁 {message}")


def rocket(message: str) -> None:
    """Print rocket message."""
    safe_print(f"🚀 {message}", "blue")
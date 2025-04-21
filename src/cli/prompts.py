"""
User interaction prompts for the CLI.
"""
import os
import sys
from typing import Dict, Any, List, Optional, Callable, Union, Tuple

class Prompt:
    """
    Handles user interaction and prompts in the CLI.
    """
    
    @staticmethod
    def confirm(message: str, default: bool = True) -> bool:
        """
        Prompt the user for confirmation.
        
        Args:
            message: Confirmation message
            default: Default value (True for yes, False for no)
            
        Returns:
            True if confirmed, False otherwise
        """
        default_str = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_str}]: ").strip().lower()
        
        if not response:
            return default
        
        return response in ['y', 'yes']
    
    @staticmethod
    def input(message: str, default: Optional[str] = None) -> str:
        """
        Prompt the user for input.
        
        Args:
            message: Input message
            default: Default value
            
        Returns:
            User input
        """
        default_str = f" [{default}]" if default else ""
        response = input(f"{message}{default_str}: ").strip()
        
        if not response and default:
            return default
        
        return response
    
    @staticmethod
    def select(message: str, options: List[str], default_index: int = 0) -> str:
        """
        Prompt the user to select from a list of options.
        
        Args:
            message: Selection message
            options: List of options
            default_index: Default option index
            
        Returns:
            Selected option
        """
        print(f"{message}")
        
        for i, option in enumerate(options):
            default_marker = " (default)" if i == default_index else ""
            print(f"{i + 1}. {option}{default_marker}")
        
        while True:
            response = input("Enter your choice [1-{}]: ".format(len(options))).strip()
            
            if not response:
                return options[default_index]
            
            try:
                choice = int(response)
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a number")
    
    @staticmethod
    def multi_select(message: str, options: List[str], default_indices: List[int] = None) -> List[str]:
        """
        Prompt the user to select multiple options from a list.
        
        Args:
            message: Selection message
            options: List of options
            default_indices: Default selected indices
            
        Returns:
            List of selected options
        """
        if default_indices is None:
            default_indices = []
        
        print(f"{message}")
        
        for i, option in enumerate(options):
            default_marker = " (default)" if i in default_indices else ""
            print(f"{i + 1}. {option}{default_marker}")
        
        while True:
            response = input("Enter your choices (comma-separated) [1-{}]: ".format(len(options))).strip()
            
            if not response:
                return [options[i] for i in default_indices]
            
            try:
                choices = [int(choice.strip()) for choice in response.split(',')]
                if all(1 <= choice <= len(options) for choice in choices):
                    return [options[choice - 1] for choice in choices]
                else:
                    print(f"Please enter numbers between 1 and {len(options)}")
            except ValueError:
                print("Please enter comma-separated numbers")
    
    @staticmethod
    def progress(message: str, total: int) -> Callable[[int], None]:
        """
        Create a progress indicator.
        
        Args:
            message: Progress message
            total: Total number of steps
            
        Returns:
            Update function for the progress indicator
        """
        if not sys.stdout.isatty():
            # Not a terminal, return no-op
            return lambda _: None
        
        def update(current: int) -> None:
            """
            Update the progress indicator.
            
            Args:
                current: Current progress value
            """
            if current > total:
                current = total
            
            percentage = int(100 * current / total)
            bar_length = 30
            filled_length = int(bar_length * current / total)
            
            bar = '█' * filled_length + '-' * (bar_length - filled_length)
            
            sys.stdout.write(f'\r{message} [{bar}] {percentage}% ({current}/{total})')
            sys.stdout.flush()
            
            if current == total:
                sys.stdout.write('\n')
                sys.stdout.flush()
        
        return update
    
    @staticmethod
    def spinner(message: str) -> Tuple[Callable[[], None], Callable[[], None]]:
        """
        Create a spinner for long-running operations.
        
        Args:
            message: Spinner message
            
        Returns:
            Tuple of (start, stop) functions
        """
        if not sys.stdout.isatty():
            # Not a terminal, return no-ops
            return (lambda: None, lambda: None)
        
        import threading
        import itertools
        import time
        
        spinner_chars = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        stop_spinner = False
        
        def spin() -> None:
            """Spinner animation function."""
            while not stop_spinner:
                sys.stdout.write(f'\r{message} {next(spinner_chars)}')
                sys.stdout.flush()
                time.sleep(0.1)
                sys.stdout.write('\r\033[K')
                sys.stdout.flush()
        
        def start() -> None:
            """Start the spinner."""
            nonlocal stop_spinner
            stop_spinner = False
            spinner_thread = threading.Thread(target=spin)
            spinner_thread.daemon = True
            spinner_thread.start()
        
        def stop() -> None:
            """Stop the spinner."""
            nonlocal stop_spinner
            stop_spinner = True
            sys.stdout.write(f'\r{message} Done!\n')
            sys.stdout.flush()
        
        return (start, stop)
    
    @staticmethod
    def print_table(headers: List[str], rows: List[List[str]], title: Optional[str] = None) -> None:
        """
        Print a formatted table.
        
        Args:
            headers: Table headers
            rows: Table rows
            title: Optional table title
        """
        if not headers or not rows:
            return
        
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = max(col_widths[i], len(str(cell)))
        
        # Calculate total width
        total_width = sum(col_widths) + len(headers) * 3 - 1
        
        # Print title if provided
        if title:
            print('=' * total_width)
            print(title.center(total_width))
            print('=' * total_width)
        
        # Print header
        header_row = ' | '.join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        print(header_row)
        print('-' * total_width)
        
        # Print rows
        for row in rows:
            row_str = ' | '.join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row) if i < len(col_widths))
            print(row_str)
    
    @staticmethod
    def print_success(message: str) -> None:
        """
        Print a success message.
        
        Args:
            message: Success message
        """
        print(f"\u001b[32m✓ {message}\u001b[0m")
    
    @staticmethod
    def print_error(message: str) -> None:
        """
        Print an error message.
        
        Args:
            message: Error message
        """
        print(f"\u001b[31m✗ {message}\u001b[0m")
    
    @staticmethod
    def print_warning(message: str) -> None:
        """
        Print a warning message.
        
        Args:
            message: Warning message
        """
        print(f"\u001b[33m! {message}\u001b[0m")
    
    @staticmethod
    def print_info(message: str) -> None:
        """
        Print an info message.
        
        Args:
            message: Info message
        """
        print(f"\u001b[34mℹ {message}\u001b[0m")
    
    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    @staticmethod
    def wait_for_keypress(message: str = "Press any key to continue...") -> None:
        """
        Wait for a keypress.
        
        Args:
            message: Message to display
        """
        print(message, end='', flush=True)
        if os.name == 'nt':
            import msvcrt
            msvcrt.getch()
        else:
            import termios
            import tty
            
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        print()
    
    @staticmethod
    def password(message: str = "Enter password: ") -> str:
        """
        Prompt for password input with hidden characters.
        
        Args:
            message: Prompt message
            
        Returns:
            Password string
        """
        import getpass
        return getpass.getpass(message)
    
    @staticmethod
    def autocomplete(message: str, options: List[str]) -> str:
        """
        Prompt with tab completion.
        
        Args:
            message: Prompt message
            options: List of completion options
            
        Returns:
            User input with completion
        """
        try:
            import readline
            
            def completer(text, state):
                matches = [opt for opt in options if opt.startswith(text)]
                return matches[state] if state < len(matches) else None
            
            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer)
            
            result = input(f"{message}: ")
            readline.set_completer(None)
            return result
            
        except (ImportError, ModuleNotFoundError):
            # If readline is not available, fall back to regular input
            return input(f"{message}: ")
    
    @staticmethod
    def display_code(code: str, language: str = "", line_numbers: bool = True) -> None:
        """
        Display formatted code with optional syntax highlighting.
        
        Args:
            code: Code to display
            language: Programming language for syntax highlighting
            line_numbers: Whether to show line numbers
        """
        try:
            from pygments import highlight
            from pygments.lexers import get_lexer_by_name
            from pygments.formatters import Terminal256Formatter
            
            lexer = get_lexer_by_name(language) if language else None
            
            if lexer and sys.stdout.isatty():
                # Apply syntax highlighting if terminal supports it
                formatter = Terminal256Formatter()
                highlighted_code = highlight(code, lexer, formatter)
                
                if line_numbers:
                    lines = highlighted_code.split('\n')
                    for i, line in enumerate(lines, 1):
                        print(f"{i:4d} | {line}")
                else:
                    print(highlighted_code)
            else:
                # Fallback to simple formatting with line numbers
                if line_numbers:
                    lines = code.split('\n')
                    for i, line in enumerate(lines, 1):
                        print(f"{i:4d} | {line}")
                else:
                    print(code)
                    
        except ImportError:
            # Fallback if pygments is not available
            if line_numbers:
                lines = code.split('\n')
                for i, line in enumerate(lines, 1):
                    print(f"{i:4d} | {line}")
            else:
                print(code)
    
    @staticmethod
    def file_selector(start_dir: str = ".", extensions: List[str] = None) -> Optional[str]:
        """
        Interactive file selector.
        
        Args:
            start_dir: Starting directory
            extensions: List of file extensions to filter (e.g., ['.py', '.txt'])
            
        Returns:
            Selected file path or None if cancelled
        """
        current_dir = os.path.abspath(start_dir)
        
        while True:
            print(f"\nCurrent directory: {current_dir}")
            entries = sorted(os.listdir(current_dir))
            
            # Filter by extensions if specified
            if extensions:
                file_entries = [e for e in entries if os.path.isfile(os.path.join(current_dir, e)) 
                              and any(e.endswith(ext) for ext in extensions)]
            else:
                file_entries = [e for e in entries if os.path.isfile(os.path.join(current_dir, e))]
                
            dir_entries = [e for e in entries if os.path.isdir(os.path.join(current_dir, e))]
            
            # Add special navigation options
            options = [".."] + dir_entries + file_entries
            types = ["[Dir]"] * (len(dir_entries) + 1) + ["[File]"] * len(file_entries)
            
            # Print the options
            print("\nAvailable entries:")
            for i, (option, type_label) in enumerate(zip(options, types)):
                print(f"{i + 1}. {option} {type_label}")
            
            print("\nEnter a number to select, or 'q' to cancel")
            response = input("> ").strip()
            
            if response.lower() in ['q', 'quit', 'exit', 'cancel']:
                return None
            
            try:
                choice = int(response)
                if 1 <= choice <= len(options):
                    selected = options[choice - 1]
                    full_path = os.path.join(current_dir, selected)
                    
                    if selected == "..":
                        # Go up one directory
                        current_dir = os.path.dirname(current_dir)
                    elif os.path.isdir(full_path):
                        # Enter the selected directory
                        current_dir = full_path
                    else:
                        # Return the selected file
                        return full_path
                else:
                    print(f"Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("Please enter a number or 'q'")
    
    @staticmethod
    def show_diff(original: str, modified: str, context_lines: int = 3) -> None:
        """
        Display diff between two strings.
        
        Args:
            original: Original text
            modified: Modified text
            context_lines: Number of context lines to show
        """
        try:
            import difflib
            from termcolor import colored
            
            diff = difflib.unified_diff(
                original.splitlines(),
                modified.splitlines(),
                lineterm='',
                n=context_lines
            )
            
            for line in diff:
                if line.startswith('+'):
                    print(colored(line, 'green'))
                elif line.startswith('-'):
                    print(colored(line, 'red'))
                elif line.startswith('@@'):
                    print(colored(line, 'cyan'))
                else:
                    print(line)
                    
        except ImportError:
            # Fallback if dependencies are not available
            diff = difflib.unified_diff(
                original.splitlines(),
                modified.splitlines(),
                lineterm='',
                n=context_lines
            )
            for line in diff:
                if line.startswith('+'):
                    print(f"\033[92m{line}\033[0m")  # Green
                elif line.startswith('-'):
                    print(f"\033[91m{line}\033[0m")  # Red
                elif line.startswith('@@'):
                    print(f"\033[96m{line}\033[0m")  # Cyan
                else:
                    print(line)
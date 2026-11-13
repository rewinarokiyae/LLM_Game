"""
Terminal User Interface.
Rich-based visual formatting, banners, status panels, and table displays for the CLI.
No web, HTML, or GUI dependencies.
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich.text import Text
from typing import List, Dict, Any, Optional

from app.config.settings import settings
from app.security.access_control import UserContext


class TerminalUI:
    def __init__(self):
        self.console = Console()

    def print_banner(self, db_status: str, llm_status: str, rag_status: str, dataset_status: str):
        banner_text = Text()
        banner_text.append("=====================================================\n", style="bold blue")
        banner_text.append("       FACULTY WORKLOAD INTELLIGENCE ASSISTANT       \n", style="bold white")
        banner_text.append("   University Academic Intelligence & Compliance CLI \n", style="italic cyan")
        banner_text.append("=====================================================\n", style="bold blue")

        status_table = Table.grid(padding=(0, 2))
        status_table.add_column(style="bold")
        status_table.add_column()

        status_table.add_row("Database:", f"[green]{db_status}[/green]")
        status_table.add_row("LLM Layer:", f"[yellow]{llm_status}[/yellow]")
        status_table.add_row("Vector Store:", f"[cyan]{rag_status}[/cyan]")
        status_table.add_row("Dataset:", f"[green]{dataset_status}[/green]")

        panel = Panel(
            status_table,
            title="[bold]System Status[/bold]",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(banner_text)
        self.console.print(panel)

    def print_user_session(self, user: UserContext):
        role_style = "bold green" if user.is_faculty() else ("bold yellow" if user.is_hod() else "bold red")
        user_info = Text()
        user_info.append(f"Logged in as: ", style="bold")
        user_info.append(f"{user.faculty_name or user.username} ", style="bold cyan")
        user_info.append(f"| Role: ", style="bold")
        user_info.append(f"{user.role.value} ", style=role_style)
        user_info.append(f"| Scope: ", style="bold")
        user_info.append(f"{user.department_scope}\n", style="bold magenta")
        user_info.append("Type a natural language question, or type /help for commands.", style="dim")

        self.console.print(Panel(user_info, border_style="cyan"))

    def render_markdown(self, md_text: str):
        self.console.print(Markdown(md_text))

    def print_error(self, message: str):
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_warning(self, message: str):
        self.console.print(f"[bold yellow]Warning:[/bold yellow] {message}")

    def print_success(self, message: str):
        self.console.print(f"[bold green]Success:[/bold green] {message}")


"""
Main Terminal Application Entry Point.
Provides interactive CLI for Faculty Workload Intelligence Assistant.
Supports:
- Interactive login and demo identity selection
- Natural language query answering
- Slash commands (/help, /whoami, /workload, /timetable, /assignments, /violations, etc.)
- Flags: --check-system, --rebuild-index, --user <id>, --query "<question>"
"""

import sys
import os
import argparse
from typing import Optional

from app.config.settings import settings
from app.config.logging_config import logger
from app.cli.terminal_ui import TerminalUI
from app.cli.commands import CommandHandler
from app.security.authentication import AuthenticationService
from app.security.access_control import UserContext, AccessDeniedError
from app.nlp.query_router import QueryRouter
from app.rag.rag_service import RAGService
from app.database.connection import get_db_session
from app.database.models import Faculty, Timetable, WorkloadPolicy
from app.llm.factory import LLMFactory


def check_system():
    ui = TerminalUI()
    ui.console.print("\n[bold blue]=== SYSTEM DIAGNOSTICS ===[/bold blue]")

    # 1. Database
    try:
        with get_db_session() as session:
            f_cnt = session.query(Faculty).count()
            tt_cnt = session.query(Timetable).count()
            p_cnt = session.query(WorkloadPolicy).count()
        db_status = f"Connected ({f_cnt} faculty, {tt_cnt} timetable slots, {p_cnt} policies)"
    except Exception as e:
        db_status = f"Error: {e}"

    # 2. LLM
    llm_status = LLMFactory.get_status()

    # 3. Vector Store
    try:
        idx_path = os.path.join(settings.VECTOR_STORE_PATH, "chunks_index.json")
        if os.path.exists(idx_path):
            import json
            with open(idx_path, "r", encoding="utf-8") as f:
                chk_cnt = len(json.load(f))
            rag_status = f"Ready ({chk_cnt} chunks indexed)"
        else:
            rag_status = "Unindexed (Run --rebuild-index)"
    except Exception as e:
        rag_status = f"Error: {e}"

    # 4. Dataset
    ds_status = "Available" if os.path.exists(settings.DATASET_PATH) else "Dataset File Missing"

    ui.print_banner(db_status, llm_status, rag_status, ds_status)
    ui.console.print("[bold green]System check complete.[/bold green]\n")


def rebuild_index():
    ui = TerminalUI()
    ui.console.print("[cyan]Rebuilding vector store index from policy documents...[/cyan]")
    rag = RAGService()
    rag.build_or_refresh_index(force=True)
    ui.console.print(f"[bold green]Vector index rebuild complete. Total chunks: {len(rag.vector_store.chunks)}[/bold green]")


def interactive_login(ui: TerminalUI) -> Optional[UserContext]:
    ui.console.print("\n[bold cyan]Select Demo Identity:[/bold cyan]")
    ui.console.print("  [bold]1.[/bold] FAC001 - Dr. Meera Nair (HOD - Computer Science & Engineering)")
    ui.console.print("  [bold]2.[/bold] FAC002 - Arjun Menon (Faculty - Computer Science & Engineering)")
    ui.console.print("  [bold]3.[/bold] FAC003 - Kavya Sharma (Faculty - Computer Science & Engineering)")
    ui.console.print("  [bold]4.[/bold] FAC007 - Dr. Vikram Rao (HOD - AI & Machine Learning)")
    ui.console.print("  [bold]5.[/bold] FAC013 - Dr. Ananya Iyer (HOD - Data Science)")
    ui.console.print("  [bold]6.[/bold] ADMIN - Institution Administrator")
    ui.console.print("  [dim](Or type any seeded faculty ID like FAC004..FAC018, username, or 'exit')[/dim]\n")

    quick_map = {
        "1": "FAC001",
        "2": "FAC002",
        "3": "FAC003",
        "4": "FAC007",
        "5": "FAC013",
        "6": "ADMIN"
    }

    while True:
        try:
            choice = input("Enter choice [1-6] or faculty ID: ").strip()
        except (KeyboardInterrupt, EOFError):
            return None

        if not choice:
            continue
        if choice.lower() in ["exit", "quit", "q"]:
            return None

        target_id = quick_map.get(choice, choice)
        try:
            user = AuthenticationService.authenticate_demo(target_id)
            ui.print_warning(AuthenticationService.DEMO_SECURITY_WARNING)
            return user
        except AccessDeniedError as e:
            ui.print_error(str(e))
        except Exception as e:
            ui.print_error(f"Authentication failed: {e}")


def interactive_session(user_context: UserContext, ui: TerminalUI):
    ui.print_user_session(user_context)

    while True:
        try:
            prompt_str = f"[{user_context.username}@{user_context.role.value}]> "
            query = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            ui.console.print("\n[yellow]Session terminated. Exiting...[/yellow]")
            break

        if not query:
            continue

        if query.lower() in ["/exit", "exit", "quit", "/quit"]:
            ui.console.print("[yellow]Exiting application. Goodbye![/yellow]")
            break

        if query.lower() in ["/logout", "logout"]:
            ui.console.print("[yellow]Logged out successfully.[/yellow]")
            new_user = interactive_login(ui)
            if new_user:
                user_context = new_user
                ui.print_user_session(user_context)
                continue
            else:
                break

        # Check slash commands
        cmd_result = CommandHandler.handle_command(query, user_context)
        if cmd_result:
            ui.render_markdown(cmd_result["response"])
            print()
            continue

        # Process natural-language query
        try:
            result = QueryRouter.process_query(user_context, query)
            ui.render_markdown(result["response"])
            print()
        except Exception as e:
            logger.error(f"CLI query error: {e}", exc_info=True)
            ui.print_error(f"An unexpected error occurred: {e}")


def main():
    parser = argparse.ArgumentParser(description="Faculty Workload Intelligence Assistant CLI")
    parser.add_argument("--check-system", action="store_true", help="Run system diagnostics and exit")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild policy vector index and exit")
    parser.add_argument("--user", type=str, help="Demo user ID or faculty ID to log in as directly")
    parser.add_argument("--query", type=str, help="Single query to execute in batch mode and exit")

    args = parser.parse_args()

    ui = TerminalUI()

    if args.check_system:
        check_system()
        return

    if args.rebuild_index:
        rebuild_index()
        return

    # Check database and vector store status
    try:
        with get_db_session() as session:
            fac_cnt = session.query(Faculty).count()
        db_stat = f"Connected ({fac_cnt} faculty loaded)"
    except Exception:
        db_stat = "Disconnected / Not Initialized"

    llm_stat = LLMFactory.get_status()

    try:
        idx_path = os.path.join(settings.VECTOR_STORE_PATH, "chunks_index.json")
        if os.path.exists(idx_path):
            import json
            with open(idx_path, "r", encoding="utf-8") as f:
                chk_cnt = len(json.load(f))
            rag_stat = f"Ready ({chk_cnt} chunks)"
        else:
            rag_stat = "Unindexed"
    except Exception:
        rag_stat = "Offline / Unindexed"

    ds_stat = "Loaded" if os.path.exists(settings.DATASET_PATH) else "Missing"

    # Direct query mode
    if args.query:
        target_user = args.user or "ADMIN"
        try:
            user = AuthenticationService.authenticate_demo(target_user)
            result = QueryRouter.process_query(user, args.query)
            ui.render_markdown(result["response"])
        except Exception as e:
            ui.print_error(str(e))
        return

    # Interactive CLI mode
    ui.print_banner(db_stat, llm_stat, rag_stat, ds_stat)

    user = None
    if args.user:
        try:
            user = AuthenticationService.authenticate_demo(args.user)
        except Exception as e:
            ui.print_error(f"Failed to login with user '{args.user}': {e}")

    if not user:
        user = interactive_login(ui)

    if user:
        interactive_session(user, ui)


if __name__ == "__main__":
    main()

import typer
import json
import os
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv

# Import your components
from models.canonical import CanonicalCandidate
from extractors.csv_extractor import extract_csv_stream
from extractors.resume_extractor import parse_pdf_resume
from extractors.github_extractor import fetch_github_profile
from merger.engine import CandidateMergeEngine
from projection.projector import ProfileProjector
from projection.path_resolver import resolve_github_handle
# Load environment variables (GITHUB_TOKEN)
load_dotenv()

app = typer.Typer(help="Eightfold Candidate Data Transformer")
console = Console()

@app.command()
def process(
    csv_path: str = typer.Option(..., help="Path to recruiter CSV"),
    resume_path: str = typer.Option(None, help="Path to resume PDF"),
    github_input: str = typer.Option(None, help="GitHub username or profile URL"),
    config_path: str = typer.Option("config.json", help="Projection config JSON path")
):
    console.print(Panel.fit("[bold blue]Eightfold Pipeline Initialized[/bold blue]"))
    
    merger = CandidateMergeEngine()
    candidate = None
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}")) as progress:
        
        # 1. CSV Stream
        task1 = progress.add_task("[yellow]Ingesting CSV...", total=None)
        if os.path.exists(csv_path):
            for row in extract_csv_stream(csv_path):
                if not candidate:
                    candidate = CanonicalCandidate(candidate_id=row.email or "unknown")
                merger.upsert_csv(candidate, row)
                break # Single candidate processing
            progress.update(task1, completed=100, description="[green]CSV Ingested!")
        else:
            progress.update(task1, completed=100, description="[red]CSV not found.")

        # 2. Resume Extraction
        if resume_path:
            task2 = progress.add_task("[yellow]Parsing PDF Resume...", total=None)
            try:
                # 1. Parse raw data
                resume_data = parse_pdf_resume(resume_path)
                if not candidate:
                    candidate = CanonicalCandidate(candidate_id=resume_data.email or "unknown")
                
                # 2. Merge
                merger.upsert_resume(candidate, resume_data)
                
                progress.update(task2, completed=100, description="[green]Resume Parsed!")
            except Exception as e:
                progress.update(task2, completed=100, description=f"[red]Resume Failed: {e}")

        # 3. GitHub API (With Path Resolution)
        if github_input:
            clean_username = resolve_github_handle(github_input)
            task3 = progress.add_task(f"[yellow]Querying GitHub for {clean_username}...", total=None)
            try:
                gh_data = fetch_github_profile(clean_username)
                if not candidate:
                    candidate = CanonicalCandidate(candidate_id=clean_username)
                
                # Merge
                merger.upsert_github(candidate, gh_data)
                
                progress.update(task3, completed=100, description="[green]GitHub Synced!")
            except Exception as e:
                progress.update(task3, completed=100, description=f"[red]GitHub Unavailable: {e}")

    # 4. Projection
    config = {"include_provenance": True}
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

    if candidate:
        final_output = ProfileProjector.project(candidate, config)
        console.print("\n[bold green]Final Canonical Profile:[/bold green]")
        console.print_json(data=final_output)
    else:
        console.print("[red]No valid candidate data could be processed.[/red]")

if __name__ == "__main__":
    app()
"""scripts/run_analysis.py"""
import typer
app = typer.Typer()
@app.command()
def analyze(run_id: str):
    print(f"Analyzing {run_id}...")
if __name__ == "__main__":
    app()

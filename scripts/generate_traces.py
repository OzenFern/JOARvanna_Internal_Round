"""scripts/generate_traces.py"""
import typer
app = typer.Typer()
@app.command()
def generate(n: int = 100):
    print(f"Generating {n} traces...")
if __name__ == "__main__":
    app()

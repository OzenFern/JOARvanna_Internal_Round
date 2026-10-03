"""scripts/run_eval.py"""
import typer
app = typer.Typer()
@app.command()
def evaluate():
    print("Evaluating...")
if __name__ == "__main__":
    app()

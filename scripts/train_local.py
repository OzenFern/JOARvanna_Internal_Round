"""scripts/train_local.py"""
import typer
app = typer.Typer()
@app.command()
def train():
    print("Training local model...")
if __name__ == "__main__":
    app()

"""scripts/export_report.py"""
import typer
app = typer.Typer()
@app.command()
def export():
    print("Exporting report...")
if __name__ == "__main__":
    app()

from render import TaskContext, Workflows

app = Workflows()

@app.task
def check_project(ctx: TaskContext) -> dict:
    return {
        "status": "success",
        "message": "Gold Parity Render Workflow is running!",
        "project": "Gold Parity Hack in the Hills"
    }

if __name__ == "__main__":
    app.start()

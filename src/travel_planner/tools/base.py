from crewai.tools import BaseTool


class TravelTool(BaseTool):
    """Base class for tools with a consistent error boundary."""

    def _run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return self.run(*args, **kwargs)
        except Exception as exc:
            return {"status": "error", "tool": self.name, "error": str(exc)}

    def run(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotImplementedError

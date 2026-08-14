async def failure(state):

    error = (
        state.get("validation_error")
        or state.get("execution_error")
        or "error desconocido"
    )

    answer = (
        "No fue posible responder la pregunta. "
        f"Motivo: {error}"
    )

    return {"answer": answer, "success": False}
FROM python:3.12-slim

WORKDIR /app

# Asegura que /app (raiz del repo) este en sys.path.
# chainlit load_module() inserta solo el dir del target (chatbot/) y no la
# raiz, por lo que `from chatbot.agent_client import ...` no resolveria.
ENV PYTHONPATH=/app

COPY chatbot/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["chainlit", "run", "chatbot/app.py", "--host", "0.0.0.0", "--port", "8001"]
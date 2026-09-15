#Imagen base
FROM python:3.14-slim

#Copia elementos necesarios para que funcione uv en l aimagen base
# uno u multiples archivos de origen (/uv /uvx), sólo uno de destino (/bin/) siempre el último
#COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
#RUN curl -LsSf https://astral.sh/uv/install.sh | sh

RUN apt update && apt install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin:/app/.venv/bin:$PATH"

#Carpeta de trabajo dentro del contenedor
WORKDIR /app

#Copia los archivos de configuración de dependencias, que tienen la informacion exacta de que instalar y con que version
COPY pyproject.toml uv.lock ./

RUN uv sync --no-install-project

#Copia el resto de los archivos del proyecto al contenedor
#Primer . (origen) carpeta dionde esta el dockerfile, segundo . (destino) carpeta actual dentro del contenedor
COPY . .

#Ejecuta la instalación de dependencias con uv
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"

#Instruccion para ejecutar como primer comando al arrancar el contenedor, formato de lista
#CMD ["uv", "run", "fastapi", "run", "src/auth/main.py", "--host", "0.0.0.0", "--port", "8000"]
CMD ["/app/.venv/bin/uvicorn", "src.auth.main:app", "--host", "0.0.0.0", "--port", "8000"]

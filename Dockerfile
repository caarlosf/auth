#Imagen base
FROM python:3.12-slim

#Copia elementos necesarios para que funcione uv en l aimagen base
# uno u multiples archivos de origen (/uv /uvx), sólo uno de destino (/bin/) siempre el último
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

#Carpeta de trabajo dentro del contenedor
WORKDIR /app

#Copia los archivos de configuración de dependencias, que tienen la informacion exacta de que instalar y con que version
COPY pyproject.toml uv.lock ./

#Ejecuta la instalación de dependencias con uv
RUN uv sync

#Copia el resto de los archivos del proyecto al contenedor
#Primer . (origen) carpeta dionde esta el dockerfile, segundo . (destino) carpeta actual dentro del contenedor
COPY . .

#Instruccion para ejecutar como primer comando al arrancar el contenedor, formato de lista
CMD ["uv", "run", "fastapi", "run", "src/auth/main.py", "--host", "0.0.0.0", "--port", "8000"]
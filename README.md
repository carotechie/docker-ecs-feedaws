# 🚀 Mi Feed AWS – Docker + ECS Demo

Feed de las últimas novedades de AWS (`What's New`), empaquetado en un contenedor Docker y listo para desplegarse en Amazon ECS.

---

## 📁 Estructura del proyecto

```
docker_con_ecs_mifeed/
├── app.py               # Aplicación Flask (lee el RSS de AWS)
├── requirements.txt     # Dependencias Python
├── Dockerfile           # Imagen Docker de la app
└── templates/
    └── index.html       # Plantilla HTML del feed
```

---

## ⚙️ Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Conexión a internet (la app consume el RSS de AWS en cada petición)

---

## 🐳 Levantar con Docker (local)

### 1. Construir la imagen

```bash
docker build -t mifeed-aws .
```

### 2. Correr el contenedor

```bash
docker run -d -p 8080:8080 --name mifeed mifeed-aws
```

| Flag | Qué hace |
|------|----------|
| `-d` | Corre el contenedor en segundo plano (detached) |
| `-p 8080:8080` | Mapea el puerto 8080 del host al 8080 del contenedor |
| `--name mifeed` | Nombre amigable para el contenedor |

### 3. Ver el feed

Abre tu navegador en:

```
http://localhost:8080
```

### 4. Verificar salud del servicio

```bash
curl http://localhost:8080/health
# → {"status": "ok"}
```

---

## 🔄 ¿Cómo se actualizan los datos?

**No necesitas hacer nada especial.** El feed se actualiza **en cada petición HTTP**:

- `app.py` llama a `feedparser.parse(AWS_RSS_URL)` cada vez que alguien visita `/`
- Eso significa que **cada vez que refrescas el navegador (`F5` o `Cmd+R`)**, la app consulta el RSS de AWS en ese instante y muestra las últimas novedades
- No hay caché, no hay intervalo fijo: el contenedor puede correr indefinidamente y siempre devolverá datos frescos

Para ver actualizaciones mientras el contenedor corre:

```bash
# Solo recarga el navegador:
# http://localhost:8080  →  F5 / Cmd+R
```

---

## 🛑 Detener y limpiar

```bash
# Detener el contenedor
docker stop mifeed

# Eliminarlo
docker rm mifeed

# (Opcional) Borrar la imagen
docker rmi mifeed-aws
```

---

## 📋 Comandos útiles de depuración

```bash
# Ver logs en tiempo real
docker logs -f mifeed

# Ver contenedores corriendo
docker ps

# Entrar al contenedor (shell interactivo)
docker exec -it mifeed /bin/sh
```

---

## ☁️ Siguiente paso: desplegar en Amazon ECS

1. Subir la imagen a **Amazon ECR**
2. Crear un **Task Definition** en ECS apuntando a esa imagen
3. Crear un **Service** con el Task Definition
4. Exponer el servicio con un **Application Load Balancer**

La URL pública del ALB reemplaza `localhost:8080` — la app funciona exactamente igual.

---

## 🧰 Stack

| Componente | Tecnología |
|------------|------------|
| Lenguaje | Python 3.12 |
| Framework web | Flask 3 |
| Servidor WSGI | Gunicorn |
| Parser RSS | feedparser |
| Contenedor | Docker (python:3.12-slim) |
| Fuente de datos | [AWS What's New RSS](https://aws.amazon.com/about-aws/whats-new/recent/feed/) |

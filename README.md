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

## ☁️ Desplegar en Amazon ECS

### Requisitos previos para AWS

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) instalado
- Un usuario IAM con permisos sobre ECR y ECS
- Tener a mano tu **Access Key ID** y **Secret Access Key**

---

### 1. Configurar credenciales de AWS

```bash
aws configure
```

Te pedirá cuatro valores:

```
AWS Access Key ID [None]:     ← tu Access Key ID
AWS Secret Access Key [None]: ← tu Secret Access Key
Default region name [None]:   us-east-1
Default output format [None]: json
```

Las credenciales quedan guardadas en `~/.aws/credentials`. Para verificar que funcionan:

```bash
aws sts get-caller-identity
```

Deberías ver el `Account`, `UserId` y `Arn` de tu usuario. Si aparece un error de credenciales, revisa que copiaste bien las keys.

---

### 2. Crear el repositorio en ECR

```bash
aws ecr create-repository \
  --repository-name demos/mifeed-aws \
  --region us-east-1
```

El comando devuelve un JSON. Copia el valor de `repositoryUri`, lo necesitarás en los pasos siguientes. Se ve así:

```
url.dkr.ecr.us-east-1.amazonaws.com/demos/mifeed-aws
```

---

### 3. Autenticarte con ECR

Docker necesita un token temporal para poder hacer push a ECR. Este comando lo obtiene y lo pasa directamente a `docker login`:

```bash
aws ecr get-login-password --region us-east-1 \
  | docker login \
    --username AWS \
    --password-stdin \
    url.dkr.ecr.us-east-1.amazonaws.com
```

Si ves `Login Succeeded`, estás lista para el siguiente paso. El token es válido por **12 horas**; si pasa ese tiempo, repite este comando.

---

### 4. Etiquetar y subir la imagen

```bash
# Define tu URI como variable para no repetirlo
ECR_URI=url.dkr.ecr.us-east-1.amazonaws.com/demos/mifeed-aws

# Etiqueta la imagen local con el URI de ECR
docker tag mifeed-aws:latest $ECR_URI:latest

# Sube la imagen al registro
docker push $ECR_URI:latest
```

El push puede tardar unos minutos la primera vez. Verás las capas subiendo una por una.

---

### 5. Crear el Cluster en ECS

Un Cluster es el entorno lógico donde corren los contenedores. Usamos **Fargate** para no tener que gestionar servidores.

```bash
aws ecs create-cluster \
  --cluster-name mifeed-aws \
  --capacity-providers FARGATE \
  --region us-east-1
```

Verifica que se creó:

```bash
aws ecs describe-clusters \
  --clusters mifeed-aws \
  --region us-east-1 \
  --query "clusters[0].status"
# → "ACTIVE"
```

---

### 6. Crear la Task Definition

La Task Definition le dice a ECS qué imagen correr, cuántos recursos asignar y en qué puerto escucha la app. Primero necesitas el ARN del rol de ejecución de ECS:

```bash
# Obtener el ARN del execution role (viene por defecto en cuentas nuevas)
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query "Role.Arn" \
  --output text
# → arn:aws:iam::<TU_ACCOUNT_ID>:role/ecsTaskExecutionRole
```

> Si el rol no existe, créalo desde la consola de AWS: IAM → Roles → Create role → Elastic Container Service Task → adjunta la policy `AmazonECSTaskExecutionRolePolicy`.

Crea el archivo `task-definition.json` en la raíz del proyecto:

```json
{
  "family": "mifeed-aws",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<TU_ACCOUNT_ID>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "mifeed-aws",
      "image": "url.dkr.ecr.us-east-1.amazonaws.com/demos/mifeed-aws:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/mifeed-aws",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs",
          "awslogs-create-group": "true"
        }
      }
    }
  ]
}
```

> Reemplaza `<TU_ACCOUNT_ID>` con el ID de tu cuenta AWS (lo ves con `aws sts get-caller-identity --query Account --output text`).

Registra la Task Definition:

```bash
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json \
  --region us-east-1
```

Verifica que quedó registrada:

```bash
aws ecs list-task-definitions --region us-east-1
# → "arn:aws:ecs:us-east-1:<TU_ACCOUNT_ID>:task-definition/mifeed-aws:1"
```

---

### 7. Crear el Security Group

El Service necesita un Security Group que permita tráfico entrante en el puerto 8080.

```bash
# Obtener el ID de la VPC por defecto
VPC_ID=$(aws ec2 describe-vpcs \
  --filters "Name=isDefault,Values=true" \
  --query "Vpcs[0].VpcId" \
  --output text \
  --region us-east-1)

echo "VPC: $VPC_ID"

# Crear el Security Group
SG_ID=$(aws ec2 create-security-group \
  --group-name mifeed-sg \
  --description "Acceso HTTP al feed en puerto 8080" \
  --vpc-id $VPC_ID \
  --region us-east-1 \
  --query "GroupId" \
  --output text)

echo "Security Group: $SG_ID"

# Abrir el puerto 8080 al mundo
aws ec2 authorize-security-group-ingress \
  --group-id $SG_ID \
  --protocol tcp \
  --port 8080 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

---

### 8. Crear el Service

El Service mantiene corriendo la cantidad de Tasks que le indiques y las reinicia automáticamente si fallan. Primero obtén los IDs de las subnets públicas de tu VPC:

```bash
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query "Subnets[*].[SubnetId,AvailabilityZone,MapPublicIpOnLaunch]" \
  --output table \
  --region us-east-1
```

Copia al menos dos SubnetIds de subnets con `MapPublicIpOnLaunch = True` y úsalos en el comando siguiente:

```bash
aws ecs create-service \
  --cluster mifeed-aws \
  --service-name mifeed-service \
  --task-definition mifeed-aws \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={
    subnets=[subnet-AAAAAAAA,subnet-BBBBBBBB],
    securityGroups=[$SG_ID],
    assignPublicIp=ENABLED
  }" \
  --region us-east-1
```

> Reemplaza `subnet-AAAAAAAA` y `subnet-BBBBBBBB` con los SubnetIds que obtuviste arriba.

Espera ~1 minuto y verifica que el Task esté corriendo:

```bash
aws ecs describe-services \
  --cluster mifeed-aws \
  --services mifeed-service \
  --region us-east-1 \
  --query "services[0].{Estado:status,Corriendo:runningCount,Deseadas:desiredCount}"
# → { "Estado": "ACTIVE", "Corriendo": 1, "Deseadas": 1 }
```

---

### 9. Obtener la IP pública y acceder a la app

```bash
# 1. Obtener el Task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster mifeed-aws \
  --service-name mifeed-service \
  --region us-east-1 \
  --query "taskArns[0]" \
  --output text)

# 2. Obtener el ENI (interfaz de red) del Task
ENI_ID=$(aws ecs describe-tasks \
  --cluster mifeed-aws \
  --tasks $TASK_ARN \
  --region us-east-1 \
  --query "tasks[0].attachments[0].details[?name=='networkInterfaceId'].value" \
  --output text)

# 3. Obtener la IP pública
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids $ENI_ID \
  --region us-east-1 \
  --query "NetworkInterfaces[0].Association.PublicIp" \
  --output text)

echo "Tu app está en: http://$PUBLIC_IP:8080"
```

Abre esa URL en tu navegador. También puedes verificar el health check:

```bash
curl http://$PUBLIC_IP:8080/health
# → {"status": "ok"}
```

---

### 10. Actualizar la app (nuevo deploy)

Cuando hagas cambios en el código y quieras desplegar una nueva versión:

```bash
# 1. Reconstruir y subir la imagen actualizada
docker build -t mifeed-aws .
docker tag mifeed-aws:latest $ECR_URI:latest
docker push $ECR_URI:latest

# 2. Forzar un nuevo deploy en ECS (descarga la imagen más reciente)
aws ecs update-service \
  --cluster mifeed-aws \
  --service mifeed-service \
  --force-new-deployment \
  --region us-east-1
```

ECS reemplazará el Task en curso con uno nuevo que usa la imagen actualizada, sin downtime.

---

### 🧹 Limpiar recursos (para no generar costos)

```bash
# Eliminar el Service (primero baja a 0 tasks)
aws ecs update-service \
  --cluster mifeed-aws \
  --service mifeed-service \
  --desired-count 0 \
  --region us-east-1

aws ecs delete-service \
  --cluster mifeed-aws \
  --service mifeed-service \
  --region us-east-1

# Eliminar el Cluster
aws ecs delete-cluster \
  --cluster mifeed-aws \
  --region us-east-1

# Eliminar el repositorio ECR (y todas sus imágenes)
aws ecr delete-repository \
  --repository-name demos/mifeed-aws \
  --force \
  --region us-east-1

# Eliminar el Security Group
aws ec2 delete-security-group \
  --group-id $SG_ID \
  --region us-east-1
```

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

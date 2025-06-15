# Deployment Guide

This guide covers deploying BrowserBot in production environments with high availability, security, and monitoring.

## Table of Contents

- [Production Requirements](#production-requirements)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring & Observability](#monitoring--observability)
- [Security Considerations](#security-considerations)
- [Scaling Strategies](#scaling-strategies)
- [Troubleshooting](#troubleshooting)

## Production Requirements

### System Requirements

- **CPU**: 4+ cores recommended
- **Memory**: 8GB+ RAM (4GB for browser processes)
- **Storage**: 20GB+ SSD storage
- **Network**: Stable internet connection with low latency

### External Dependencies

- **Redis**: For session storage and caching (Redis 6.0+)
- **Monitoring**: Prometheus + Grafana for metrics
- **Logging**: ELK Stack or similar for log aggregation
- **Load Balancer**: nginx, HAProxy, or cloud load balancer

## Docker Deployment

### Single Node Deployment

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/BrowserBot.git
cd BrowserBot

# 2. Configure environment
cp .env.example .env
# Edit .env with your configuration

# 3. Deploy with Docker Compose
docker-compose up -d

# 4. Verify deployment
docker-compose ps
docker-compose logs -f browserbot
```

### Multi-Node Docker Swarm

```bash
# 1. Initialize Docker Swarm
docker swarm init

# 2. Deploy stack
docker stack deploy -c docker-compose.prod.yml browserbot

# 3. Scale services
docker service scale browserbot_app=3
docker service scale browserbot_worker=5
```

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: browserbot:latest
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        max_attempts: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
      - REDIS_URL=redis://redis:6379
      - METRICS_PORT=8000
    networks:
      - browserbot-net
    volumes:
      - ./data:/app/data:rw
      - ./logs:/app/logs:rw

  worker:
    image: browserbot:latest
    command: python -m browserbot.worker
    deploy:
      replicas: 5
      restart_policy:
        condition: on-failure
    environment:
      - ENVIRONMENT=production
      - WORKER_MODE=true
    networks:
      - browserbot-net
    volumes:
      - ./data:/app/data:rw

  redis:
    image: redis:7-alpine
    deploy:
      restart_policy:
        condition: on-failure
    command: redis-server --appendonly yes
    networks:
      - browserbot-net
    volumes:
      - redis-data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - browserbot-net
    depends_on:
      - app

  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks:
      - browserbot-net

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - browserbot-net

volumes:
  redis-data:
  grafana-data:

networks:
  browserbot-net:
    driver: overlay
    attachable: true
```

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl and helm
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
curl https://get.helm.sh/helm-v3.12.0-linux-amd64.tar.gz | tar xz
```

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: browserbot
  labels:
    name: browserbot

---
apiVersion: v1
kind: ConfigMap
metadata:
  name: browserbot-config
  namespace: browserbot
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
  REDIS_URL: "redis://redis-service:6379"
  METRICS_PORT: "8000"
  BROWSER_HEADLESS: "true"
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: browserbot-app
  namespace: browserbot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: browserbot-app
  template:
    metadata:
      labels:
        app: browserbot-app
    spec:
      containers:
      - name: browserbot
        image: browserbot:latest
        ports:
        - containerPort: 8080
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: browserbot-config
        - secretRef:
            name: browserbot-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: data-volume
          mountPath: /app/data
        - name: logs-volume
          mountPath: /app/logs
      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: browserbot-data-pvc
      - name: logs-volume
        emptyDir: {}

---
apiVersion: v1
kind: Service
metadata:
  name: browserbot-service
  namespace: browserbot
spec:
  selector:
    app: browserbot-app
  ports:
  - name: http
    port: 80
    targetPort: 8080
  - name: metrics
    port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: browserbot-ingress
  namespace: browserbot
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - browserbot.yourdomain.com
    secretName: browserbot-tls
  rules:
  - host: browserbot.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: browserbot-service
            port:
              number: 80
```

### Secrets

```bash
# Create secrets
kubectl create secret generic browserbot-secrets \
  --from-literal=OPENROUTER_API_KEY=your_api_key \
  --namespace=browserbot

# Deploy Redis
helm repo add bitnami https://charts.bitnami.com/bitnami
helm install redis bitnami/redis \
  --namespace browserbot \
  --set auth.enabled=false \
  --set replica.replicaCount=2

# Deploy the application
kubectl apply -f k8s/
```

## Cloud Deployment

### AWS ECS Deployment

```json
{
  "family": "browserbot",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "browserbot",
      "image": "your-account.dkr.ecr.region.amazonaws.com/browserbot:latest",
      "portMappings": [
        {
          "containerPort": 8080,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ENVIRONMENT", "value": "production"},
        {"name": "LOG_LEVEL", "value": "INFO"}
      ],
      "secrets": [
        {
          "name": "OPENROUTER_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:browserbot/api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/browserbot",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run

```yaml
# cloud-run.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: browserbot
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/memory: "2Gi"
        run.googleapis.com/cpu: "1000m"
    spec:
      containers:
      - image: gcr.io/your-project/browserbot:latest
        ports:
        - containerPort: 8080
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: OPENROUTER_API_KEY
          valueFrom:
            secretKeyRef:
              name: browserbot-secrets
              key: api_key
        resources:
          limits:
            memory: "2Gi"
            cpu: "1000m"
```

### Azure Container Instances

```bash
# Deploy to Azure Container Instances
az container create \
  --resource-group browserbot-rg \
  --name browserbot \
  --image browserbot:latest \
  --cpu 2 \
  --memory 4 \
  --restart-policy Always \
  --ports 8080 \
  --environment-variables \
    ENVIRONMENT=production \
    LOG_LEVEL=INFO \
  --secure-environment-variables \
    OPENROUTER_API_KEY=your_api_key
```

## Monitoring & Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'browserbot'
    static_configs:
      - targets: ['browserbot-service:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Grafana Dashboards

Import dashboard ID: `12345` for BrowserBot metrics or create custom dashboards with:

- **Application Metrics**: Request rate, response time, error rate
- **System Metrics**: CPU, memory, disk usage
- **Browser Metrics**: Active sessions, page load times
- **Error Metrics**: Error rates by type, recovery success rates

### Alert Rules

```yaml
# alert_rules.yml
groups:
- name: browserbot.rules
  rules:
  - alert: HighErrorRate
    expr: rate(browserbot_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: High error rate detected

  - alert: HighMemoryUsage
    expr: browserbot_memory_usage_bytes > 1.5e9
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High memory usage detected

  - alert: ServiceDown
    expr: up{job="browserbot"} == 0
    for: 30s
    labels:
      severity: critical
    annotations:
      summary: BrowserBot service is down
```

## Security Considerations

### Network Security

```nginx
# nginx.conf security headers
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    location / {
        proxy_pass http://browserbot-app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Secrets Management

```bash
# Use external secret management
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name browserbot/config \
  --secret-string '{"api_key":"your_api_key"}'

# Kubernetes secrets
kubectl create secret generic browserbot-secrets \
  --from-literal=api_key=your_api_key \
  --namespace=browserbot

# HashiCorp Vault
vault kv put secret/browserbot api_key=your_api_key
```

### Resource Limits

```yaml
# Security policies
apiVersion: policy/v1beta1
kind: PodSecurityPolicy
metadata:
  name: browserbot-psp
spec:
  privileged: false
  allowPrivilegeEscalation: false
  requiredDropCapabilities:
    - ALL
  volumes:
    - 'configMap'
    - 'emptyDir'
    - 'projected'
    - 'secret'
    - 'downwardAPI'
    - 'persistentVolumeClaim'
  runAsUser:
    rule: 'MustRunAsNonRoot'
  seLinux:
    rule: 'RunAsAny'
  fsGroup:
    rule: 'RunAsAny'
```

## Scaling Strategies

### Horizontal Pod Autoscaler (HPA)

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: browserbot-hpa
  namespace: browserbot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: browserbot-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Pod Autoscaler (VPA)

```yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: browserbot-vpa
  namespace: browserbot
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: browserbot-app
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
    - containerName: browserbot
      maxAllowed:
        cpu: 2
        memory: 4Gi
      minAllowed:
        cpu: 100m
        memory: 256Mi
```

## Troubleshooting

### Common Issues

1. **High Memory Usage**
   ```bash
   # Check memory usage
   kubectl top pods -n browserbot
   
   # Check browser processes
   kubectl exec -it browserbot-pod -- ps aux | grep chrome
   
   # Restart pods if needed
   kubectl rollout restart deployment/browserbot-app -n browserbot
   ```

2. **Connection Timeouts**
   ```bash
   # Check network connectivity
   kubectl exec -it browserbot-pod -- nslookup google.com
   
   # Check service endpoints
   kubectl get endpoints -n browserbot
   
   # Verify load balancer
   kubectl describe service browserbot-service -n browserbot
   ```

3. **Failed Browser Launches**
   ```bash
   # Check browser installation
   kubectl exec -it browserbot-pod -- which chromium-browser
   
   # Check display server
   kubectl exec -it browserbot-pod -- echo $DISPLAY
   
   # Check permissions
   kubectl exec -it browserbot-pod -- ls -la /tmp/.X11-unix/
   ```

### Debug Commands

```bash
# View logs
kubectl logs -f deployment/browserbot-app -n browserbot

# Debug container
kubectl exec -it browserbot-pod -n browserbot -- /bin/bash

# Port forward for testing
kubectl port-forward service/browserbot-service 8080:80 -n browserbot

# Scale deployment
kubectl scale deployment browserbot-app --replicas=5 -n browserbot

# Check resource usage
kubectl top nodes
kubectl top pods -n browserbot
```

### Health Check Endpoints

- **Health**: `GET /health` - Basic health check
- **Ready**: `GET /ready` - Readiness probe
- **Metrics**: `GET /metrics` - Prometheus metrics
- **Status**: `GET /status` - Detailed system status

### Log Analysis

```bash
# Search for errors
kubectl logs deployment/browserbot-app -n browserbot | grep ERROR

# Follow specific pod logs
kubectl logs -f browserbot-app-12345-abcde -n browserbot

# Export logs for analysis
kubectl logs deployment/browserbot-app -n browserbot > browserbot.log
```

This deployment guide provides comprehensive instructions for running BrowserBot in production environments with proper security, monitoring, and scaling configurations.
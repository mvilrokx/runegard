#!/usr/bin/env bash
set -euo pipefail

echo "==> Creating kind cluster (skips if exists)..."
kind create cluster --name runegard-demo 2>/dev/null || echo "Cluster already exists"

echo "==> Cleaning up previous demo resources..."
kubectl delete deployment broken-app --ignore-not-found
kubectl delete deployment oom-pod --ignore-not-found

echo "==> Creating CrashLoopBackOff pod..."
kubectl create deployment broken-app \
  --image=busybox -- /bin/sh -c "exit 1"

echo "==> Creating OOMKilled pod..."
kubectl apply -f - <<'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: oom-pod
spec:
  replicas: 1
  selector:
    matchLabels:
      app: oom-pod
  template:
    metadata:
      labels:
        app: oom-pod
    spec:
      containers:
      - name: oom
        image: busybox
        command: ["/bin/sh", "-c", "dd if=/dev/zero of=/dev/null bs=1G"]
        resources:
          limits:
            memory: "10Mi"
EOF

echo "==> Waiting for pods to fail..."
sleep 15

echo "==> Cluster ready. Current pods:"
kubectl get pods -A

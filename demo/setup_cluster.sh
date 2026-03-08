#!/usr/bin/env bash
set -euo pipefail

echo "Creating kind cluster..."
kind create cluster --name runegard-demo 2>/dev/null || echo "Cluster already exists"

echo "Seeding CrashLoopBackOff failure..."
kubectl create deployment broken-app \
  --image=busybox -- /bin/sh -c "exit 1" 2>/dev/null || true

echo "Waiting for pod to enter CrashLoopBackOff..."
sleep 15

echo "Cluster ready. Current pods:"
kubectl get pods -A

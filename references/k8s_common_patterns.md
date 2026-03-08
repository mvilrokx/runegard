# Common Kubernetes Failure Patterns

## CrashLoopBackOff
- Pod repeatedly crashes and K8s backs off restart attempts
- Check: `kubectl describe pod` Events section
- Common causes: OOMKilled, bad entrypoint, missing config, image issues
- Key indicators in describe output: "Back-off restarting failed container"

## OOMKilled
- Container exceeded memory limits
- Check: `kubectl describe pod` for "OOMKilled" in last state
- Fix: increase memory limits or fix memory leak

## ImagePullBackOff
- K8s cannot pull the container image
- Check: image name/tag, registry auth, imagePullSecrets
- Key indicators: "Failed to pull image", "ErrImagePull"

## Pending PVC
- PersistentVolumeClaim stuck in Pending
- Check: `kubectl describe pvc` for events
- Common causes: no matching PV, missing StorageClass, WaitForFirstConsumer

## ResourceQuota Exceeded
- Namespace resource limits reached
- Check: `kubectl describe quota -n <ns>`
- Fix: increase quota, reduce usage, or evict non-critical pods

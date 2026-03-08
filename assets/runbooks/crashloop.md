# Runbook: KubePodCrashLooping

## Trigger
Alert: KubePodCrashLooping -- Pod is restarting > 0.5/second

## Steps

### Step 1: Identify the crashing pod
- Run: `kubectl get pods --field-selector=status.phase!=Running -A`
- Look for pods with STATUS = CrashLoopBackOff

### Step 2: Get pod details
- Run: `kubectl describe pod <pod-name> -n <namespace>`
- Check the Events section for:
  - OOMKilled -> go to Step 5
  - ImagePullBackOff -> go to Step 6
  - Error or CrashLoopBackOff -> continue to Step 3

### Step 3: Check container logs
- Run: `kubectl logs <pod-name> -n <namespace> --previous`
- If logs show application error -> go to Step 4
- If logs are empty -> go to Step 7

### Step 4: Diagnose application error
- Review the error message in logs
- Common causes:
  - Missing environment variable -> check ConfigMap/Secret mounts
  - Database connection failure -> verify service DNS and network policies
  - Permission denied -> check RBAC and SecurityContext
- **Remediation**: Fix the root cause (may require deployment update)

### Step 5: Handle OOMKilled
- Run: `kubectl top pod <pod-name> -n <namespace>` (if metrics-server available)
- **Remediation**: Increase memory limits:
  `kubectl patch deployment <deploy-name> -n <namespace> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container>","resources":{"limits":{"memory":"512Mi"}}}]}}}}'`

### Step 6: Handle ImagePullBackOff
- Run: `kubectl describe pod <pod-name> -n <namespace> | grep -A5 "Events"`
- Verify image name and tag exist
- Check imagePullSecrets if using private registry
- **Remediation**: Fix image reference in deployment spec

### Step 7: Empty logs -- check init containers
- Run: `kubectl logs <pod-name> -n <namespace> -c <init-container> --previous`
- If init container is failing, diagnose its logs separately

### Verification
- Run: `kubectl get pods -n <namespace> | grep <pod-name>`
- Confirm STATUS = Running and RESTARTS has stopped incrementing
- Wait 2 minutes and re-check

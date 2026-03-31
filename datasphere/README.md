# DataSphere

The application used throughout the OCP4 Getting Started workshop series.

## Components

| Folder | What it is | How it's used in the labs |
|--------|-----------|--------------------------|
| `api/` | Python FastAPI backend | Built from source via S2I in Lab 2 |
| `ui/` | React + Nginx frontend | Deployed from pre-built image in Lab 1 |
| `gitops/` | Helm chart for the full 2-tier app | Deployed via `helm install` in Lab 2 |

## S2I source URL

When students build the API using Source-to-Image in Lab 2, the command is:

```bash
oc new-app python~https://github.com/rhpds/ocp4-getting-started-automation \
  --context-dir=datasphere/api \
  --name=datasphere-api
```

## Pre-built images

| Component | Image |
|-----------|-------|
| UI | `quay.io/nstephan/datasphere-ui:1.0.0` |
| API | `quay.io/nstephan/datasphere-api:1.0.0` |

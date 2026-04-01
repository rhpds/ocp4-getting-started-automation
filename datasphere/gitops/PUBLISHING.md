# DataSphere Helm Chart — Publishing to quay.io

The DataSphere Helm chart (`datasphere/gitops/`) is published to quay.io as an OCI artifact.
This makes it available in the OpenShift Developer Catalog via the `datasphere-helm-catalog`
platform workload (`HelmChartRepository` pointing at `oci://quay.io/rhpds`).

Republish the chart whenever `Chart.yaml` version is bumped or chart templates change.

---

## Prerequisites

- `helm` v3.8+ (OCI support is built in)
- Write access to `quay.io/rhpds` — use a robot account with push rights to `datasphere-chart`
- The `quay.io/rhpds/datasphere-chart` repository must exist and be set to **public**

---

## Steps

### 1. Bump the chart version (if content changed)

Edit [datasphere/gitops/Chart.yaml](Chart.yaml) and increment `version`:

```yaml
version: 1.1.0   # increment for any chart template change
appVersion: "1.1.0"  # match the image tags if changed
```

### 2. Package the chart

```bash
cd repos/ocp4-getting-started-automation
helm package datasphere/gitops -d /tmp/
```

Output: `/tmp/datasphere-<version>.tgz`

### 3. Log in to quay.io

```bash
helm registry login quay.io -u '<robot-account>' -p <robot-token>
```

### 4. Push the chart

```bash
helm push /tmp/datasphere-<version>.tgz oci://quay.io/rhpds
```

Verify at: `https://quay.io/repository/rhpds/datasphere-chart`

### 5. Enable the Helm catalog in the cluster CI (first publish only)

In `agd_v2/ocp4-getting-started-cluster/common.yaml`, add under `platformValues`:

```yaml
platformValues:
  developerPerspective:
    enabled: true
    ...
  datasphereHelmCatalog:
    enabled: true
    git:
      repoURL: https://github.com/rhpds/ocp4-getting-started-automation.git
      targetRevision: main
```

---

## Building and pushing images

Images live at `quay.io/rhpds/datasphere-ui` and `quay.io/rhpds/datasphere-api`.
Both must target `linux/amd64` — the CNV cluster architecture.

### API image

The API is pure Python with no native build step, so cross-compilation works fine:

```bash
cd repos/ocp4-getting-started-automation
podman build --platform linux/amd64 -t quay.io/rhpds/datasphere-api:1.1.0 datasphere/api/
podman push quay.io/rhpds/datasphere-api:1.1.0
```

### UI image (Apple Silicon caveat)

The UI Dockerfile has two stages: a Node.js build (runs `vite build`) and an nginx serve stage.
**The Node build stage crashes under QEMU amd64 emulation on Apple Silicon** — esbuild's Go
binary hits a fatal runtime error when emulated. Build the frontend natively instead:

```bash
cd repos/ocp4-getting-started-automation/datasphere/ui

# 1. Build the frontend natively (runs on arm64, output is platform-neutral JS/HTML)
npm ci
npm run build
# This produces datasphere/ui/dist/

# 2. Build the container image from the pre-built dist (no emulated npm step)
cd ../..   # back to repos/ocp4-getting-started-automation
podman build --platform linux/amd64 \
  -t quay.io/rhpds/datasphere-ui:1.1.0 \
  -f - . << 'EOF'
FROM registry.access.redhat.com/ubi9/nginx-122:latest
COPY datasphere/ui/dist /usr/share/nginx/html
COPY datasphere/ui/nginx.conf /etc/nginx/conf.d/datasphere.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
EOF

podman push quay.io/rhpds/datasphere-ui:1.1.0
```

> **On Linux (amd64 host):** The full multi-stage `Dockerfile` in `datasphere/ui/` works
> directly — no workaround needed:
> ```bash
> podman build --platform linux/amd64 -t quay.io/rhpds/datasphere-ui:1.1.0 datasphere/ui/
> ```

---

## When to republish

| Change | Republish needed? |
|--------|------------------|
| Chart template change (new resource, label, etc.) | Yes — bump version |
| `values.yaml` default change (image tag) | Yes — bump version |
| Lab content changes (adoc files) | No |
| Image rebuild only, same chart | Only if `appVersion` in Chart.yaml needs updating |
| `seed_data.py` or `main.py` change | Rebuild images, bump appVersion + chart version |

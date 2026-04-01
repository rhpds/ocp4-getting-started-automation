# DataSphere — Publishing Images and the Helm Chart

## How the Helm chart reaches the Developer Catalog

The chart is packaged and pushed to the cluster's Gitea Helm package registry automatically
by the `gitea-content-init` Job at cluster provision time. You do not need to publish the
chart to an external registry.

If you need to re-run the Job manually (e.g. after a chart update):

```bash
oc create job gitea-content-init-manual --from=job/gitea-content-init -n gitea
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
# This produces datasphere/ui/dist/ — commit the result so the Dockerfile can skip the build stage

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

## After rebuilding images

Update the image tags in `datasphere/gitops/values.yaml` and commit to main. The
`gitea-content-init` Job will push the updated chart on the next cluster provision.

---

## When to republish

| Change | Action needed |
|--------|--------------|
| `seed_data.py` or `main.py` change | Rebuild API image, bump tag in `values.yaml` |
| UI source change | Rebuild UI image (see Apple Silicon caveat above), bump tag in `values.yaml` |
| Chart template change | Bump `version` in `Chart.yaml`; chart is re-pushed automatically at next provision |
| Lab content only (adoc files) | No image or chart action needed |

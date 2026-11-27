# Local Kubernetes demo (not production)
Use an isolated local cluster such as kind with a default storage class. Do not use a shared or internet-accessible cluster. There is no ingress, LoadBalancer, external banking integration or production network policy. Redis has no authentication in this local-only example. Kubernetes secrets need cluster-side encryption and RBAC in a real deployment.

From the repo root, generate secrets, build and load the local image, then deploy in order:

    python3 scripts/init_demo_env.py
    docker build -f backend/Dockerfile -t arth-demo:0.9.0 .
    kind load docker-image arth-demo:0.9.0
    kubectl create namespace arth-demo
    kubectl -n arth-demo create secret generic arth-demo-secrets --from-env-file=.env
    kubectl -n arth-demo apply -f deploy/k8s/dependencies.yaml
    kubectl -n arth-demo rollout status statefulset/arth-db --timeout=120s
    kubectl -n arth-demo rollout status deployment/arth-redis --timeout=120s
    kubectl -n arth-demo apply -f deploy/k8s/migrate.yaml
    kubectl -n arth-demo wait --for=condition=complete job/arth-migrate-0001 --timeout=120s
    kubectl -n arth-demo apply -f deploy/k8s/app.yaml
    kubectl -n arth-demo rollout status deployment/arth-api --timeout=120s
    kubectl -n arth-demo port-forward --address 127.0.0.1 svc/arth-api 8000:8000

Use http://127.0.0.1:8000/docs. Never commit .env. Existing databases require baseline adoption as documented in docs/release.md. Do not delete the namespace if you need its data; deletion can remove persistent claims. Manifests are examples; cluster execution has not been verified.

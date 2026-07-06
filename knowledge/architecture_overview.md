# Architecture Overview

The VendorGuard platform is designed with a defense-in-depth security architecture, isolating services and data at multiple layers.

## 1. Hosting & Network Isolation
- **Orchestration**: All containerized services run on Google Kubernetes Engine (GKE) using private, hardened node pools.
- **Network Boundaries**: GKE nodes reside inside a private Google Cloud Virtual Private Cloud (VPC). No direct public ingress is allowed to nodes.
- **Ingress Traffic**: External traffic enters via Google Cloud HTTP(S) Load Balancer and is routed through a Cloud Armor Web Application Firewall (WAF) to protect against DDoS and OWASP Top 10 vulnerabilities.

## 2. Service Mesh & Service-to-Service Security
- **Service Mesh**: Istio is deployed within the GKE cluster to orchestrate service discovery and routing.
- **mutual TLS (mTLS)**: Strict mTLS is enforced for all pod-to-pod communications within the service mesh, ensuring encryption and cryptographic identity verification between services.

## 3. Secret and Credential Management
- **Secret Manager**: Database credentials, API tokens, and service keys are stored securely in GCP Secret Manager.
- **Dynamic Access**: Application pods retrieve secrets dynamically at runtime using IAM Service Account bindings (Workload Identity), eliminating static credentials in source code or environment variables.

## 4. Secure CI/CD Pipeline
- **Signed Images**: The deployment pipeline utilizes Cosign to sign container images upon passing automated unit, integration, and security scans.
- **Admission Controller**: GKE uses Binary Authorization to verify image signatures, preventing unsigned or untrusted images from being deployed to production.

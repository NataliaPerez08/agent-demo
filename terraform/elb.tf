# ELB resources for the data analyst agent are managed by the CCE cloud-controller-manager
# via the kubernetes.io/elb.autocreate annotation on the K8s LoadBalancer services.
# The CCM auto-creates ELBs, listeners, pools, and health checks.

# Kubeconfig temporal para el smoke test (local-exec necesita kubectl).
resource "local_file" "kubeconfig" {
  content  = huaweicloud_cce_cluster.agent.kube_config_raw
  filename = "${path.module}/.kubeconfig"

  lifecycle {
    ignore_changes = [content]
  }
}

# Smoke test post-deploy: espera a que los ELBs asignen EIPs y el API responda.
resource "terraform_data" "smoke" {
  provisioner "local-exec" {
    environment = {
      KUBECONFIG = local_file.kubeconfig.filename
      NS         = var.namespace
    }
    command = <<-EOT
      echo ">> esperando EIPs de los ELBs..."
      for i in $(seq 1 60); do
        API_IP=$(kubectl get svc api-elb -n "$NS" -o 'jsonpath={.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
        if [ -n "$API_IP" ]; then
          break
        fi
        sleep 10
      done

      if [ -z "$API_IP" ]; then
        echo "!! no se obtuvo EIP del API tras 10 min"
        exit 1
      fi

      CHATBOT_IP=$(kubectl get svc chatbot-elb -n "$NS" -o 'jsonpath={.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
      LITELLM_IP=$(kubectl get svc litellm-elb -n "$NS" -o 'jsonpath={.status.loadBalancer.ingress[0].ip}' 2>/dev/null)

      echo ">> EIPs asignados:"
      echo "   API:     $API_IP"
      echo "   Chatbot: $CHATBOT_IP"
      echo "   LiteLLM: $LITELLM_IP"

      echo ">> esperando a que el API responda..."
      for i in $(seq 1 60); do
        if curl -sf "http://$API_IP:8000/health" >/dev/null 2>&1; then
          echo ">> API OK: http://$API_IP:8000/health"
          echo ">> Chatbot:  http://$CHATBOT_IP:8001"
          echo ">> LiteLLM:  http://$LITELLM_IP:4000"
          exit 0
        fi
        sleep 10
      done
      echo "!! el API no respondio tras 10 min"
      exit 1
    EOT
  }

  depends_on = [
    kubernetes_manifest.api_elb,
    kubernetes_manifest.chatbot_elb,
    kubernetes_manifest.litellm_elb,
  ]
}

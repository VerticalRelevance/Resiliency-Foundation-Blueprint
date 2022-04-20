resource "aws_ssm_document" "StressMemory" {
  name            = "StressMemory"
  document_type   = "Command"
  document_format = "YAML"

  content = file("StressMemory.yml")
}

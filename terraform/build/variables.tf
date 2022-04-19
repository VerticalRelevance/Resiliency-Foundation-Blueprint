variable "codestar_connection_arn" {
  type        = string
  description = "ARN for the existing Codestar Connection"
}

variable "repository_id" {
  type        = string
  description = "Repository Path in Github"
}

variable "repository_branch" {
  type        = string
  description = "Repository branch of the resiliency code"
}

variable "domain_name" {
  type        = string
  description = "Domain for the CodeArtifact repository"
}

variable "repo_name" {
  type        = string
  description = "Name of the CodeArtifact repository"
}

variable "owner" {
  type        = string
  description = "Owner of the CodeArtifact repository"
}
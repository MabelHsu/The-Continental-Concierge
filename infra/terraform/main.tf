# ============================================================
# The Continental Concierge — Terraform Infrastructure
# ============================================================
# Provisions: AlloyDB, Cloud Run, Artifact Registry,
#             Secret Manager, IAM, VPC for AlloyDB.
# ============================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  backend "gcs" {
    # Configure: bucket = "your-tf-state-bucket"
  }
}

variable "project_id" {
  type        = string
  description = "Google Cloud project ID"
}

variable "region" {
  type        = string
  default     = "us-central1"
  description = "Google Cloud region"
}

variable "db_password" {
  type        = string
  sensitive   = true
  description = "AlloyDB continental_app user password"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable APIs ───────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "alloydb.googleapis.com",
    "aiplatform.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "compute.googleapis.com",
    "servicenetworking.googleapis.com",
    "cloudresourcemanager.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# ── VPC for AlloyDB ───────────────────────────────────────────

resource "google_compute_network" "continental_vpc" {
  name                    = "continental-vpc"
  auto_create_subnetworks = false
  depends_on              = [google_project_service.apis]
}

resource "google_compute_subnetwork" "continental_subnet" {
  name          = "continental-subnet"
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region
  network       = google_compute_network.continental_vpc.id
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "continental-private-ip"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.continental_vpc.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.continental_vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
}

# ── AlloyDB Cluster & Instance ────────────────────────────────

resource "google_alloydb_cluster" "continental" {
  cluster_id = "continental-cluster"
  location   = var.region

  network_config {
    network = google_compute_network.continental_vpc.id
  }

  initial_user {
    user     = "continental_app"
    password = var.db_password
  }

  database_version = "POSTGRES_15"

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_alloydb_instance" "continental_primary" {
  cluster       = google_alloydb_cluster.continental.name
  instance_id   = "continental-primary"
  instance_type = "PRIMARY"

  machine_config {
    cpu_count = 2  # Start small, scale as needed
  }

  database_flags = {
    "google_ml_integration.enable_model_support" = "on"
  }

  depends_on = [google_alloydb_cluster.continental]
}

# ── Secret Manager ────────────────────────────────────────────

resource "google_secret_manager_secret" "db_password" {
  secret_id = "continental-db-password"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password
}

# ── Artifact Registry ────────────────────────────────────────

resource "google_artifact_registry_repository" "continental" {
  repository_id = "continental"
  format        = "DOCKER"
  location      = var.region
  description   = "Continental Concierge container images"
  depends_on    = [google_project_service.apis]
}

# ── Service Account ───────────────────────────────────────────

resource "google_service_account" "continental_sa" {
  account_id   = "continental-sa"
  display_name = "Continental Concierge Service Account"
}

# IAM bindings
resource "google_project_iam_member" "continental_roles" {
  for_each = toset([
    "roles/alloydb.client",
    "roles/aiplatform.user",
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.continental_sa.email}"
}

# ── Cloud Run (MCP Server) ───────────────────────────────────

resource "google_cloud_run_v2_service" "mcp_server" {
  name     = "continental-mcp"
  location = var.region

  template {
    service_account = google_service_account.continental_sa.email

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/continental/mcp-server:latest"

      ports {
        container_port = 8080
      }

      env {
        name  = "ALLOYDB_HOST"
        value = "127.0.0.1"
      }
      env {
        name  = "ALLOYDB_DATABASE"
        value = "continental"
      }
      env {
        name  = "ALLOYDB_USER"
        value = "continental_app"
      }
      env {
        name = "ALLOYDB_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_password.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }

    # AlloyDB Auth Proxy sidecar
    containers {
      image = "gcr.io/alloydb-connectors/alloydb-auth-proxy:latest"
      args = [
        "${var.project_id}:${var.region}:continental-cluster",
        "--port=5432",
      ]
      resources {
        limits = {
          cpu    = "0.5"
          memory = "256Mi"
        }
      }
    }

    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }

    vpc_access {
      network_interfaces {
        network    = google_compute_network.continental_vpc.name
        subnetwork = google_compute_subnetwork.continental_subnet.name
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  depends_on = [
    google_alloydb_instance.continental_primary,
    google_artifact_registry_repository.continental,
  ]
}

# ── Outputs ───────────────────────────────────────────────────

output "alloydb_cluster_id" {
  value = google_alloydb_cluster.continental.cluster_id
}

output "alloydb_instance_ip" {
  value = google_alloydb_instance.continental_primary.ip_address
}

output "mcp_server_url" {
  value = google_cloud_run_v2_service.mcp_server.uri
}

output "artifact_registry" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/continental"
}

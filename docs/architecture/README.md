<!-- omit in toc -->
# Architecture Overview

<!-- omit in toc -->
## Table of Contents
- [Repository Layout](#repository-layout)
  - [Telescope Control](#telescope-control)
  - [Backend \& Data](#backend--data)
  - [Frontend \& Web](#frontend--web)
  - [Infrastructure \& Docs](#infrastructure--docs)

## Repository Layout

### Telescope Control
| Repository | Description |
|-------------|-------------|
| `telescope-robotics` | Controls telescope movement and low-level operations. |
| `telescope-data-handler` | Handles SDR streams, telemetry & commands, and data uploading from the telescope. |

### Backend & Data
| Repository | Description |
|-------------|-------------|
| `database` | Database schema definitions, migrations, and seed data. |
| `backend` | Main backend for web and data APIs (interfacing with telescope control through Kafka and the frontend through REST). |

### Frontend & Web
| Repository | Description |
|-------------|-------------|
| `web` | The main website of Astro, written in Angular. (served on astrobeam.gr) |
| `apps` | Frontend applications for data visualization and user interaction. (served on apps.astrobeam.gr) |

### Infrastructure & Docs
| Repository | Description |
|-------------|-------------|
| `infrastructure` | Deployment automation, IaC (Terraform, Ansible, Docker Compose, etc.). |
| `knowledgebase` | Centralized documentation, onboarding, design notes, and scripts. |
| `.github` *(org-wide)* | Issue/PR templates, contribution guide, and CI/CD workflows shared across repos. |

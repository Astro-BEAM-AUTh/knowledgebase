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
| `telescope-manual-control` | Interfaces for manual or local control of telescope motors, sensors, etc. |
| `telescope-automated-control` | Autonomous control algorithms and consumer of commands from the backend. |
| `telescope-data-handler` | Handles SDR streams, telemetry & commands, and data uploading from the telescope. |

### Backend & Data
| Repository | Description |
|-------------|-------------|
| `database` | Database schema definitions, migrations, and seed data. |
| `backend` | Main backend for web and data APIs (interfacing with telescope control through Kafka and the frontend through REST). |

### Frontend & Web
| Repository | Description |
|-------------|-------------|
| `web-frontend` | The main web interface for telescope monitoring and data visualization. |
| `team-website` | Public-facing static site for project info and updates. |

> **Note:** The above may be merged into one repository with the backend in the future, depending on a conversation with the team.

### Infrastructure & Docs
| Repository | Description |
|-------------|-------------|
| `infrastructure` | Deployment automation, IaC (Terraform, Ansible, Docker Compose, etc.). |
| `knowledgebase` | Centralized documentation, onboarding, design notes, and scripts. |
| `.github` *(org-wide)* | Issue/PR templates, contribution guide, and CI/CD workflows shared across repos. |
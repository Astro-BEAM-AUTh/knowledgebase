<!-- omit in toc -->
# Knowledgebase: GitHub Organization Structure & Conventions

<!-- omit in toc -->
## Table of Contents
- [🏛️ Overview](#️-overview)
- [🧩 1. Teams \& Access](#-1-teams--access)
  - [Core Teams](#core-teams)
  - [Permissions](#permissions)
- [🧠 2. Knowledgebase Layout](#-2-knowledgebase-layout)
- [🧭 3. Quick Links](#-3-quick-links)


## 🏛️ Overview

This document defines the structure and conventions for our GitHub organization.  
Our goal is to maintain clarity, consistency, and collaboration across all telescope software efforts - from robotic control to data processing and user interfaces.

## 🧩 1. Teams & Access

### Core Teams
| Team | Subteams | Description |
|------|-----------|--------------|
| **Robotics** | - | Low-level telescope control and hardware integration. |
| **Software** | `Data Analysis`, `Telescope`, `Website`, `BackEnd`, `Database` | Main software effort, divided into focused domains. |
| **`Data Analysis`** | - | Data processing, SDR signal handling, image analysis. |
| **`Website`** | - | Public-facing static site and web interfaces. |
| **`BackEnd`** | - | API development, database management, and server-side logic. |
| **`Telescope`** | - | Telescope's side of Back End integration and control logic. |
| **`Database`** | - | Database design, management, and query optimization. |

### Permissions
- **Write:** All organization members.
- **Admin:** Repository maintainers or tech lead. (for now @kesoglidis and @dyka3773)


## 🧠 2. Knowledgebase Layout

The `knowledgebase` repo includes:
```
/docs
├── architecture/
├── hardware/
├── onboarding/
├── protocols/
├── research-how-tos/
└── software-guidelines/
```

Recommended pages:
- `docs/architecture/system-architecture/readme.md` - high-level system architecture.
- `docs/onboarding/developer-setup.md` - new developer guide.
- `docs/protocols/` - telescope comms, SDR formats, telemetry schema.


## 🧭 3. Quick Links

- [Organization Home](https://github.com/Astro-BEAM-AUTh)
- [Knowledgebase Repo](https://github.com/Astro-BEAM-AUTh/knowledgebase)
- [Contribution Guide](https://github.com/Astro-BEAM-AUTh/.github/blob/main/CONTRIBUTING.md)

**Document maintained by:** Iraklis Konsoulas (@dyka3773) - Software Team

**Feedback:** Open an issue or PR in the `knowledgebase` repo.

<!-- omit in toc -->
# ASTRO Software Architecture

<!-- omit in toc -->
## Table of Contents
- [Components](#components)
  - [Control Room (or Cloud)](#control-room-or-cloud)
    - [Frontend:](#frontend)
    - [Backend:](#backend)
    - [Database:](#database)
    - [Storage Bucket?:](#storage-bucket)
    - [Kafka Broker:](#kafka-broker)
  - [Telescope Control System (TCS)](#telescope-control-system-tcs)
    - [Raspberry Pi 4 (Telescope Movement Control):](#raspberry-pi-4-telescope-movement-control)
    - [Raspberry Pi 4 (SDR and Data Handling):](#raspberry-pi-4-sdr-and-data-handling)
    - [Raspberry Pi 4 (Manual Telescope Control):](#raspberry-pi-4-manual-telescope-control)


## Components
### Control Room (or Cloud)
#### Frontend:
- **Angular** for building a responsive web interface.
#### Backend:
- **FastAPI**
  - Handles user authentication, session management, and API endpoints for the frontend.
  - Serves data visualizations and telescope status updates to the frontend.
- Connects to Telescope Control System via Kafka for asynchronous command sending
- Sends email notifications using an SMTP server to the user about observation status and alerts.
#### Database:
- **PostgreSQL** for structured data storage
  - **TimescaleDB** extension for time-series data?
#### Storage Bucket?:
- **AWS S3**, **Google Cloud Storage** or **Azure Blob Storage** for storing large datasets and observation files.
> Note: IDK if we need this yet, perhaps we can just use the TimescaleDB for everything.
#### Kafka Broker:
- **Apache Kafka** for real-time data streaming between the Control Room and Telescope
  - Facilitates communication between the backend and the Telescope Control System.
  - Ensures reliable message delivery and processing for commands and data.
  - 1 topic for commands from Control Room to Telescope and the other way around. eg: 
    - CR->Telescope: start observation in X direction for Y time by Z user
    - Telescope->CR: observation complete for X direction by Y user, data at `<link to storage>`
  - 1 topic for data from Telescope to Control Room
    - Could be used in tandem with a Kafka Connect sink to store data directly into the TimescaleDB or Storage Bucket.


### Telescope Control System (TCS)
#### Raspberry Pi 4 (Telescope Movement Control):
- Controls low-level operations of the telescope such as motor control
- Communicates with the Kafka server to receive commands from the Control Room
#### Raspberry Pi 4 (SDR and Data Handling):
- Manages the SDR for radio signal processing.
- Handles communication with the cloud services via Kafka.
  - Sends processed data to the cloud for storage and analysis.
  - Receives commands and configuration updates from the cloud.
- Is connected to an external storage (e.g., SSD) for temporary data buffering and preventing data loss in case of network issues.
#### Raspberry Pi 4 (Manual Telescope Control):
- Controls manual movement of the telescope.


> See also [System Architecture Diagram](architecture-diagram.html) for a visual representation of the architecture.

# Langflow AI Prototyping Environment

## Overview

This project provides a **Langflow-based environment** for rapid AI prototyping. It leverages a set of **containerized services** to facilitate experimentation with Langflow, Weaviate for vector storage, and various monitoring tools. The setup does **not** include an inference service. It includes Weaviate, Postgres and Redis.

NOTE: Langflow now has a [desktop client](https://www.langflow.org/desktop-form-complete), simplifying setup. The default `docker-compose.yml` now excludes self-hosted Langflow and Postgres. Use `docker-compose-langflow.yml` for a fully self-hosted browser-based setup.

## Components

### **Core Services**

- **Langflow** – Main UI for building AI workflows
- **PostgreSQL** – Database backend for Langflow
- **Weaviate** – Vector database for AI memory storage (available at endpoint: `/v1/graphql`)

- **Weaviate Embeddings** – Handles local text embedding with `BAAI/bge-base-en-v1.5`
- **Redis** – Caching layer first used instead of chat history shoveling but could be useful elsewhere
- **RedisInsight** – Web-based Redis management UI (for database inspection)

### **Embeddings Setup**

- The system uses **Weaviate’s module** with `BAAI/bge-base-en-v1.5 (ONNX, CPU-optimized)`. CPU was chosen to leave VRAM for model inference.
- The embeddings service runs in a dedicated container (`langflow-weaviate-embeddings`).

### **Networking & Ports**

The following services are available at:

| Service              | External URL                                   | Internal Container & Port                   |
| -------------------- | ---------------------------------------------- | ------------------------------------------- |
| **Langflow UI**      | [http://10.0.0.11:7878](http://10.0.0.11:7878) | `langflow:7860`                             |
| **Weaviate**         | [http://10.0.0.11:8181](http://10.0.0.11:8181) | `langflow-weaviate:8080`                    |
| **Weaviate gRPC**    | n/a                                            | `langflow-weaviate:50051`                   |
| **Embeddings**       | n/a                                            | `langflow-weaviate-embeddings:8080`         |
| **PostgreSQL**       | n/a                                            | `langflow-postgres:5432`                    |
| **Redis**            | n/a                                            | `langflow-redis:6379`                       |
| **RedisInsight**     | [http://10.0.0.11:6380](http://10.0.0.11:6380) | `langflow-redisinsight:6380`                |

## **Project Configuration & Utilities**

### **Configuration Files**

- **Sample Langflow flows and Weaviate vector DB classes** can be found in the `config/` directory.

### **Schema Setup**

This project includes `setup_weaviate.py` for a repeatable way to load a new schema into the vector database and populate it with sample data:

🛠 Commands:
  --add-class <Collection>      Add schema from JSON (e.g. Memory_v1)
  --add-sample <Collection>     Add sample data from corresponding _samples.py
  --clear-sample <Collection>   Delete objects tagged as 'sample'
  --clear-all <Collection>      Delete all objects in collection

| Command                       | Description                                           |
| ----------------------------- | ----------------------------------------------------- |
| `--add-class <Collection>`    | Add schema from JSON (e.g. Memory_v1) |
|  `--add-sample <Collection>`  | Add sample data from corresponding samples.py |
|  `--clear-sample <Collection>`| Delete objects tagged as 'sample' |
|  `--clear-all <Collection>`   | Delete all objects in collection |

## **Usage**

1. **Start the environment**
   ```sh
   docker-compose up -d
   ```
2. **Initialize Weaviate schema**
   
   Add a sample schema  (loads `config/weaviate/Memory_v1.json`)
   ```sh
   python --add-class Memory_v1
   ```
   
   *Add sample data (optional)*

   (loads `config/weaviate/Memory_v1_samples.py`)
   ```sh
   python --add-sample Memory_v1
   ```
3. **Verify Weaviate schema and data**

   Verify the schema directly `http://10.0.0.11:8181/v1/schema` or use a GraphQL client
   [Altair GraphQL Client](https://altairgraphql.dev/) (think: Postman for Graph databases). You may save collections of queries in `agc` format.
   
   Note: A collection of queries is located in `config/weaviate/Memory_v1.agc`

4. **Setup Langflow Desktop Client**

   Install the [Langflow macOS desktop client](https://www.langflow.org/desktop-form-complete) or direct your browser to yoru locally hosted Langflow

   Load sample workflows located in `./config/flows`

## **Notes**

- As stated setup does **not** include an LLM inference service.
- Uses Docker volumes instead of host file system mapping for ease erasure
- **All containers are running as root. Do not expose this project to the open web**

# Langflow AI Prototyping Environment

**DO NOT USE IN PRODUCTION**

## Overview

This project provides a **Langflow-based environment** for rapid AI prototyping. It leverages a set of **containerized services** to facilitate experimentation with Langflow, Weaviate for vector storage, and various monitoring tools. The setup does **not** include an inference service.

## Components

### **Core Services**

- **Langflow** – Main UI for building AI workflows
- **PostgreSQL** – Database backend for Langflow and Hasura
- **Weaviate** – Vector database for AI memory storage
- **Weaviate Embeddings** – Handles local text embedding with `BAAI/bge-base-en-v1.5`
- **Redis** – Caching layer first used instead of chat history shoveling but could be useful elsewhere

### **Monitoring & Web UI Services**

- **RedisInsight** – Web-based Redis management UI (for database inspection)
- **Hasura** – GraphQL API engine. While built for Postgres, an action may be set up for inspection of Weaviate
- **Hasura Data Connector** – Enables external database integrations
- **OpenTelemetry (OTEL)** – Centralized logging and tracing

### **Embeddings Setup**

- The system uses **Weaviate’s ****\`\`**** module** with **BAAI/bge-base-en-v1.5 (ONNX, CPU-optimized)**. CPU was chosen to leave VRAM for model inference.
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
| **Hasura UI**        | [http://10.0.0.11:8182](http://10.0.0.11:8182) | `langflow-hasura:8080`                      |
| **Hasura Connector** | [http://10.0.0.11:8081](http://10.0.0.11:8081) | `langflow-hasura-data-connector:8081`       |
| **OpenTelemetry**    | n/a                                            | `langflow-otel:4317` (gRPC) / `4318` (HTTP) |

## **Project Configuration & Utilities**

### **Configuration Files**

- **Sample Langflow flows and Weaviate vector DB classes** can be found in the `config/` directory.

### **Makefile Automation**

This project includes a `Makefile` for common tasks:

| Command                     | Description                                           |
| --------------------------- | ----------------------------------------------------- |
| `make init-weaviate`        | Initializes the Weaviate schema from `Memory_v1.json` |
| `make view-weaviate-schema` | Fetches the current Weaviate schema for review        |

## **Usage**

1. **Start the environment**
   ```sh
   docker-compose up -d
   ```
2. **Initialize Weaviate schema**
   This is hard-coded for a specific schema right now (`config/weaviate/Memory_v1.json`)
   ```sh
   make init-weaviate
   ```
3. **Verify Weaviate schema**
   ```sh
   make view-weaviate-schema
   ```
4. **Connect Hasura to Weaviate** (optional)
    
    We are going to create various Actions in Hasura to map Weaviate's REST API for use with GraphQL

    **Query Memories**
    1. Go to `Actions` > `Create`
    2. Action definition
        ```
        type Query {
            """
            Langflow Weaviate
            """
            queryWeaviate: WeaviateResponse
            }
        ```
    3. Type Configuration
        ```
        type WeaviateResponse {
            result: String!
            }
        ```
    4. Webhook (HTTP/S) Handler
        
        `http://langflow-weaviate:8080/v1/graphql`
    5. Click `Add Payload Transform`
        1. Sample Input (should pre-populate)
            ```
            {
                "action": {
                    "name": "queryWeaviate"
                },
                "input": {}
            }
            ```
        2. Configure Request Body
            ```
            {
                "query": "{ Get { Memory_v1 { content timestamp tags source importance relatedMemories { ... on Memory_v1 { content timestamp } } _additional { id } } } }"
            }
            ```
    6. Click `Add Response Transform`
        1. Configure Response Body
            ```
            {
                "result": {{ $body }}
            }
            ```
    7. Click `Save Action`
    8. Test Action
    In API tab run the following query:
    ```
    query {
        queryWeaviate {
            result
        }
    }
    ```
    
    **Mutate (add) memory**
    1. Go to `Actions` > `Create`
    2. Action definition
        ```
        type Mutation {
            """
            Weaviate Mutation - Insert
            """
            insertMemoryV1(
                content: String!
                timestamp: String!
                tags: [String!]
                source: String!
                importance: Int!
                relatedMemories: [String!]
            ): MemoryV1Response
            }
        ```
    3. Type Configuration
        ```
        type MemoryV1Response {
            success: Boolean!
            message: String!
        }
        ```
    4. Webhook (HTTP/S) Handler
        
        `http://langflow-weaviate:8080/v1/objects`
    5. Click `Add Payload Transform`
        1. Sample Input (should pre-populate)
            ```
            {
                "action": {
                    "name": "insertMemoryV1"
                },
                "input": {
                    "content": "content",
                    "timestamp": "timestamp",
                    "source": "source",
                    "importance": 10
                }
            }
            ```
        2. Configure Request Body (ignore validation failure message)
            ```
            {
                "class": "Memory_v1",
                "properties": {
                    "content": {{$body.input.content}},
                    "timestamp": {{$body.input.timestamp}},
                    "tags": {{$body.input.tags}},
                    "source": {{$body.input.source}},
                    "importance": {{$body.input.importance}},
                    "relatedMemories": {{$body.input.relatedMemories}}
                }
            }
            ```
    6. Click `Add Response Transform`
        1. Configure Response Body
            ```
            {
                "success": {{ $body.id != null }},
                "message": "Memory inserted successfully with ID: {{ $body.id }}"
            }
            ```
    7. Click `Save Action`    
    8. Test Action
        ```
        mutation {
            insertMemoryV1(
                content: "Ozmo is a SaaS company focused on Human and AI-powered solutions to improve complex technical support."
                timestamp: "2025-02-09T15:00:00Z"
                tags: ["SaaS", "AI", "Technical Support"]
                source: "knowledge_base"
                importance: 7
                relatedMemories: []
            ) {
                success
                message
            }
        }
        ```

## **Notes**

- As stated setup does **not** include an LLM inference service.
- Uses Docker volumes instead of host file system mapping for ease erasure
- **All containers are running as root. Do not expose this project to the open web**

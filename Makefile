WEAVIATE_HOST=10.0.0.11
WEAVIATE_PORT=8181
SCHEMA_FILE=./config/weaviate/Memory_v1.json

.PHONY: init-weaviate view-weaviate-schema

init-weaviate:
	@echo "Initializing Weaviate schema from $(SCHEMA_FILE)..."
	@curl -X POST "http://$(WEAVIATE_HOST):$(WEAVIATE_PORT)/v1/schema" \
	  -H "Content-Type: application/json" \
	  --data-binary @$(SCHEMA_FILE)
	@echo "Schema initialized. Verify with 'make view-weaviate-schema'..."
view-weaviate-schema:
	@curl -X GET "http://$(WEAVIATE_HOST):$(WEAVIATE_PORT)/v1/schema" | jq

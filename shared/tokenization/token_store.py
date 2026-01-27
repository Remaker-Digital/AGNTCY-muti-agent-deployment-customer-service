"""
Token Store Module

Provides storage backends for PII token mappings.
Primary: Azure Key Vault (production)
Fallback: Cosmos DB (if latency >100ms)
Mock: In-memory (Phase 1-3)
"""

import asyncio
import logging
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenMapping:
    """Represents a token-to-PII mapping."""
    token: str
    original_value: str
    pii_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    context_id: Optional[str] = None  # Conversation/session context


class TokenStore(ABC):
    """Abstract base class for token storage backends."""

    @abstractmethod
    async def store(self, mapping: TokenMapping) -> bool:
        """Store a token mapping."""
        pass

    @abstractmethod
    async def retrieve(self, token: str) -> Optional[TokenMapping]:
        """Retrieve a token mapping."""
        pass

    @abstractmethod
    async def delete(self, token: str) -> bool:
        """Delete a token mapping."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired token mappings. Returns count deleted."""
        pass

    def generate_token(self) -> str:
        """Generate a new unique token."""
        return f"TOKEN_{uuid.uuid4()}"


class InMemoryTokenStore(TokenStore):
    """
    In-memory token store for development and testing (Phase 1-3).

    NOT suitable for production - data is lost on restart.
    """

    def __init__(self, default_ttl_hours: int = 24):
        self._store: Dict[str, TokenMapping] = {}
        self._default_ttl = timedelta(hours=default_ttl_hours)
        self._lock = asyncio.Lock()

    async def store(self, mapping: TokenMapping) -> bool:
        """Store a token mapping in memory."""
        async with self._lock:
            if mapping.expires_at is None:
                mapping.expires_at = datetime.utcnow() + self._default_ttl
            self._store[mapping.token] = mapping
            logger.debug(f"Stored token {mapping.token[:20]}... for {mapping.pii_type}")
            return True

    async def retrieve(self, token: str) -> Optional[TokenMapping]:
        """Retrieve a token mapping from memory."""
        async with self._lock:
            mapping = self._store.get(token)
            if mapping is None:
                return None
            if mapping.expires_at and datetime.utcnow() > mapping.expires_at:
                del self._store[token]
                return None
            return mapping

    async def delete(self, token: str) -> bool:
        """Delete a token mapping from memory."""
        async with self._lock:
            if token in self._store:
                del self._store[token]
                return True
            return False

    async def cleanup_expired(self) -> int:
        """Remove all expired token mappings."""
        async with self._lock:
            now = datetime.utcnow()
            expired = [
                token for token, mapping in self._store.items()
                if mapping.expires_at and now > mapping.expires_at
            ]
            for token in expired:
                del self._store[token]
            return len(expired)

    @property
    def size(self) -> int:
        """Return the number of stored mappings."""
        return len(self._store)


class KeyVaultTokenStore(TokenStore):
    """
    Azure Key Vault token store for production (Phase 4-5).

    Provides highest security with managed encryption and audit logs.
    """

    def __init__(
        self,
        vault_url: Optional[str] = None,
        credential=None,
        default_ttl_hours: int = 24
    ):
        """
        Initialize Key Vault token store.

        Args:
            vault_url: Azure Key Vault URL (defaults to KEYVAULT_URI env var)
            credential: Azure credential (defaults to DefaultAzureCredential)
            default_ttl_hours: Default TTL for tokens
        """
        self._vault_url = vault_url or os.getenv("KEYVAULT_URI")
        self._default_ttl = timedelta(hours=default_ttl_hours)
        self._client = None
        self._credential = credential

        if not self._vault_url:
            logger.warning("KEYVAULT_URI not set - Key Vault store unavailable")

    async def _get_client(self):
        """Lazy initialization of Key Vault client."""
        if self._client is None:
            try:
                from azure.identity.aio import DefaultAzureCredential
                from azure.keyvault.secrets.aio import SecretClient

                if self._credential is None:
                    self._credential = DefaultAzureCredential()

                self._client = SecretClient(
                    vault_url=self._vault_url,
                    credential=self._credential
                )
                logger.info(f"Key Vault client initialized: {self._vault_url}")
            except ImportError:
                logger.error("azure-identity or azure-keyvault-secrets not installed")
                raise
        return self._client

    async def store(self, mapping: TokenMapping) -> bool:
        """Store a token mapping in Key Vault."""
        try:
            client = await self._get_client()

            # Key Vault secret names have restrictions - use sanitized token
            secret_name = self._sanitize_secret_name(mapping.token)

            # Store the mapping as JSON
            import json
            secret_value = json.dumps({
                "original_value": mapping.original_value,
                "pii_type": mapping.pii_type,
                "created_at": mapping.created_at.isoformat(),
                "context_id": mapping.context_id
            })

            # Set expiration
            expires_on = mapping.expires_at or (datetime.utcnow() + self._default_ttl)

            await client.set_secret(
                secret_name,
                secret_value,
                expires_on=expires_on,
                content_type="application/json"
            )

            logger.debug(f"Stored token in Key Vault: {secret_name[:20]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to store token in Key Vault: {e}")
            return False

    async def retrieve(self, token: str) -> Optional[TokenMapping]:
        """Retrieve a token mapping from Key Vault."""
        try:
            client = await self._get_client()
            secret_name = self._sanitize_secret_name(token)

            secret = await client.get_secret(secret_name)

            if secret.value is None:
                return None

            import json
            data = json.loads(secret.value)

            return TokenMapping(
                token=token,
                original_value=data["original_value"],
                pii_type=data["pii_type"],
                created_at=datetime.fromisoformat(data["created_at"]),
                expires_at=secret.properties.expires_on,
                context_id=data.get("context_id")
            )

        except Exception as e:
            logger.debug(f"Token not found in Key Vault: {e}")
            return None

    async def delete(self, token: str) -> bool:
        """Delete a token mapping from Key Vault."""
        try:
            client = await self._get_client()
            secret_name = self._sanitize_secret_name(token)

            # Start deletion
            poller = await client.begin_delete_secret(secret_name)
            await poller.wait()

            logger.debug(f"Deleted token from Key Vault: {secret_name[:20]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to delete token from Key Vault: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """
        Key Vault handles expiration automatically.
        This method is a no-op for Key Vault.
        """
        return 0

    def _sanitize_secret_name(self, token: str) -> str:
        """
        Sanitize token for use as Key Vault secret name.

        Key Vault secret names:
        - Must be 1-127 characters
        - Alphanumeric and dashes only
        """
        # Remove TOKEN_ prefix and convert to valid format
        name = token.replace("TOKEN_", "pii-").replace("_", "-")
        # Ensure valid characters
        name = "".join(c if c.isalnum() or c == "-" else "-" for c in name)
        return name[:127]

    async def close(self):
        """Close the Key Vault client."""
        if self._client:
            await self._client.close()
            self._client = None


class CosmosDBTokenStore(TokenStore):
    """
    Cosmos DB token store as fallback when Key Vault latency is too high.

    Lower latency (10-20ms) but less secure than Key Vault.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        database_name: str = "agntcy-cs",
        container_name: str = "pii-tokens",
        default_ttl_hours: int = 24
    ):
        """
        Initialize Cosmos DB token store.

        Args:
            endpoint: Cosmos DB endpoint (defaults to COSMOS_ENDPOINT env var)
            database_name: Database name
            container_name: Container name
            default_ttl_hours: Default TTL for tokens
        """
        self._endpoint = endpoint or os.getenv("COSMOS_ENDPOINT")
        self._database_name = database_name
        self._container_name = container_name
        self._default_ttl = timedelta(hours=default_ttl_hours)
        self._client = None
        self._container = None

    async def _get_container(self):
        """Lazy initialization of Cosmos DB container."""
        if self._container is None:
            try:
                from azure.cosmos.aio import CosmosClient
                from azure.identity.aio import DefaultAzureCredential

                credential = DefaultAzureCredential()
                self._client = CosmosClient(self._endpoint, credential=credential)
                database = self._client.get_database_client(self._database_name)
                self._container = database.get_container_client(self._container_name)

                logger.info(f"Cosmos DB client initialized: {self._endpoint}")
            except ImportError:
                logger.error("azure-cosmos not installed")
                raise
        return self._container

    async def store(self, mapping: TokenMapping) -> bool:
        """Store a token mapping in Cosmos DB."""
        try:
            container = await self._get_container()

            expires_at = mapping.expires_at or (datetime.utcnow() + self._default_ttl)
            ttl_seconds = int((expires_at - datetime.utcnow()).total_seconds())

            document = {
                "id": mapping.token,
                "partitionKey": mapping.pii_type,
                "original_value": mapping.original_value,
                "pii_type": mapping.pii_type,
                "created_at": mapping.created_at.isoformat(),
                "expires_at": expires_at.isoformat(),
                "context_id": mapping.context_id,
                "ttl": ttl_seconds  # Cosmos DB auto-deletes expired items
            }

            await container.create_item(document)
            logger.debug(f"Stored token in Cosmos DB: {mapping.token[:20]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to store token in Cosmos DB: {e}")
            return False

    async def retrieve(self, token: str) -> Optional[TokenMapping]:
        """Retrieve a token mapping from Cosmos DB."""
        try:
            container = await self._get_container()

            # Query by token ID
            query = "SELECT * FROM c WHERE c.id = @token"
            items = container.query_items(
                query=query,
                parameters=[{"name": "@token", "value": token}],
                enable_cross_partition_query=True
            )

            async for item in items:
                return TokenMapping(
                    token=item["id"],
                    original_value=item["original_value"],
                    pii_type=item["pii_type"],
                    created_at=datetime.fromisoformat(item["created_at"]),
                    expires_at=datetime.fromisoformat(item["expires_at"]) if item.get("expires_at") else None,
                    context_id=item.get("context_id")
                )

            return None

        except Exception as e:
            logger.debug(f"Token not found in Cosmos DB: {e}")
            return None

    async def delete(self, token: str) -> bool:
        """Delete a token mapping from Cosmos DB."""
        try:
            container = await self._get_container()

            # Need to find the partition key first
            mapping = await self.retrieve(token)
            if mapping is None:
                return False

            await container.delete_item(token, partition_key=mapping.pii_type)
            logger.debug(f"Deleted token from Cosmos DB: {token[:20]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to delete token from Cosmos DB: {e}")
            return False

    async def cleanup_expired(self) -> int:
        """
        Cosmos DB handles TTL-based expiration automatically.
        This method is a no-op.
        """
        return 0

    async def close(self):
        """Close the Cosmos DB client."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton token store instance
_token_store: Optional[TokenStore] = None


def get_token_store() -> TokenStore:
    """
    Get the appropriate token store based on environment.

    Returns:
        TokenStore instance (Key Vault for production, in-memory for dev)
    """
    global _token_store

    if _token_store is not None:
        return _token_store

    # Check environment
    use_azure = os.getenv("USE_AZURE_TOKENSTORE", "").lower() == "true"
    keyvault_uri = os.getenv("KEYVAULT_URI")

    if use_azure and keyvault_uri:
        logger.info("Using Azure Key Vault token store")
        _token_store = KeyVaultTokenStore(vault_url=keyvault_uri)
    else:
        logger.info("Using in-memory token store (development mode)")
        _token_store = InMemoryTokenStore()

    return _token_store


async def set_token_store(store: TokenStore):
    """Set the global token store instance (for testing)."""
    global _token_store
    _token_store = store

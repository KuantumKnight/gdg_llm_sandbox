"""Provider failures with explicit retry and attempt-charging semantics."""

from __future__ import annotations


class ProviderError(Exception):
    code = "PROVIDER_UNAVAILABLE"
    retryable = True
    chargeable = True


class ProviderCredentialRequiredError(ProviderError):
    code = "PROVIDER_CREDENTIAL_REQUIRED"
    retryable = False
    chargeable = False


class ProviderCredentialRejectedError(ProviderError):
    code = "PROVIDER_CREDENTIAL_REJECTED"
    retryable = False
    chargeable = False


class ProviderConfigurationError(ProviderError):
    code = "PROVIDER_CONFIGURATION_ERROR"
    retryable = False
    chargeable = False


class ProviderRateLimitedError(ProviderError):
    code = "PROVIDER_RATE_LIMITED"
    chargeable = False


class ProviderTimeoutError(ProviderError):
    code = "PROVIDER_TIMEOUT"


class ProviderUnavailableError(ProviderError):
    code = "PROVIDER_UNAVAILABLE"


class ProviderMalformedResponseError(ProviderError):
    code = "PROVIDER_MALFORMED_RESPONSE"
    retryable = False

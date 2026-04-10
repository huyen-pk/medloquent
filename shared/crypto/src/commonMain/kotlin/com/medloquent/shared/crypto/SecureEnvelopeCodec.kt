package com.medloquent.shared.crypto

import kotlinx.serialization.Serializable
import kotlin.io.encoding.Base64
import kotlin.io.encoding.ExperimentalEncodingApi

@Serializable
data class ProtectedEnvelope(
    val algorithm: String,
    val keyAlias: String,
    val ciphertext: String,
)

interface SecureEnvelopeCodec {
    fun protect(
        plaintext: String,
        keyAlias: String,
    ): ProtectedEnvelope

    fun reveal(envelope: ProtectedEnvelope): String
}

@OptIn(ExperimentalEncodingApi::class)
class DemoEnvelopeCodec : SecureEnvelopeCodec {
    override fun protect(
        plaintext: String,
        keyAlias: String,
    ): ProtectedEnvelope = ProtectedEnvelope(
        algorithm = "demo-base64-envelope",
        keyAlias = keyAlias,
        ciphertext = Base64.encode(plaintext.encodeToByteArray()),
    )

    override fun reveal(envelope: ProtectedEnvelope): String = Base64
        .decode(envelope.ciphertext)
        .decodeToString()
}

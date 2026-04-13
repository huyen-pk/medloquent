package com.medloquent.shared.lora

import com.medloquent.shared.core.FederatedModelUpdate
import com.medloquent.shared.core.SyncPriority
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
data class LoRaPacket(
    val packetId: String,
    val priority: SyncPriority,
    val payloadBytes: Int,
    val compressedPayload: String,
    val queuedAt: Instant = Clock.System.now(),
)

interface LoraSyncTransport {
    suspend fun queue(update: FederatedModelUpdate): LoRaPacket

    fun queued(): List<LoRaPacket>
}

class InMemoryLoraSyncTransport(
    private val json: Json = Json { encodeDefaults = true },
) : LoraSyncTransport {
    private val queue = mutableListOf<LoRaPacket>()

    override suspend fun queue(update: FederatedModelUpdate): LoRaPacket {
        val packet = LoRaPacket(
            packetId = "lora-${queue.size + 1}",
            priority = update.priority,
            payloadBytes = update.payloadSizeBytes,
            compressedPayload = json.encodeToString(update.topLayerDeltas).take(180),
        )
        queue += packet
        return packet
    }

    override fun queued(): List<LoRaPacket> = queue.toList()
}

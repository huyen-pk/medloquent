package com.medloquent.shared.fl

import com.medloquent.shared.core.FederatedFeature
import com.medloquent.shared.core.FederatedModelUpdate
import com.medloquent.shared.core.LocalModelDescriptor
import com.medloquent.shared.core.StructuredClinicalNote
import com.medloquent.shared.core.SyncPriority
import com.medloquent.shared.core.TrainingConsent
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

interface FederatedLearningClient {
    suspend fun prepareUpdate(
        note: StructuredClinicalNote,
        consent: TrainingConsent,
    ): FederatedModelUpdate?
}

class LayerWiseFedAvgClient(
    private val modelDescriptor: LocalModelDescriptor,
    private val json: Json = Json { encodeDefaults = true },
) : FederatedLearningClient {
    override suspend fun prepareUpdate(
        note: StructuredClinicalNote,
        consent: TrainingConsent,
    ): FederatedModelUpdate? {
        if (!consent.participates) {
            return null
        }

        val featureDeltas = note.transcript.text
            .lowercase()
            .split(Regex("[^a-z0-9]+"))
            .filter { it.length > 3 }
            .groupingBy { token -> token }
            .eachCount()
            .entries
            .sortedByDescending { it.value }
            .take(8)
            .map { entry -> FederatedFeature(name = entry.key, weight = entry.value.toDouble()) }

        return FederatedModelUpdate(
            deviceId = consent.deviceId,
            modelName = modelDescriptor.name,
            modelVersion = modelDescriptor.version,
            quantization = modelDescriptor.quantization,
            priority = if (featureDeltas.size <= 4) SyncPriority.CRITICAL else SyncPriority.ROUTINE,
            topLayerDeltas = featureDeltas,
            payloadSizeBytes = json.encodeToString(featureDeltas).encodeToByteArray().size,
        )
    }
}

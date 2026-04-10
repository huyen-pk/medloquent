package com.medloquent.shared.core

import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.serialization.Serializable

@Serializable
data class PatientContext(
    val patientId: String,
    val encounterId: String,
    val clinicianId: String,
    val capturedAt: Instant = Clock.System.now(),
)

@Serializable
data class SpeechSession(
    val sessionId: String,
    val patient: PatientContext,
    val locale: String = "en-US",
    val startedAt: Instant = Clock.System.now(),
)

@Serializable
data class AudioChunk(
    val index: Int,
    val sampleRateHz: Int,
    val pcm16: String,
    val metadata: Map<String, String> = emptyMap(),
)

@Serializable
data class TranscriptSegment(
    val chunkIndex: Int,
    val text: String,
    val confidence: Double,
)

@Serializable
data class Transcript(
    val text: String,
    val confidence: Double,
    val segments: List<TranscriptSegment>,
)

@Serializable
enum class ClinicalSection {
    CHIEF_COMPLAINT,
    HISTORY_OF_PRESENT_ILLNESS,
    ASSESSMENT,
    PLAN,
    MEDICATIONS,
    VITALS,
    ALLERGIES,
}

val ClinicalSection.label: String
    get() = when (this) {
        ClinicalSection.CHIEF_COMPLAINT -> "Chief Complaint"
        ClinicalSection.HISTORY_OF_PRESENT_ILLNESS -> "History of Present Illness"
        ClinicalSection.ASSESSMENT -> "Assessment"
        ClinicalSection.PLAN -> "Plan"
        ClinicalSection.MEDICATIONS -> "Medications"
        ClinicalSection.VITALS -> "Vitals"
        ClinicalSection.ALLERGIES -> "Allergies"
    }

@Serializable
enum class ClinicalEntityType {
    CONDITION,
    SYMPTOM,
    MEDICATION,
    ALLERGY,
    VITAL_SIGN,
    PROCEDURE,
}

@Serializable
data class ClinicalEntity(
    val type: ClinicalEntityType,
    val display: String,
    val codingSystem: String,
    val code: String,
    val section: ClinicalSection,
)

@Serializable
data class VitalSign(
    val name: String,
    val value: String,
    val unit: String,
)

@Serializable
data class StructuredClinicalNote(
    val transcript: Transcript,
    val summary: String,
    val sections: Map<String, String>,
    val entities: List<ClinicalEntity>,
    val vitals: List<VitalSign>,
    val problemList: List<String>,
    val planItems: List<String>,
)

@Serializable
data class LocalModelDescriptor(
    val name: String,
    val version: String,
    val runtime: String,
    val quantization: String,
)

@Serializable
enum class SyncPriority {
    CRITICAL,
    ROUTINE,
    BULK,
}

@Serializable
data class FederatedFeature(
    val name: String,
    val weight: Double,
)

@Serializable
data class FederatedModelUpdate(
    val deviceId: String,
    val modelName: String,
    val modelVersion: String,
    val quantization: String,
    val priority: SyncPriority,
    val topLayerDeltas: List<FederatedFeature>,
    val payloadSizeBytes: Int,
    val createdAt: Instant = Clock.System.now(),
)

@Serializable
data class TrainingConsent(
    val deviceId: String,
    val participates: Boolean,
)

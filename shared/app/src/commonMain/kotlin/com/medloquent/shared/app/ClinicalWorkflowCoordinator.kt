package com.medloquent.shared.app

import com.medloquent.shared.audio.AudioCaptureRequest
import com.medloquent.shared.core.PatientContext
import com.medloquent.shared.core.SpeechSession
import com.medloquent.shared.core.TrainingConsent
import kotlinx.datetime.Clock


data class DictationDraft(
    val patientId: String,
    val encounterId: String,
    val clinicianId: String,
    val dictationText: String,
    val participateInFederatedLearning: Boolean,
)

data class ClinicalWorkflowResult(
    val transcriptText: String,
    val transcriptConfidence: Double,
    val summary: String,
    val sections: Map<String, String>,
    val entities: List<String>,
    val vitals: List<String>,
    val bundleJson: String,
    val storedPath: String,
    val federatedPacketId: String?,
    val federatedPayloadBytes: Int,
    val queuedPacketCount: Int,
)

class ClinicalWorkflowCoordinator(
    private val services: MedLoquentServices,
) {
    suspend fun process(draft: DictationDraft): ClinicalWorkflowResult {
        require(draft.dictationText.isNotBlank()) {
            "Dictation is required before the offline pipeline can run."
        }

        val timestamp = Clock.System.now().toEpochMilliseconds()
        val patient = PatientContext(
            patientId = draft.patientId.trim().ifBlank { "patient-$timestamp" },
            encounterId = draft.encounterId.trim().ifBlank { "encounter-$timestamp" },
            clinicianId = draft.clinicianId.trim().ifBlank { "clinician-edge" },
        )
        val session = SpeechSession(
            sessionId = "session-$timestamp",
            patient = patient,
        )

        val chunks = services.audioCaptureEngine.capture(
            session = session,
            request = AudioCaptureRequest(seedTranscript = draft.dictationText),
        )
        val transcript = services.asrEngine.transcribe(session, chunks)
        val note = services.nlpPipeline.structure(patient, transcript)
        val bundle = services.fhirBundleMapper.map(patient, note)
        val storedRecord = services.clinicalRecordStore.save(bundle)
        val federatedUpdate = services.federatedLearningClient.prepareUpdate(
            note = note,
            consent = TrainingConsent(
                deviceId = services.deviceId,
                participates = draft.participateInFederatedLearning,
            ),
        )
        val queuedPacket = federatedUpdate?.let { services.loraSyncTransport.queue(it) }

        return ClinicalWorkflowResult(
            transcriptText = transcript.text,
            transcriptConfidence = transcript.confidence,
            summary = note.summary,
            sections = note.sections,
            entities = note.entities.map { "${it.display} (${it.code})" },
            vitals = note.vitals.map { "${it.name}: ${it.value} ${it.unit}".trim() },
            bundleJson = services.fhirBundleMapper.prettyPrint(bundle),
            storedPath = storedRecord.bundlePath,
            federatedPacketId = queuedPacket?.packetId,
            federatedPayloadBytes = federatedUpdate?.payloadSizeBytes ?: 0,
            queuedPacketCount = services.loraSyncTransport.queued().size,
        )
    }
}

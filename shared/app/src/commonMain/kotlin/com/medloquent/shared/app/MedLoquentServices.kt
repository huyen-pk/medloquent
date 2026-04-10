package com.medloquent.shared.app

import com.medloquent.shared.asr.OfflineMedicalAsrEngine
import com.medloquent.shared.asr.StreamingAsrEngine
import com.medloquent.shared.audio.AudioCaptureEngine
import com.medloquent.shared.audio.SeededAudioCaptureEngine
import com.medloquent.shared.crypto.DemoEnvelopeCodec
import com.medloquent.shared.ehr.DefaultFhirBundleMapper
import com.medloquent.shared.ehr.FhirBundleMapper
import com.medloquent.shared.fl.FederatedLearningClient
import com.medloquent.shared.fl.LayerWiseFedAvgClient
import com.medloquent.shared.lora.InMemoryLoraSyncTransport
import com.medloquent.shared.lora.LoraSyncTransport
import com.medloquent.shared.nlp.ClinicalNlpPipeline
import com.medloquent.shared.nlp.RuleBasedClinicalNlpPipeline
import com.medloquent.shared.storage.ClinicalRecordStore
import com.medloquent.shared.storage.JsonFileClinicalRecordStore

data class MedLoquentServices(
    val deviceId: String,
    val audioCaptureEngine: AudioCaptureEngine,
    val asrEngine: StreamingAsrEngine,
    val nlpPipeline: ClinicalNlpPipeline,
    val fhirBundleMapper: FhirBundleMapper,
    val clinicalRecordStore: ClinicalRecordStore,
    val federatedLearningClient: FederatedLearningClient,
    val loraSyncTransport: LoraSyncTransport,
)

object MedLoquentServiceFactory {
    fun create(
        storageRoot: String,
        deviceId: String,
    ): MedLoquentServices {
        val asrEngine = OfflineMedicalAsrEngine()

        return MedLoquentServices(
            deviceId = deviceId,
            audioCaptureEngine = SeededAudioCaptureEngine(),
            asrEngine = asrEngine,
            nlpPipeline = RuleBasedClinicalNlpPipeline(),
            fhirBundleMapper = DefaultFhirBundleMapper(),
            clinicalRecordStore = JsonFileClinicalRecordStore(
                storageRoot = storageRoot,
                codec = DemoEnvelopeCodec(),
            ),
            federatedLearningClient = LayerWiseFedAvgClient(modelDescriptor = asrEngine.model),
            loraSyncTransport = InMemoryLoraSyncTransport(),
        )
    }
}

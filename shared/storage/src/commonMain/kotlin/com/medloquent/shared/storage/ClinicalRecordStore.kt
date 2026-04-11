package com.medloquent.shared.storage

import com.medloquent.shared.crypto.ProtectedEnvelope
import com.medloquent.shared.crypto.SecureEnvelopeCodec
import com.medloquent.shared.ehr.FhirBundle
import kotlinx.datetime.Clock
import kotlinx.datetime.Instant
import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okio.FileSystem
import okio.Path.Companion.toPath

@Serializable
data class StoredEhrDocument(
    val recordId: String,
    val bundlePath: String,
    val storedAt: Instant = Clock.System.now(),
)

interface ClinicalRecordStore {
    suspend fun save(bundle: FhirBundle): StoredEhrDocument

    suspend fun load(record: StoredEhrDocument): FhirBundle
}

class JsonFileClinicalRecordStore(
    private val storageRoot: String,
    private val codec: SecureEnvelopeCodec,
    private val keyAlias: String = "ehr-bundle",
    private val json: Json = Json {
        prettyPrint = true
        encodeDefaults = true
        ignoreUnknownKeys = true
    },
) : ClinicalRecordStore {
    private val bundleDirectory = "$storageRoot/ehr".toPath()

    override suspend fun save(bundle: FhirBundle): StoredEhrDocument {
        defaultFileSystem().createDirectories(bundleDirectory)

        val recordId = bundle.entry
            .firstOrNull { it.resource.resourceType == "Composition" }
            ?.resource
            ?.id
            ?: "bundle-${Clock.System.now().toEpochMilliseconds()}"
        val bundlePath = "${bundleDirectory.toString()}/$recordId.json".toPath()
        val envelope = codec.protect(
            plaintext = json.encodeToString(bundle),
            keyAlias = keyAlias,
        )

        defaultFileSystem().write(bundlePath) {
            writeUtf8(json.encodeToString(envelope))
        }

        return StoredEhrDocument(
            recordId = recordId,
            bundlePath = bundlePath.toString(),
        )
    }

    override suspend fun load(record: StoredEhrDocument): FhirBundle {
        val serializedEnvelope = defaultFileSystem().read(record.bundlePath.toPath()) {
            readUtf8()
        }
        val envelope = json.decodeFromString<ProtectedEnvelope>(serializedEnvelope)
        return json.decodeFromString(codec.reveal(envelope))
    }
}

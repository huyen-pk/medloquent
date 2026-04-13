package com.medloquent.shared.ehr

import com.medloquent.shared.core.ClinicalEntity
import com.medloquent.shared.core.ClinicalEntityType
import com.medloquent.shared.core.PatientContext
import com.medloquent.shared.core.StructuredClinicalNote
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Serializable
data class FhirIdentifier(
    val system: String,
    val value: String,
)

@Serializable
data class FhirCoding(
    val system: String,
    val code: String,
    val display: String,
)

@Serializable
data class FhirCodeableConcept(
    val coding: List<FhirCoding>,
    val text: String,
)

@Serializable
data class FhirReference(
    val reference: String,
    val display: String? = null,
)

@Serializable
data class FhirAnnotation(
    val text: String,
)

@Serializable
data class FhirQuantity(
    val value: Double,
    val unit: String,
)

@Serializable
data class FhirResource(
    val resourceType: String,
    val id: String,
    val status: String? = null,
    val identifier: List<FhirIdentifier> = emptyList(),
    val subject: FhirReference? = null,
    val encounter: FhirReference? = null,
    val code: FhirCodeableConcept? = null,
    val category: List<FhirCodeableConcept> = emptyList(),
    val valueString: String? = null,
    val valueQuantity: FhirQuantity? = null,
    val note: List<FhirAnnotation> = emptyList(),
    val clinicalStatus: FhirCodeableConcept? = null,
    val description: String? = null,
    val text: String? = null,
)

@Serializable
data class FhirBundleEntry(
    val fullUrl: String,
    val resource: FhirResource,
)

@Serializable
data class FhirBundle(
    val resourceType: String = "Bundle",
    val type: String = "collection",
    val timestamp: String,
    val entry: List<FhirBundleEntry>,
)

interface FhirBundleMapper {
    fun map(
        patient: PatientContext,
        note: StructuredClinicalNote,
    ): FhirBundle

    fun prettyPrint(bundle: FhirBundle): String
}

class DefaultFhirBundleMapper(
    private val json: Json = Json {
        prettyPrint = true
        encodeDefaults = true
    },
) : FhirBundleMapper {
    override fun map(
        patient: PatientContext,
        note: StructuredClinicalNote,
    ): FhirBundle {
        val patientRef = FhirReference(reference = "Patient/${patient.patientId}", display = patient.patientId)
        val encounterRef = FhirReference(reference = "Encounter/${patient.encounterId}", display = patient.encounterId)

        val baseResources = listOf(
            FhirResource(
                resourceType = "Patient",
                id = patient.patientId,
                identifier = listOf(FhirIdentifier(system = "urn:medloquent:patient-id", value = patient.patientId)),
                text = "Offline patient reference",
            ),
            FhirResource(
                resourceType = "Encounter",
                id = patient.encounterId,
                status = "finished",
                subject = patientRef,
                identifier = listOf(FhirIdentifier(system = "urn:medloquent:encounter-id", value = patient.encounterId)),
                text = "Captured by clinician ${patient.clinicianId}",
            ),
            FhirResource(
                resourceType = "Composition",
                id = "composition-${patient.encounterId}",
                status = "final",
                subject = patientRef,
                encounter = encounterRef,
                note = listOf(FhirAnnotation(note.summary)),
                text = note.sections.entries.joinToString(separator = "\n") { (section, content) -> "$section: $content" },
            ),
        )

        val conditionResources = note.entities
            .filter { it.type == ClinicalEntityType.CONDITION || it.type == ClinicalEntityType.SYMPTOM }
            .mapIndexed { index, entity ->
                FhirResource(
                    resourceType = "Condition",
                    id = "condition-${patient.encounterId}-$index",
                    clinicalStatus = FhirCodeableConcept(
                        coding = listOf(FhirCoding("http://terminology.hl7.org/CodeSystem/condition-clinical", "active", "Active")),
                        text = "active",
                    ),
                    subject = patientRef,
                    encounter = encounterRef,
                    code = toConcept(entity),
                    note = listOf(FhirAnnotation("Extracted from offline clinical NLP pipeline")),
                )
            }

        val medicationResources = note.entities
            .filter { it.type == ClinicalEntityType.MEDICATION }
            .mapIndexed { index, entity ->
                FhirResource(
                    resourceType = "MedicationStatement",
                    id = "medication-${patient.encounterId}-$index",
                    status = "active",
                    subject = patientRef,
                    encounter = encounterRef,
                    code = toConcept(entity),
                    note = listOf(FhirAnnotation("Mentioned in dictation")),
                )
            }

        val observationResources = note.vitals.mapIndexed { index, vital ->
            val numericValue = vital.value.toDoubleOrNull()
            FhirResource(
                resourceType = "Observation",
                id = "observation-${patient.encounterId}-$index",
                status = "final",
                subject = patientRef,
                encounter = encounterRef,
                code = FhirCodeableConcept(
                    coding = listOf(FhirCoding("urn:medloquent:vital", vital.name.lowercase().replace(" ", "-"), vital.name)),
                    text = vital.name,
                ),
                valueString = numericValue?.let { null } ?: vital.value,
                valueQuantity = numericValue?.let { FhirQuantity(value = it, unit = vital.unit) },
            )
        }

        val entries = (baseResources + conditionResources + medicationResources + observationResources).map { resource ->
            FhirBundleEntry(
                fullUrl = "urn:uuid:${resource.id}",
                resource = resource,
            )
        }

        return FhirBundle(
            timestamp = patient.capturedAt.toString(),
            entry = entries,
        )
    }

    override fun prettyPrint(bundle: FhirBundle): String = json.encodeToString(bundle)

    private fun toConcept(entity: ClinicalEntity): FhirCodeableConcept = FhirCodeableConcept(
        coding = listOf(
            FhirCoding(
                system = entity.codingSystem,
                code = entity.code,
                display = entity.display,
            ),
        ),
        text = entity.display,
    )
}

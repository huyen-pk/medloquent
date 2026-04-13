package com.medloquent.shared.nlp

import com.medloquent.shared.core.ClinicalEntity
import com.medloquent.shared.core.ClinicalEntityType
import com.medloquent.shared.core.ClinicalSection
import com.medloquent.shared.core.ClinicalSection.ALLERGIES
import com.medloquent.shared.core.ClinicalSection.ASSESSMENT
import com.medloquent.shared.core.ClinicalSection.CHIEF_COMPLAINT
import com.medloquent.shared.core.ClinicalSection.HISTORY_OF_PRESENT_ILLNESS
import com.medloquent.shared.core.ClinicalSection.MEDICATIONS
import com.medloquent.shared.core.ClinicalSection.PLAN
import com.medloquent.shared.core.ClinicalSection.VITALS
import com.medloquent.shared.core.PatientContext
import com.medloquent.shared.core.StructuredClinicalNote
import com.medloquent.shared.core.Transcript
import com.medloquent.shared.core.VitalSign
import com.medloquent.shared.core.label

private data class LexiconEntry(
    val phrase: String,
    val type: ClinicalEntityType,
    val system: String,
    val code: String,
    val display: String,
    val section: ClinicalSection,
)

interface ClinicalNlpPipeline {
    suspend fun structure(
        patient: PatientContext,
        transcript: Transcript,
    ): StructuredClinicalNote
}

class RuleBasedClinicalNlpPipeline : ClinicalNlpPipeline {
    private val lexicon = listOf(
        LexiconEntry("chest pain", ClinicalEntityType.SYMPTOM, "http://snomed.info/sct", "29857009", "Chest pain", CHIEF_COMPLAINT),
        LexiconEntry("shortness of breath", ClinicalEntityType.SYMPTOM, "http://snomed.info/sct", "267036007", "Shortness of breath", CHIEF_COMPLAINT),
        LexiconEntry("hypertension", ClinicalEntityType.CONDITION, "http://snomed.info/sct", "38341003", "Hypertension", ASSESSMENT),
        LexiconEntry("type 2 diabetes", ClinicalEntityType.CONDITION, "http://snomed.info/sct", "44054006", "Type 2 diabetes mellitus", ASSESSMENT),
        LexiconEntry("penicillin", ClinicalEntityType.ALLERGY, "http://snomed.info/sct", "91936005", "Penicillin allergy", ALLERGIES),
        LexiconEntry("metformin", ClinicalEntityType.MEDICATION, "http://www.nlm.nih.gov/research/umls/rxnorm", "860975", "Metformin", MEDICATIONS),
        LexiconEntry("lisinopril", ClinicalEntityType.MEDICATION, "http://www.nlm.nih.gov/research/umls/rxnorm", "29046", "Lisinopril", MEDICATIONS),
        LexiconEntry("x ray", ClinicalEntityType.PROCEDURE, "http://snomed.info/sct", "168537006", "Radiography", PLAN),
    )

    override suspend fun structure(
        patient: PatientContext,
        transcript: Transcript,
    ): StructuredClinicalNote {
        val normalized = transcript.text.lowercase()
        val entities = lexicon
            .filter { normalized.contains(it.phrase) }
            .map {
                ClinicalEntity(
                    type = it.type,
                    display = it.display,
                    codingSystem = it.system,
                    code = it.code,
                    section = it.section,
                )
            }

        val vitals = extractVitals(transcript.text)
        val problemList = entities
            .filter { it.type == ClinicalEntityType.CONDITION || it.type == ClinicalEntityType.SYMPTOM }
            .map { it.display }
            .distinct()
        val planItems = derivePlan(problemList, entities, vitals)
        val sections = buildSections(transcript.text, entities, vitals, planItems)
        val summary = buildSummary(patient, problemList, vitals)

        return StructuredClinicalNote(
            transcript = transcript,
            summary = summary,
            sections = sections,
            entities = entities,
            vitals = vitals,
            problemList = problemList,
            planItems = planItems,
        )
    }

    private fun buildSummary(
        patient: PatientContext,
        problemList: List<String>,
        vitals: List<VitalSign>,
    ): String {
        val headline = if (problemList.isEmpty()) {
            "Encounter ${patient.encounterId} captured for patient ${patient.patientId}."
        } else {
            "Encounter ${patient.encounterId} documents ${problemList.joinToString()} for patient ${patient.patientId}."
        }

        val vitalSummary = if (vitals.isEmpty()) {
            "No vitals extracted from the dictation."
        } else {
            "Extracted vitals: ${vitals.joinToString { "${it.name} ${it.value}${it.unit}".trim() }}."
        }

        return "$headline $vitalSummary"
    }

    private fun buildSections(
        transcript: String,
        entities: List<ClinicalEntity>,
        vitals: List<VitalSign>,
        planItems: List<String>,
    ): Map<String, String> {
        val symptoms = entities
            .filter { it.type == ClinicalEntityType.SYMPTOM }
            .joinToString { it.display }
            .ifBlank { "Narrative captured from dictation." }
        val assessment = entities
            .filter { it.type == ClinicalEntityType.CONDITION }
            .joinToString { it.display }
            .ifBlank { "Assessment pending clinician review." }
        val medications = entities
            .filter { it.type == ClinicalEntityType.MEDICATION }
            .joinToString { it.display }
            .ifBlank { "No medications called out in the transcript." }
        val allergies = entities
            .filter { it.type == ClinicalEntityType.ALLERGY }
            .joinToString { it.display }
            .ifBlank { "No allergy statements captured." }
        val vitalText = vitals
            .joinToString { "${it.name}: ${it.value} ${it.unit}".trim() }
            .ifBlank { "No structured vitals extracted." }

        return linkedMapOf(
            CHIEF_COMPLAINT.label to symptoms,
            HISTORY_OF_PRESENT_ILLNESS.label to transcript,
            ASSESSMENT.label to assessment,
            PLAN.label to planItems.joinToString().ifBlank { "Continue monitoring and review locally stored draft." },
            MEDICATIONS.label to medications,
            VITALS.label to vitalText,
            ALLERGIES.label to allergies,
        )
    }

    private fun derivePlan(
        problemList: List<String>,
        entities: List<ClinicalEntity>,
        vitals: List<VitalSign>,
    ): List<String> {
        val plan = mutableListOf<String>()

        if (problemList.any { it.contains("Chest pain", ignoreCase = true) }) {
            plan += "Obtain ECG and continue symptom monitoring"
        }
        if (problemList.any { it.contains("Hypertension", ignoreCase = true) }) {
            plan += "Trend blood pressure locally and review antihypertensive adherence"
        }
        if (entities.any { it.display.contains("Metformin", ignoreCase = true) }) {
            plan += "Continue metformin and review glucose logs"
        }
        if (vitals.isNotEmpty()) {
            plan += "Persist FHIR Observation resources for extracted vitals"
        }
        if (plan.isEmpty()) {
            plan += "Finalize clinician note and store encrypted FHIR bundle"
        }

        return plan.distinct()
    }

    private fun extractVitals(text: String): List<VitalSign> {
        val vitals = mutableListOf<VitalSign>()
        val lowercase = text.lowercase()

        Regex("blood pressure\\s+(\\d{2,3}/\\d{2,3})").find(lowercase)?.groupValues?.getOrNull(1)?.let {
            vitals += VitalSign(name = "Blood Pressure", value = it, unit = "mmHg")
        }
        Regex("heart rate\\s+(\\d{2,3})").find(lowercase)?.groupValues?.getOrNull(1)?.let {
            vitals += VitalSign(name = "Heart Rate", value = it, unit = "bpm")
        }
        Regex("temp(?:erature)?\\s+(\\d{2}(?:\\.\\d)?)").find(lowercase)?.groupValues?.getOrNull(1)?.let {
            vitals += VitalSign(name = "Temperature", value = it, unit = "C")
        }
        Regex("oxygen saturation\\s+(\\d{2,3})").find(lowercase)?.groupValues?.getOrNull(1)?.let {
            vitals += VitalSign(name = "Oxygen Saturation", value = it, unit = "%")
        }

        return vitals
    }
}

package com.medloquent.shared.app

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedCard
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

private const val SampleDictation = "Patient presents with chest pain and shortness of breath. History significant for hypertension and type 2 diabetes. Blood pressure 148/92 heart rate 88 temperature 37.1 oxygen saturation 96. Continue lisinopril and metformin. Allergy to penicillin."

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MedLoquentApp(
    storageRoot: String,
    deviceId: String,
    onShareBundle: ((String) -> Unit)? = null,
    modifier: Modifier = Modifier,
) {
    val services = remember(storageRoot, deviceId) {
        MedLoquentServiceFactory.create(
            storageRoot = storageRoot,
            deviceId = deviceId,
        )
    }
    val coordinator = remember(services) { ClinicalWorkflowCoordinator(services) }
    val coroutineScope = rememberCoroutineScope()
    val scrollState = rememberScrollState()

    var patientId by rememberSaveable { mutableStateOf("patient-001") }
    var encounterId by rememberSaveable { mutableStateOf("encounter-001") }
    var clinicianId by rememberSaveable { mutableStateOf("dr-edge") }
    var dictationText by rememberSaveable { mutableStateOf(SampleDictation) }
    var participateInFl by rememberSaveable { mutableStateOf(true) }
    var result by remember { mutableStateOf<ClinicalWorkflowResult?>(null) }
    var isProcessing by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    MaterialTheme {
        Surface(modifier = modifier.fillMaxSize()) {
            Scaffold(
                topBar = {
                    TopAppBar(
                        title = { Text("MedLoquent") },
                    )
                },
            ) { paddingValues ->
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .verticalScroll(scrollState)
                        .padding(paddingValues)
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    HeadlineCard(deviceId = deviceId)
                    OutlinedTextField(
                        value = patientId,
                        onValueChange = { patientId = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Patient ID") },
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = encounterId,
                        onValueChange = { encounterId = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Encounter ID") },
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = clinicianId,
                        onValueChange = { clinicianId = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Clinician ID") },
                        singleLine = true,
                    )
                    OutlinedTextField(
                        value = dictationText,
                        onValueChange = { dictationText = it },
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 180.dp),
                        label = { Text("Offline clinical dictation") },
                        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences),
                    )
                    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text("On-device federated learning")
                                Text(
                                    text = "Queue compressed top-layer deltas for low-bandwidth LoRa sync.",
                                    style = MaterialTheme.typography.bodySmall,
                                )
                            }
                            Switch(
                                checked = participateInFl,
                                onCheckedChange = { participateInFl = it },
                            )
                        }
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        Button(
                            onClick = {
                                errorMessage = null
                                isProcessing = true
                                coroutineScope.launch {
                                    runCatching {
                                        coordinator.process(
                                            DictationDraft(
                                                patientId = patientId,
                                                encounterId = encounterId,
                                                clinicianId = clinicianId,
                                                dictationText = dictationText,
                                                participateInFederatedLearning = participateInFl,
                                            ),
                                        )
                                    }.onSuccess {
                                        result = it
                                    }.onFailure {
                                        errorMessage = it.message
                                    }
                                    isProcessing = false
                                }
                            },
                            enabled = !isProcessing,
                            modifier = Modifier.weight(1f),
                        ) {
                            if (isProcessing) {
                                CircularProgressIndicator(modifier = Modifier.padding(end = 8.dp))
                            }
                            Text("Run offline pipeline")
                        }
                        OutlinedButton(
                            onClick = {
                                dictationText = SampleDictation
                                errorMessage = null
                            },
                            modifier = Modifier.weight(1f),
                        ) {
                            Text("Load sample")
                        }
                    }
                    errorMessage?.let {
                        Text(
                            text = it,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }
                    result?.let {
                        ResultCard(
                            result = it,
                            onShareBundle = onShareBundle,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun HeadlineCard(deviceId: String) {
    OutlinedCard(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                text = "Fully offline clinical dictation to FHIR",
                style = MaterialTheme.typography.headlineSmall,
            )
            Text(
                text = "ASR, clinical structuring, encrypted local persistence, federated updates, and LoRa-ready sync all stay on device.",
                style = MaterialTheme.typography.bodyMedium,
            )
            Text(
                text = "Device: $deviceId",
                style = MaterialTheme.typography.labelMedium,
            )
        }
    }
}

@Composable
private fun ResultCard(
    result: ClinicalWorkflowResult,
    onShareBundle: ((String) -> Unit)? = null,
) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Transcript", style = MaterialTheme.typography.titleMedium)
                Text(result.transcriptText)
                Text(
                    text = "Confidence: ${formatConfidence(result.transcriptConfidence)}",
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Structured note", style = MaterialTheme.typography.titleMedium)
                Text(result.summary)
                result.sections.forEach { (section, content) ->
                    Text(section, style = MaterialTheme.typography.labelLarge)
                    Text(content)
                }
            }
        }
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("Entities and sync", style = MaterialTheme.typography.titleMedium)
                Text(
                    text = result.entities.joinToString().ifBlank { "No coded entities extracted." },
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text(
                    text = result.vitals.joinToString().ifBlank { "No vitals extracted." },
                    style = MaterialTheme.typography.bodyMedium,
                )
                Text("Stored path: ${result.storedPath}")
                Text(
                    text = result.federatedPacketId?.let { "LoRa packet $it queued (${result.federatedPayloadBytes} bytes)." }
                        ?: "Federated learning disabled for this encounter.",
                )
                Text("Queued packets: ${result.queuedPacketCount}")
            }
        }
        OutlinedCard(modifier = Modifier.fillMaxWidth()) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Text("FHIR bundle preview", style = MaterialTheme.typography.titleMedium)
                Box(modifier = Modifier.fillMaxWidth()) {
                    Text(
                        text = result.bundleJson,
                        fontFamily = FontFamily.Monospace,
                        maxLines = 24,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                onShareBundle?.let { shareBundle ->
                    OutlinedButton(
                        onClick = { shareBundle(result.bundleJson) },
                    ) {
                        Text("Share FHIR JSON")
                    }
                }
            }
        }
    }
}

private fun formatConfidence(value: Double): String {
    val rounded = (value * 100).toInt() / 100.0
    return rounded.toString()
}

package com.medloquent.shared.audio

import com.medloquent.shared.core.AudioChunk
import com.medloquent.shared.core.SpeechSession


data class AudioCaptureRequest(
    val seedTranscript: String,
    val sampleRateHz: Int = 16_000,
    val chunkTokenSize: Int = 8,
)

interface AudioCaptureEngine {
    suspend fun capture(
        session: SpeechSession,
        request: AudioCaptureRequest,
    ): List<AudioChunk>
}

class SeededAudioCaptureEngine : AudioCaptureEngine {
    override suspend fun capture(
        session: SpeechSession,
        request: AudioCaptureRequest,
    ): List<AudioChunk> {
        val tokens = request.seedTranscript
            .trim()
            .split(Regex("\\s+"))
            .filter { it.isNotBlank() }

        if (tokens.isEmpty()) {
            return emptyList()
        }

        return tokens.chunked(request.chunkTokenSize).mapIndexed { index, words ->
            AudioChunk(
                index = index,
                sampleRateHz = request.sampleRateHz,
                pcm16 = "",
                metadata = mapOf(
                    "seedTranscript" to words.joinToString(" "),
                    "sessionId" to session.sessionId,
                ),
            )
        }
    }
}
